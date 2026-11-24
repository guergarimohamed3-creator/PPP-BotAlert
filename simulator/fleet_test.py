#!/usr/bin/env python3
"""
fleet_test.py — Script de test de charge (Fleet Mode)
======================================================
Auteur : Mohamed Guergari (DevOps)

USAGE :
    python fleet_test.py --devices 100   # Test avec 100 maisons
    python fleet_test.py --devices 500   # Test avec 500 maisons
    python fleet_test.py --devices 1000  # Test avec 1000 maisons

MESURES :
    - Messages publiés par seconde
    - Taux d'erreur
    - Durée du test configurable

Ce script est distinct du simulateur principal. Il est utilisé
uniquement pour les benchmarks de performance à présenter au prof.
======================================================
"""
import argparse
import json
import threading
import time
import random
import logging
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

MQTT_HOST = "localhost"
MQTT_PORT = 1883
TARE_KG   = 14.0
CAP_KG    = 12.0

# Métriques partagées entre threads
_lock = threading.Lock()
_metrics = {
    "published": 0,
    "errors":    0,
    "start_time": None,
}


def device_worker(device_id: str, interval: float, stop_event: threading.Event):
    """Thread représentant un capteur IoT."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"fleet-{device_id}")
    try:
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        client.loop_start()
    except Exception as e:
        log.error(f"Connexion impossible pour {device_id}: {e}")
        return

    weight = TARE_KG + random.uniform(2, CAP_KG)
    topic  = f"botalert/{device_id}/telemetry"

    while not stop_event.is_set():
        payload = json.dumps({
            "device_id": device_id,
            "ts":        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "weight_kg": round(weight, 2),
            "gas_ppm":   random.randint(0, 50),
        })
        result = client.publish(topic, payload, qos=1)
        with _lock:
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                _metrics["published"] += 1
            else:
                _metrics["errors"] += 1
        weight = max(TARE_KG, weight - 0.001)
        time.sleep(interval)

    client.loop_stop()
    client.disconnect()


def run_fleet_test(num_devices: int, duration_sec: int, interval: float):
    log.info(f"\n{'='*60}")
    log.info(f"🚀 TEST DE CHARGE : {num_devices} appareils")
    log.info(f"   Durée    : {duration_sec}s")
    log.info(f"   Intervalle : {interval}s par appareil")
    log.info(f"   Débit théorique max : {num_devices / interval:.0f} msg/s")
    log.info(f"{'='*60}\n")

    stop_event = threading.Event()
    threads = []

    _metrics["start_time"] = time.time()
    _metrics["published"]  = 0
    _metrics["errors"]     = 0

    # Démarrer tous les threads d'appareils
    for i in range(1, num_devices + 1):
        device_id = f"home-{i:04d}"
        t = threading.Thread(
            target=device_worker,
            args=(device_id, interval, stop_event),
            daemon=True,
        )
        t.start()
        threads.append(t)
        if num_devices > 100:
            time.sleep(0.01)  # Étaler le démarrage pour éviter le pic de connexions

    log.info(f"✅ {num_devices} threads démarrés. Test en cours...\n")

    # Afficher les métriques en direct toutes les 10 secondes
    elapsed = 0
    while elapsed < duration_sec:
        time.sleep(10)
        elapsed += 10
        with _lock:
            pub = _metrics["published"]
            err = _metrics["errors"]
            rate = pub / elapsed if elapsed > 0 else 0
        log.info(
            f"⏱  {elapsed}s | "
            f"📤 {pub} messages | "
            f"⚡ {rate:.1f} msg/s | "
            f"❌ {err} erreurs"
        )

    # Arrêter tous les threads
    stop_event.set()
    log.info("\nArrêt des appareils...")
    time.sleep(2)

    # Résultat final
    total_time = time.time() - _metrics["start_time"]
    with _lock:
        pub = _metrics["published"]
        err = _metrics["errors"]
        rate = pub / total_time
        error_pct = (err / (pub + err) * 100) if (pub + err) > 0 else 0

    log.info(f"\n{'='*60}")
    log.info(f"📊 RÉSULTATS FINAUX — {num_devices} appareils")
    log.info(f"   Durée totale   : {total_time:.1f}s")
    log.info(f"   Messages envoyés : {pub}")
    log.info(f"   Débit réel     : {rate:.2f} msg/s")
    log.info(f"   Erreurs        : {err} ({error_pct:.2f}%)")
    log.info(f"{'='*60}\n")

    return {
        "num_devices": num_devices,
        "messages_sent": pub,
        "rate_msg_per_sec": round(rate, 2),
        "errors": err,
        "error_pct": round(error_pct, 2),
        "duration_sec": round(total_time, 1),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BotAlert Fleet Load Test")
    parser.add_argument("--devices",  type=int,   default=100,  help="Nombre d'appareils")
    parser.add_argument("--duration", type=int,   default=60,   help="Durée du test (secondes)")
    parser.add_argument("--interval", type=float, default=5.0,  help="Intervalle de publication (secondes)")
    args = parser.parse_args()

    results = run_fleet_test(args.devices, args.duration, args.interval)

    # Sauvegarder les résultats en JSON (pour Grafana/rapport)
    import json
    output_file = f"fleet_results_{args.devices}_devices.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    log.info(f"📁 Résultats sauvegardés dans {output_file}")
