"""
simulator.py — Simulateur de bouteilles de gaz connectées
==========================================================
SQUELETTE créé par Mohamed Guergari (DevOps)
À compléter par le membre en charge du simulateur
==========================================================

EXPLICATION :
    Ce script simule N maisons (NUM_DEVICES), chacune avec
    une bouteille de gaz. Toutes les PUBLISH_INTERVAL_SEC secondes,
    chaque maison publie ses mesures via MQTT.

    En mode "fleet", on lance 500 ou 1000 appareils simultanément
    pour tester la charge du système.
"""
import os
import json
import time
import random
import logging
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --- Configuration depuis les variables d'environnement ---
MQTT_HOST           = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT           = int(os.getenv("MQTT_PORT", 1883))
NUM_DEVICES         = int(os.getenv("NUM_DEVICES", 1))
PUBLISH_INTERVAL    = float(os.getenv("PUBLISH_INTERVAL_SEC", 5))
TARE_KG             = float(os.getenv("TARE_KG", 14.0))
BOTTLE_CAPACITY_KG  = float(os.getenv("BOTTLE_CAPACITY_KG", 12.0))


def publish_telemetry(client: mqtt.Client, device_id: str, weight_kg: float, gas_ppm: int):
    """Publie un message MQTT avec le payload standardisé."""
    topic = f"botalert/{device_id}/telemetry"
    payload = {
        "device_id": device_id,
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "weight_kg": round(weight_kg, 2),
        "gas_ppm": gas_ppm,
    }
    client.publish(topic, json.dumps(payload), qos=1)
    logging.info(f"[{device_id}] Publié → {payload}")


def main():
    logging.info(f"Démarrage simulateur : {NUM_DEVICES} appareil(s), intervalle {PUBLISH_INTERVAL}s")

    # Connexion au broker MQTT
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    # État initial de chaque bouteille (poids aléatoire pour varier)
    devices = {}
    for i in range(1, NUM_DEVICES + 1):
        device_id = f"home-{i:03d}"
        devices[device_id] = {
            "weight_kg": TARE_KG + random.uniform(2.0, BOTTLE_CAPACITY_KG),
            "consumption_per_cycle": random.uniform(0.05, 0.15),  # consommation variable
        }

    # Boucle principale d'envoi
    try:
        while True:
            for device_id, state in devices.items():
                # Simuler la consommation de gaz
                state["weight_kg"] = max(TARE_KG, state["weight_kg"] - state["consumption_per_cycle"])

                # Simuler un capteur de fuite (1% de chance de fuite)
                gas_ppm = random.randint(1200, 2000) if random.random() < 0.01 else random.randint(0, 50)

                publish_telemetry(client, device_id, state["weight_kg"], gas_ppm)

            time.sleep(PUBLISH_INTERVAL)

    except KeyboardInterrupt:
        logging.info("Simulateur arrêté.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
