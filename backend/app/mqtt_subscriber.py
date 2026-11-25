"""
app/mqtt_subscriber.py — Client MQTT asynchrone / threadé pour la télémétrie BotAlert
=====================================================================================
Mohamed ElQadi — Backend and Data Logic
"""
import json
import logging
import asyncio
from datetime import datetime
import paho.mqtt.client as mqtt

from app.config import settings
from app.models import TelemetryPayload
from app.logic import calculate_gas_metrics, detect_bottle_change
from app import db

log = logging.getLogger("botalert.mqtt")


class MQTTService:
    def __init__(self):
        self.client: mqtt.Client = None
        self.loop: asyncio.AbstractEventLoop = None

    def start(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="botalert-backend-subscriber",
        )
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        self.client.reconnect_delay_set(min_delay=1, max_delay=10)

        log.info(f"Connexion MQTT vers {settings.mqtt_host}:{settings.mqtt_port}...")
        try:
            self.client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            log.warning(f"Connexion initiale au broker MQTT échouée ({e}). Reconnexion en tâche de fond.")
            # Si le broker n'est pas encore prêt, paho gère ou on retente dans un thread
            self.client.loop_start()

    def stop(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            log.info("Client MQTT arrêté.")

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            log.info(f"✅ Connecté au broker MQTT. Abonnement à {settings.mqtt_topic}")
            client.subscribe(settings.mqtt_topic, qos=1)
        else:
            log.error(f"❌ Échec connexion MQTT, reason code: {reason_code}")

    def on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        log.warning(f"⚠️ Déconnecté du broker MQTT (code {reason_code}). Reconnexion auto...")

    def on_message(self, client, userdata, msg):
        """Reçoit le message MQTT et planifie le traitement async dans la boucle d'événements FastAPI."""
        try:
            payload_str = msg.payload.decode("utf-8")
            topic = msg.topic
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.process_message(topic, payload_str),
                    self.loop
                )
        except Exception as e:
            log.error(f"Erreur lors de la réception du message MQTT : {e}")

    async def process_message(self, topic: str, payload_str: str):
        """Valide le JSON, calcule les indicateurs, détecte les anomalies et persiste."""
        try:
            data = json.loads(payload_str)
            # Validation via Pydantic
            telemetry = TelemetryPayload(**data)
        except Exception as e:
            log.warning(f"Payload MQTT invalide sur topic {topic} : {e} -> {payload_str}")
            return

        device_id = telemetry.device_id
        ts = telemetry.ts
        weight_kg = telemetry.weight_kg
        gas_ppm = telemetry.gas_ppm

        try:
            # 1. Récupérer la mesure précédente pour détecter les changements de bouteille
            prev_reading = await db.get_latest_reading(device_id)

            # 2. Stocker la nouvelle lecture dans TimescaleDB
            await db.insert_reading(ts, device_id, weight_kg, gas_ppm)

            # 3. Calculs métier
            remaining_kg, percent = calculate_gas_metrics(
                weight_kg,
                tare_kg=settings.tare_kg,
                bottle_capacity_kg=settings.bottle_capacity_kg
            )

            # 4. Détection du changement de bouteille (saut de poids > 5kg)
            if prev_reading is not None:
                prev_weight = prev_reading["weight_kg"]
                if detect_bottle_change(weight_kg, prev_weight, settings.bottle_change_threshold_kg):
                    log.info(f"🔄 Changement de bouteille détecté pour {device_id} ({prev_weight}kg -> {weight_kg}kg)")
                    await db.insert_alert(
                        device_id=device_id,
                        alert_type="bottle_change",
                        message=f"Bouteille remplacée : passage de {prev_weight} kg à {weight_kg} kg.",
                        value=weight_kg,
                        ts=ts
                    )

            # 5. Détection de fuite (gas_ppm > leak_ppm_threshold)
            if gas_ppm >= settings.leak_ppm_threshold:
                # Éviter le spam : n'alerte que si pas déjà alerté dans les 2 dernières minutes
                is_spammed = await db.has_recent_alert(device_id, "leak", minutes=2)
                if not is_spammed:
                    log.warning(f"🚨 FUITE DE GAZ DÉTECTÉE sur {device_id}: {gas_ppm} ppm !")
                    await db.insert_alert(
                        device_id=device_id,
                        alert_type="leak",
                        message=f"Alerte fuite de gaz critique : {gas_ppm} ppm détectés !",
                        value=float(gas_ppm),
                        ts=ts
                    )

            # 6. Détection de niveau bas de gaz (percent < low_gas_threshold_pct)
            if percent <= settings.low_gas_threshold_pct:
                is_spammed = await db.has_recent_alert(device_id, "low_gas", minutes=30)
                if not is_spammed:
                    log.warning(f"⚠️ Niveau de gaz faible sur {device_id}: {percent}% ({remaining_kg} kg)")
                    await db.insert_alert(
                        device_id=device_id,
                        alert_type="low_gas",
                        message=f"Niveau de gaz bas : {percent}% restant ({remaining_kg} kg).",
                        value=percent,
                        ts=ts
                    )

        except Exception as e:
            log.error(f"Erreur lors de la persistance de la télémétrie pour {device_id}: {e}")


mqtt_service = MQTTService()
