"""
virtual_bottle.py — Simulateur réaliste d'une bouteille de gaz
==============================================================
Auteur    : ElMehdi (Device / Simulateur)
Structure : Mohamed Guergari (DevOps)

FONCTIONNEMENT RÉALISTE :
    - 3 sessions de cuisson par jour (matin, midi, soir)
    - Consommation de gaz uniquement pendant les sessions
    - Bruit aléatoire sur le poids (simule les vibrations du capteur)
    - Changement automatique de bouteille quand vide
    - Mode fuite : gas_ppm dépasse 1000 (activable par flag CLI ou LEAK_MODE=true)
    - Speed factor : 1 sec réelle = N minutes simulées (pour démo rapide)

USAGE :
    # Démo normale (10s entre chaque publication)
    python virtual_bottle.py

    # Mode accéléré (1s = 1 minute simulée, pour montrer une journée en 24s)
    SPEED_FACTOR=60 python virtual_bottle.py

    # Simuler une fuite
    python virtual_bottle.py --leak

    # Changer l'appareil
    DEVICE_ID=home-042 python virtual_bottle.py

VARIABLES D'ENVIRONNEMENT :
    MQTT_HOST           : adresse du broker (défaut: localhost)
    MQTT_PORT           : port MQTT (défaut: 1883)
    DEVICE_ID           : identifiant de la bouteille (défaut: home-001)
    TARE_KG             : poids bouteille vide en kg (défaut: 14.0)
    BOTTLE_CAPACITY_KG  : capacité en gaz en kg (défaut: 12.0)
    SPEED_FACTOR        : accélération du temps (défaut: 1)
    PUBLISH_INTERVAL_SEC: intervalle entre publications en secondes (défaut: 10)
    LEAK_MODE           : "true" pour activer la fuite (défaut: false)

CONTRAT MQTT (ne pas modifier) :
    Topic   : botalert/<device_id>/telemetry
    Payload : {"device_id":"...","ts":"...","weight_kg":...,"gas_ppm":...}
==============================================================
"""
import os
import sys
import json
import time
import random
import logging
import argparse
from datetime import datetime, timezone, timedelta

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── Configuration ───────────────────────────────────────────────────────────
MQTT_HOST          = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT          = int(os.getenv("MQTT_PORT", 1883))
DEVICE_ID          = os.getenv("DEVICE_ID", "home-001")
TARE_KG            = float(os.getenv("TARE_KG", 14.0))
BOTTLE_CAP_KG      = float(os.getenv("BOTTLE_CAPACITY_KG", 12.0))
SPEED_FACTOR       = float(os.getenv("SPEED_FACTOR", 1))      # 1 = temps réel, 60 = x60
PUBLISH_INTERVAL   = float(os.getenv("PUBLISH_INTERVAL_SEC", 10))
LEAK_MODE_ENV      = os.getenv("LEAK_MODE", "false").lower() == "true"

# ─── Modélisation des sessions de cuisson ────────────────────────────────────
# Chaque session = (heure_début_h, heure_fin_h, conso_kg_par_heure)
COOKING_SESSIONS = [
    (7,  8,  0.08),   # Petit-déjeuner : 7h-8h, 0.08 kg/h
    (12, 13, 0.15),   # Déjeuner       : 12h-13h, 0.15 kg/h
    (19, 21, 0.20),   # Dîner          : 19h-21h, 0.20 kg/h
]


def is_cooking(sim_hour: float) -> tuple[bool, float]:
    """
    Vérifie si la bouteille est en cours d'utilisation à l'heure simulée.
    Retourne (en_cuisson, consommation_kg_par_heure).
    """
    for start, end, rate in COOKING_SESSIONS:
        if start <= sim_hour < end:
            return True, rate
    return False, 0.0


def add_weight_noise(weight: float) -> float:
    """
    Ajoute un bruit gaussien pour simuler les vibrations du capteur HX711.
    Bruit de ±20g (0.02 kg) → réaliste pour un capteur à jauge de contrainte.
    """
    return weight + random.gauss(0, 0.02)


def connect_mqtt() -> mqtt.Client:
    """Crée et connecte le client MQTT avec reconnexion automatique."""
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"virtual-bottle-{DEVICE_ID}",
    )

    def on_connect(c, userdata, flags, rc, props):
        if rc == 0:
            log.info(f"✅ Connecté au broker {MQTT_HOST}:{MQTT_PORT}")
        else:
            log.error(f"❌ Connexion refusée (code {rc})")

    def on_disconnect(c, userdata, flags, rc, props):
        if rc != 0:
            log.warning("⚠️  Déconnecté, tentative de reconnexion...")

    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=1, max_delay=10)

    for attempt in range(10):
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            return client
        except Exception as e:
            log.warning(f"Tentative {attempt+1}/10 : {e}. Retry dans 3s...")
            time.sleep(3)

    log.error("Impossible de se connecter au broker. Arrêt.")
    sys.exit(1)


def main():
    # ─── Arguments CLI ───────────────────────────────────────────────────────
    parser = argparse.ArgumentParser(description="BotAlert Virtual Bottle Simulator")
    parser.add_argument(
        "--leak", action="store_true",
        help="Activer le mode fuite (gas_ppm > 1000)",
    )
    args = parser.parse_args()

    leak_mode = args.leak or LEAK_MODE_ENV

    # ─── Affichage de la configuration ───────────────────────────────────────
    log.info("=" * 55)
    log.info(f"🫙  BotAlert — Virtual Bottle Simulator")
    log.info(f"   Device ID    : {DEVICE_ID}")
    log.info(f"   Broker       : {MQTT_HOST}:{MQTT_PORT}")
    log.info(f"   Tare         : {TARE_KG} kg")
    log.info(f"   Capacité gaz : {BOTTLE_CAP_KG} kg")
    log.info(f"   Intervalle   : {PUBLISH_INTERVAL}s")
    log.info(f"   Speed factor : x{SPEED_FACTOR} (1s = {SPEED_FACTOR} min simulées)")
    log.info(f"   Mode fuite   : {'🔴 ACTIVÉ' if leak_mode else '✅ Normal'}")
    log.info("=" * 55)

    # ─── Connexion MQTT ───────────────────────────────────────────────────────
    client = connect_mqtt()
    client.loop_start()

    topic = f"botalert/{DEVICE_ID}/telemetry"

    # ─── État initial de la bouteille ─────────────────────────────────────────
    # Bouteille à 80% pleine au démarrage
    gas_kg  = BOTTLE_CAP_KG * 0.80
    weight  = TARE_KG + gas_kg

    # Temps simulé : on part de 06h00 aujourd'hui
    sim_now = datetime.now(timezone.utc).replace(hour=6, minute=0, second=0, microsecond=0)

    # Durée simulée par intervalle de publication
    sim_step = timedelta(minutes=PUBLISH_INTERVAL * SPEED_FACTOR / 60)

    bottle_changes = 0

    try:
        while True:
            sim_hour = sim_now.hour + sim_now.minute / 60.0

            # ─── Calcul de la consommation ─────────────────────────────────
            cooking, rate_per_hour = is_cooking(sim_hour)

            if cooking:
                # Consommation pendant la durée simulée de ce cycle
                hours_elapsed = (PUBLISH_INTERVAL * SPEED_FACTOR) / 3600
                consumed = rate_per_hour * hours_elapsed
                gas_kg = max(0.0, gas_kg - consumed)
                weight = TARE_KG + gas_kg

            # ─── Bruit du capteur ─────────────────────────────────────────
            measured_weight = add_weight_noise(weight)

            # ─── Détection gaz ppm ────────────────────────────────────────
            if leak_mode:
                gas_ppm = random.randint(1200, 3000)
            else:
                gas_ppm = random.randint(0, 50)

            # ─── Changement automatique de bouteille ──────────────────────
            if gas_kg <= 0.05:
                bottle_changes += 1
                log.info(f"🔄 Bouteille #{bottle_changes} vide → changement automatique !")
                gas_kg = BOTTLE_CAP_KG
                weight = TARE_KG + gas_kg
                measured_weight = add_weight_noise(weight)
                # Le saut de poids visible dans les données = détection de changement

            # ─── Calcul du % restant ──────────────────────────────────────
            pct = round(gas_kg / BOTTLE_CAP_KG * 100, 1)

            # ─── Payload JSON (contrat partagé) ───────────────────────────
            payload = {
                "device_id": DEVICE_ID,
                "ts":        sim_now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "weight_kg": round(measured_weight, 3),
                "gas_ppm":   gas_ppm,
            }

            # ─── Publication MQTT ──────────────────────────────────────────
            result = client.publish(topic, json.dumps(payload), qos=1)

            # ─── Log ───────────────────────────────────────────────────────
            status = "🔴 FUITE" if gas_ppm > 1000 else ("🟡 BAS" if pct < 15 else "🟢")
            session_label = f"🍳 cuisson ({rate_per_hour}kg/h)" if cooking else "💤 repos"
            log.info(
                f"[{sim_now.strftime('%H:%M')}] {status} | "
                f"{pct}% gaz | "
                f"{round(measured_weight, 2)}kg | "
                f"{gas_ppm}ppm | "
                f"{session_label}"
            )

            # ─── Avancer le temps simulé ──────────────────────────────────
            sim_now += sim_step

            time.sleep(PUBLISH_INTERVAL)

    except KeyboardInterrupt:
        log.info("🛑 Simulateur arrêté.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
