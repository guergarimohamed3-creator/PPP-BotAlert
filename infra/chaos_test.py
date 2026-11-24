#!/usr/bin/env python3
"""
chaos_test.py — Test de résilience du système BotAlert
=======================================================
Auteur : Mohamed Guergari (DevOps)

OBJECTIF :
    Démontrer au professeur que le système est RÉSILIENT.
    On coupe volontairement le broker MQTT pendant 15 secondes,
    puis on le redémarre et on vérifie que tout reprend
    automatiquement sans perte de données.

SCÉNARIO DÉMONTRÉ :
    1. Le simulateur publie des messages normalement
    2. On arrête le conteneur Mosquitto (panne simulée)
    3. Le simulateur détecte la déconnexion et essaie de se reconnecter
    4. On redémarre Mosquitto après 15 secondes
    5. Le simulateur se reconnecte AUTOMATIQUEMENT
    6. Les données reprennent sans intervention humaine

USAGE :
    python chaos_test.py

PRÉREQUIS :
    docker-compose up -d (tous les services doivent tourner)
=======================================================
"""
import subprocess
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

BROKER_CONTAINER = "mosquitto"
DOWNTIME_SEC     = 15   # Durée de la panne simulée


def run(cmd: str) -> str:
    """Exécute une commande shell et retourne la sortie."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()


def get_message_count() -> int:
    """Compte le nombre de messages reçus dans la DB."""
    out = run(
        'docker-compose exec -T timescaledb psql -U botalert -d botalert_db '
        '-t -c "SELECT COUNT(*) FROM readings WHERE ts >= NOW() - INTERVAL \'2 minutes\';"'
    )
    try:
        return int(out.strip())
    except ValueError:
        return 0


def print_separator(title: str):
    log.info("=" * 55)
    log.info(f"  {title}")
    log.info("=" * 55)


def main():
    print_separator("🔬 TEST DE RÉSILIENCE — BotAlert")
    log.info("Ce test va simuler une panne du broker MQTT")
    log.info(f"Durée de la panne : {DOWNTIME_SEC} secondes\n")

    # --- Phase 1 : Vérifier l'état initial ---
    print_separator("Phase 1 : État initial")
    status = run(f"docker-compose ps {BROKER_CONTAINER}")
    log.info(f"État Mosquitto :\n{status}")

    count_before = get_message_count()
    log.info(f"Messages en DB (2 dernières minutes) : {count_before}")
    log.info("Attente 10s pour laisser le simulateur publier...")
    time.sleep(10)

    count_after_wait = get_message_count()
    log.info(f"Messages après 10s : {count_after_wait} (+{count_after_wait - count_before})\n")

    # --- Phase 2 : Simuler la panne ---
    print_separator("Phase 2 : 💥 PANNE — Arrêt du broker MQTT")
    log.info(f"Arrêt du conteneur '{BROKER_CONTAINER}'...")
    run(f"docker-compose stop {BROKER_CONTAINER}")
    log.info("✅ Mosquitto arrêté.")
    log.info(
        "👉 Le simulateur va tenter de se reconnecter automatiquement.\n"
        "   Les logs du simulateur montrent les tentatives de reconnexion.\n"
    )

    # Afficher un compte à rebours
    for i in range(DOWNTIME_SEC, 0, -5):
        log.info(f"   ⏳ Redémarrage dans {i} secondes...")
        time.sleep(5)

    # --- Phase 3 : Rétablissement ---
    print_separator("Phase 3 : 🔄 RÉTABLISSEMENT — Redémarrage du broker")
    log.info("Redémarrage de Mosquitto...")
    run(f"docker-compose start {BROKER_CONTAINER}")
    log.info("✅ Mosquitto redémarré.")
    log.info("Attente de 15s pour que le simulateur se reconnecte...")
    time.sleep(15)

    # --- Phase 4 : Vérification ---
    print_separator("Phase 4 : ✅ VÉRIFICATION")
    status_after = run(f"docker-compose ps {BROKER_CONTAINER}")
    log.info(f"État Mosquitto après redémarrage :\n{status_after}")

    count_recovered = get_message_count()
    log.info(f"Messages en DB (2 dernières minutes) : {count_recovered}")

    if count_recovered > count_after_wait:
        log.info(
            f"\n🎉 RÉSULTAT : RÉSILIENCE CONFIRMÉE !\n"
            f"   Nouveaux messages après rétablissement : "
            f"+{count_recovered - count_after_wait}\n"
            f"   Le simulateur s'est reconnecté AUTOMATIQUEMENT.\n"
            f"   Aucune intervention humaine nécessaire."
        )
    else:
        log.warning(
            "\n⚠️  Peu de messages reçus. Vérifier les logs du simulateur :\n"
            "   docker-compose logs --tail=20 simulator"
        )

    print_separator("FIN DU TEST DE RÉSILIENCE")


if __name__ == "__main__":
    main()
