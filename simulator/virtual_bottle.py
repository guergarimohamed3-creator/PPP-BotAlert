"""virtual_bottle.py — Simulateur réaliste d'une bouteille de gaz.

==============================================================
Auteur    : ElMehdi (Device / Simulateur) & Mohamed Guergari (DevOps)

FONCTIONNEMENT RÉALISTE :
    - 3 sessions de cuisson par jour (matin, midi, soir)
    - Consommation de gaz progressive pendant les sessions
    - Bruit aléatoire gaussien sur le capteur de poids (+/- 20g)
    - Changement automatique de bouteille quand vide (saut de poids visible > 5 kg)
    - Mode fuite : gas_ppm dépasse 1000 (déclenchable par flag CLI, env var, ou touche 'l')
    - Contrôles clavier interactifs en direct dans le terminal :
        [ l ] : Basculer le mode fuite (PPM > 1000)
        [ c ] : Remplacer la bouteille (recharge à 100%, saut de poids à 26 kg)
        [ k ] : Forcer le mode cuisson (brûleur allumé)
        [ + / - ] : Augmenter / diminuer l'accélération du temps
        [ q ] : Quitter proprement
    - Mode autonome / hors-ligne : fonctionne même si Mosquitto n'est pas encore lancé.

USAGE :
    # Démo normale (intervalle de 10s)
    python virtual_bottle.py

    # Mode accéléré (1s réelle = 60s simulées = 1 min)
    SPEED_FACTOR=60 python virtual_bottle.py

    # Démarrer directement en mode fuite
    python virtual_bottle.py --leak

CONTRAT MQTT :
    Topic   : botalert/<device_id>/telemetry
    Payload : {"device_id":"...","ts":"...","weight_kg":...,"gas_ppm":...}
==============================================================
"""

import argparse
import json
import logging
import os
import random
import socket
import sys
import time
from datetime import UTC, datetime, timedelta

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─── Configuration (supporte les deux conventions de nommage) ────────────────
MQTT_HOST = os.getenv("MQTT_HOST", os.getenv("MQTT_BROKER", "localhost"))
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
DEVICE_ID = os.getenv("DEVICE_ID", "home-001")
TARE_KG = float(os.getenv("TARE_KG", os.getenv("TARE_WEIGHT", "14.0")))
BOTTLE_CAP_KG = float(
    os.getenv("BOTTLE_CAPACITY_KG", os.getenv("GAS_CAPACITY", "12.0"))
)
SPEED_FACTOR = float(os.getenv("SPEED_FACTOR", os.getenv("SPEEDUP", "60.0")))
PUBLISH_INTERVAL = float(
    os.getenv("PUBLISH_INTERVAL_SEC", os.getenv("PUBLISH_INTERVAL", "10.0"))
)
LEAK_MODE_ENV = os.getenv("LEAK_MODE", "false").lower() in ("true", "1", "yes")

# ─── Sessions de cuisson quotidiennes (heures au format 24h) ─────────────────
# (heure_debut, heure_fin, taux_kg_par_heure, nom)
COOKING_SESSIONS = [
    (7.0, 8.5, 0.12, "Petit-déjeuner"),
    (12.0, 14.0, 0.20, "Déjeuner"),
    (19.5, 21.5, 0.25, "Dîner"),
]


def is_cooking(sim_hour: float) -> tuple[bool, float, str]:
    """Vérifie si la bouteille est en cours d'utilisation à l'heure simulée."""
    for start, end, rate, name in COOKING_SESSIONS:
        if start <= sim_hour < end:
            return True, rate, name
    return False, 0.0, "Repos"


def add_weight_noise(weight: float) -> float:
    """Simule le bruit mécanique du capteur HX711 (+/- 20g)."""
    return round(weight + random.gauss(0, 0.02), 2)


class NonBlockingKeyboard:
    """Gestionnaire de saisie clavier non-bloquante (Windows / Linux / Docker)."""

    def __init__(self):
        self.is_windows = os.name == "nt"
        self.is_tty = sys.stdin.isatty()
        self.old_settings = None

        if not self.is_windows and self.is_tty:
            try:
                import termios
                import tty

                self.old_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())
            except (ImportError, OSError):
                self.is_tty = False

    def get_key(self):
        if not self.is_tty:
            return None

        if self.is_windows:
            try:
                import msvcrt

                if msvcrt.kbhit():
                    ch = msvcrt.getch()
                    return ch.decode("utf-8", errors="ignore").lower()
            except (ImportError, OSError):
                return None
        else:
            try:
                import select

                rlist, _, _ = select.select([sys.stdin], [], [], 0)
                if rlist:
                    return sys.stdin.read(1).lower()
            except (ImportError, OSError):
                return None
        return None

    def cleanup(self):
        if not self.is_windows and self.old_settings and self.is_tty:
            try:
                import termios

                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
            except (ImportError, OSError):
                pass


def is_broker_available(host: str, port: int, timeout: float = 0.8) -> bool:
    """Vérifie rapidement si le port MQTT est accessible sans bloquer."""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except OSError:
        return False


def connect_mqtt(
    host: str, port: int, client_id: str
) -> tuple[mqtt.Client | None, bool]:
    """Tente de connecter le client MQTT avec détection hors-ligne propre."""
    if not is_broker_available(host, port):
        log.warning(f"⚠️  Broker MQTT injoignable sur {host}:{port}")
        log.info(
            "💡 Mode autonome actif : la simulation tourne en direct dans le terminal."
        )
        log.info("   (Démarrez Mosquitto ou Docker pour publier sur le réseau)\n")
        return None, False

    try:
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
        )

        def on_connect(c, userdata, flags, rc, props=None):
            rc_val = getattr(rc, "value", rc)
            if rc_val == 0:
                log.info(f"✅ Connecté au broker MQTT {host}:{port}")
            else:
                log.warning(f"Connexion MQTT refusée (code {rc_val})")

        client.on_connect = on_connect
        client.connect(host, port, keepalive=60)
        client.loop_start()
        return client, True
    except (OSError, RuntimeError) as e:
        log.warning(f"Échec de connexion MQTT ({e}), passage en mode démo autonome.")
        return None, False


def main():
    parser = argparse.ArgumentParser(description="BotAlert Virtual Bottle Simulator")
    parser.add_argument(
        "--leak", action="store_true", help="Démarrer en mode fuite (gas_ppm > 1000)"
    )
    parser.add_argument(
        "--speedup",
        type=float,
        default=SPEED_FACTOR,
        help="Facteur d'accélération (défaut: 60)",
    )
    parser.add_argument(
        "--device-id", default=DEVICE_ID, help="Identifiant de la bouteille"
    )
    args = parser.parse_args()

    leak_mode = args.leak or LEAK_MODE_ENV
    speedup = args.speedup
    device_id = args.device_id
    manual_cooking = False

    log.info("=" * 60)
    log.info("🛢️  BOTALERT — VIRTUAL BOTTLE SIMULATOR")
    log.info(f"   Device ID     : {device_id}")
    log.info(f"   Broker MQTT   : {MQTT_HOST}:{MQTT_PORT}")
    log.info(f"   Poids Tare    : {TARE_KG} kg (bouteille vide)")
    log.info(
        f"   Capacité Gaz  : {BOTTLE_CAP_KG} kg (bouteille pleine = {TARE_KG + BOTTLE_CAP_KG} kg)"
    )
    log.info(f"   Intervalle    : {PUBLISH_INTERVAL}s")
    log.info(f"   Accélération  : x{speedup:.0f} (1s réelle = {speedup:.0f}s simulées)")
    log.info(
        f"   Mode Fuite    : {'🔴 ACTIVÉ (>1000 ppm)' if leak_mode else '🟢 Normal'}"
    )
    log.info("-" * 60)
    log.info("Touches interactives dans le terminal :")
    log.info("  [ l ] Basculer le mode fuite (gas_ppm > 1000)")
    log.info("  [ c ] Remplacer la bouteille (recharge à 100%, saut > 5 kg)")
    log.info("  [ k ] Forcer la cuisson (brûleur allumé)")
    log.info("  [ + / - ] Augmenter / diminuer la vitesse de simulation")
    log.info("  [ q ] Quitter")
    log.info("=" * 60 + "\n")

    client, is_connected = connect_mqtt(
        MQTT_HOST, MQTT_PORT, f"virtual-bottle-{device_id}"
    )
    topic = f"botalert/{device_id}/telemetry"

    # État initial de la bouteille
    gas_kg = BOTTLE_CAP_KG * 0.85
    sim_now = datetime.now(UTC).replace(hour=7, minute=0, second=0, microsecond=0)
    bottle_changes = 0

    kbd = NonBlockingKeyboard()
    last_publish = 0.0

    try:
        while True:
            # Gestion des touches clavier
            key = kbd.get_key()
            if key:
                if key == "l":
                    leak_mode = not leak_mode
                    state_str = (
                        "🔴 ACTIVÉ (PPM > 1000)"
                        if leak_mode
                        else "🟢 DÉSACTIVÉ (Normal)"
                    )
                    print(f"\n[ALERTE] Mode fuite : {state_str}\n", flush=True)
                elif key == "c":
                    bottle_changes += 1
                    gas_kg = BOTTLE_CAP_KG
                    print(
                        f"\n[ÉVÉNEMENT] 🔄 Bouteille #{bottle_changes} changée ! Nouveau poids : {TARE_KG + gas_kg:.1f} kg (Saut > 5kg détecté)\n",
                        flush=True,
                    )
                elif key == "k":
                    manual_cooking = not manual_cooking
                    print(
                        f"\n[CUISSON] Mode forcé : {'ALLUMÉ' if manual_cooking else 'ARRÊTÉ'}\n",
                        flush=True,
                    )
                elif key in ("+", "="):
                    speedup = min(3600.0, speedup * 2)
                    print(
                        f"\n[VITESSE] Accélération portée à x{speedup:.0f}\n",
                        flush=True,
                    )
                elif key in ("-", "_"):
                    speedup = max(1.0, speedup / 2)
                    print(
                        f"\n[VITESSE] Accélération réduite à x{speedup:.0f}\n",
                        flush=True,
                    )
                elif key == "q":
                    print("\n[STOP] Arrêt demandé par l'utilisateur.\n", flush=True)
                    break

            now = time.time()
            if now - last_publish >= PUBLISH_INTERVAL:
                dt_real = now - last_publish if last_publish > 0 else PUBLISH_INTERVAL
                last_publish = now

                # Avancer le temps simulé
                sim_elapsed_seconds = dt_real * speedup
                sim_now += timedelta(seconds=sim_elapsed_seconds)
                sim_hour = sim_now.hour + sim_now.minute / 60.0

                # Calcul de la consommation de gaz
                cooking_sched, rate_per_hour, meal_name = is_cooking(sim_hour)
                is_active_cooking = cooking_sched or manual_cooking

                consumed = 0.0
                if is_active_cooking:
                    active_rate = rate_per_hour if cooking_sched else 0.25
                    consumed += active_rate * (sim_elapsed_seconds / 3600.0)

                if leak_mode:
                    consumed += 1.20 * (
                        sim_elapsed_seconds / 3600.0
                    )  # Le gaz s'échappe vite lors d'une fuite

                gas_kg = max(0.0, gas_kg - consumed)

                # Changement automatique si vide
                if gas_kg <= 0.05:
                    bottle_changes += 1
                    gas_kg = BOTTLE_CAP_KG
                    log.info(
                        f"🔄 Bouteille vide → remplacement automatique #{bottle_changes} (Poids: {TARE_KG + gas_kg:.1f} kg)"
                    )

                # Bruit du capteur de poids
                weight = TARE_KG + gas_kg
                measured_weight = max(TARE_KG, add_weight_noise(weight))

                # Capteur de gaz MQ-6
                if leak_mode:
                    gas_ppm = random.randint(1200, 2400)
                else:
                    gas_ppm = max(5, int(random.gauss(15, 4)))

                pct = round((gas_kg / BOTTLE_CAP_KG) * 100.0, 1)

                # Contrat JSON partagé
                payload = {
                    "device_id": device_id,
                    "ts": sim_now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "weight_kg": round(measured_weight, 1),
                    "gas_ppm": gas_ppm,
                }
                payload_str = json.dumps(payload)

                # Publication MQTT si connecté
                if client and is_connected:
                    try:
                        client.publish(topic, payload_str, qos=1)
                    except OSError:
                        pass

                # Affichage des logs
                status = (
                    "🔴 FUITE !"
                    if gas_ppm > 1000
                    else ("🟡 GAZ BAS (<15%)" if pct < 15 else "🟢 OK")
                )
                session_desc = (
                    f"🍳 {meal_name}"
                    if cooking_sched
                    else ("🍳 Cuisson manuelle" if manual_cooking else "💤 Repos")
                )

                log.info(
                    f"[{sim_now.strftime('%H:%M:%S')}] {status} | "
                    f"Poids: {round(measured_weight, 1):>4.1f} kg ({pct:>5.1f}%) | "
                    f"Gaz: {gas_ppm:>4} ppm | "
                    f"{session_desc}"
                )

            time.sleep(0.08)

    except KeyboardInterrupt:
        log.info("🛑 Simulateur arrêté proprement.")
    finally:
        kbd.cleanup()
        if client and is_connected:
            client.loop_stop()
            client.disconnect()


if __name__ == "__main__":
    main()
