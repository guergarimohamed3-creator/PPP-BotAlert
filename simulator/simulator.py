"""
simulator.py — Simulateur de bouteilles de gaz connectées
==========================================================
Auteur : Mohamed Guergari (DevOps)
Rôle   : Simuler N maisons IoT qui publient leurs mesures via MQTT.

FONCTIONNEMENT :
    1. Chaque "maison" (home-001, home-002...) a une bouteille de gaz.
    2. Toutes les PUBLISH_INTERVAL_SEC secondes, chaque maison publie
       un message MQTT sur le topic botalert/<device_id>/telemetry.
    3. La consommation de gaz diminue progressivement.
    4. 1% de chance par cycle de simuler une fuite (gas_ppm > 1000).
    5. Quand la bouteille est vide, elle est automatiquement "changée".

FLEET MODE :
    Mettre NUM_DEVICES=500 ou 1000 dans .env pour tester la charge.
    Le script utilise des threads pour publier en parallèle.
==========================================================
"""

import json
import logging
import os
import random
import threading
import time
from datetime import UTC, datetime

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

# --- Configuration des logs ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# --- Configuration depuis les variables d'environnement ---
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
NUM_DEVICES = int(os.getenv("NUM_DEVICES", "1"))
PUBLISH_INTERVAL = float(os.getenv("PUBLISH_INTERVAL_SEC", "5"))
TARE_KG = float(os.getenv("TARE_KG", "14.0"))
BOTTLE_CAPACITY_KG = float(os.getenv("BOTTLE_CAPACITY_KG", "12.0"))

# Compteur global pour les métriques de performance
_lock = threading.Lock()
_stats = {"published": 0, "errors": 0}


def make_mqtt_client(client_id: str) -> mqtt.Client:
    """Crée et connecte un client MQTT avec reconnexion automatique."""
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id,
    )

    def on_connect(c, userdata, flags, reason_code, properties):
        if reason_code == 0:
            log.info(f"[{client_id}] Connecté au broker MQTT {MQTT_HOST}:{MQTT_PORT}")
        else:
            log.error(f"[{client_id}] Connexion refusée : code {reason_code}")

    def on_disconnect(c, userdata, flags, reason_code, properties):
        if reason_code != 0:
            log.warning(
                f"[{client_id}] Déconnecté (code {reason_code}), reconnexion..."
            )

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    # Reconnexion automatique toutes les 5 secondes si déconnecté
    client.reconnect_delay_set(min_delay=1, max_delay=5)

    # Tentatives de connexion avec retry (utile au démarrage de Docker)
    for attempt in range(10):
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            break
        except (OSError, RuntimeError) as e:
            log.warning(
                f"[{client_id}] Tentative {attempt+1}/10 échouée : {e}. Retry dans 3s..."
            )
            time.sleep(3)

    return client


def run_device(device_id: str):
    """
    Simule une bouteille de gaz pour un appareil donné.
    S'exécute dans un thread séparé pour le fleet mode.
    """
    client = make_mqtt_client(f"sim-{device_id}")
    client.loop_start()

    # État initial : bouteille entre 50% et 100% pleine (aléatoire par appareil)
    weight_kg = TARE_KG + random.uniform(BOTTLE_CAPACITY_KG * 0.5, BOTTLE_CAPACITY_KG)

    # Consommation journalière variable selon la "famille" simulée
    # Entre 0.3 kg/jour et 1.5 kg/jour → ramené par cycle
    daily_consumption = random.uniform(0.3, 1.5)
    consumption_per_cycle = (daily_consumption / 86400) * PUBLISH_INTERVAL

    topic = f"botalert/{device_id}/telemetry"

    while True:
        try:
            # --- Simuler la consommation de gaz ---
            weight_kg = max(TARE_KG, weight_kg - consumption_per_cycle)

            # --- Simuler un capteur de fuite (1% de chance) ---
            if random.random() < 0.01:
                gas_ppm = random.randint(1200, 3000)  # Fuite détectée !
            else:
                gas_ppm = random.randint(0, 50)  # Normal

            # --- Remplacement automatique de bouteille ---
            # Si la bouteille est vide (poids ≈ tare), on la "change"
            if weight_kg <= TARE_KG + 0.1:
                log.info(f"[{device_id}] Bouteille vide → changement automatique")
                weight_kg = TARE_KG + BOTTLE_CAPACITY_KG  # Bouteille neuve

            # --- Construire le payload JSON (contrat partagé) ---
            payload = {
                "device_id": device_id,
                "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "weight_kg": round(weight_kg, 2),
                "gas_ppm": gas_ppm,
            }

            # --- Publier sur MQTT (QoS 1 = accusé de réception) ---
            result = client.publish(topic, json.dumps(payload), qos=1)

            with _lock:
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    _stats["published"] += 1
                else:
                    _stats["errors"] += 1

            # Log seulement pour les 3 premiers appareils (sinon trop verbeux en fleet)
            if int(device_id.split("-")[-1]) <= 3:
                gas_status = "🔴 FUITE!" if gas_ppm > 1000 else "✅"
                remaining_pct = round(
                    (weight_kg - TARE_KG) / BOTTLE_CAPACITY_KG * 100, 1
                )
                log.info(
                    f"[{device_id}] {remaining_pct}% gaz | "
                    f"{weight_kg}kg | {gas_ppm}ppm {gas_status}"
                )

        except (OSError, RuntimeError) as e:
            log.error(f"[{device_id}] Erreur publication : {e}")
            with _lock:
                _stats["errors"] += 1

        time.sleep(PUBLISH_INTERVAL)


def print_stats():
    """Affiche les métriques de performance toutes les 30 secondes."""
    while True:
        time.sleep(30)
        with _lock:
            rate = _stats["published"] / 30 if _stats["published"] > 0 else 0
            log.info(
                f"📊 STATS | {NUM_DEVICES} appareils | "
                f"{_stats['published']} publiés | "
                f"{_stats['errors']} erreurs | "
                f"{rate:.1f} msg/s"
            )
            # Reset pour la prochaine fenêtre de 30s
            _stats["published"] = 0
            _stats["errors"] = 0


def main():
    log.info("=" * 60)
    log.info("🚀 BotAlert Simulator démarré")
    log.info(f"   Appareils  : {NUM_DEVICES}")
    log.info(f"   Broker     : {MQTT_HOST}:{MQTT_PORT}")
    log.info(f"   Intervalle : {PUBLISH_INTERVAL}s")
    log.info(f"   Tare       : {TARE_KG}kg | Capacité : {BOTTLE_CAPACITY_KG}kg")
    log.info("=" * 60)

    # Générer la liste des device IDs
    devices = [f"home-{i:03d}" for i in range(1, NUM_DEVICES + 1)]

    # Lancer le thread de statistiques
    stats_thread = threading.Thread(target=print_stats, daemon=True)
    stats_thread.start()

    # Lancer un thread par appareil (fleet mode)
    threads = []
    for device_id in devices:
        t = threading.Thread(target=run_device, args=(device_id,), daemon=True)
        t.start()
        threads.append(t)
        # Petit délai entre chaque démarrage pour éviter de surcharger le broker
        if NUM_DEVICES > 50:
            time.sleep(0.05)  # 50ms entre chaque appareil en fleet mode

    log.info(f"✅ {NUM_DEVICES} appareil(s) démarré(s)")

    # Maintenir le processus principal en vie
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("🛑 Simulateur arrêté par l'utilisateur.")


if __name__ == "__main__":
    main()
