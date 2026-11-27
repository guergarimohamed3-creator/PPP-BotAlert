"""
app/main.py — Point d'entrée de l'API Backend BotAlert
======================================================
Auteurs: Mohamed Guergari (DevOps / Skeleton)
         Mohamed ElQadi (Backend and Data Logic)

Endpoints disponibles :
- GET  /health                      → Vérification de santé du service
- GET  /devices                     → Liste de tous les appareils enregistrés
- GET  /devices/{id}/readings       → Historique des mesures pour un appareil
- GET  /devices/{id}/status         → Statut en temps réel (% restant, jours restants, alertes)
- GET  /alerts                      → Liste des alertes détectées
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import ReadingOut, DeviceStatus, AlertOut, DeviceSummary
from app.logic import calculate_gas_metrics, calculate_days_left
from app import db
from app.mqtt_subscriber import mqtt_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
log = logging.getLogger("botalert.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestionnaire de cycle de vie de FastAPI (démarrage et arrêt).
    Démarre la connexion TimescaleDB et le subscriber MQTT.
    """
    log.info("🚀 Démarrage du backend BotAlert...")
    loop = asyncio.get_running_loop()
    
    # 1. Tester et initialiser le pool TimescaleDB
    try:
        pool = await db.get_db_pool()
        log.info("✅ Connexion à TimescaleDB établie avec succès.")
    except Exception as e:
        log.error(f"⚠️ Erreur de connexion à TimescaleDB au démarrage: {e}")

    # 2. Démarrer le subscriber MQTT
    try:
        mqtt_service.start(loop)
    except Exception as e:
        log.error(f"⚠️ Erreur lors du démarrage du client MQTT: {e}")

    yield

    # Arrêt gracieux
    log.info("🛑 Arrêt du backend BotAlert...")
    mqtt_service.stop()
    await db.close_db_pool()
    log.info("✅ Arrêt complet terminé.")


app = FastAPI(
    title="BotAlert API",
    description="API de surveillance et prédiction pour bouteilles de gaz butane connectées",
    version="1.0.0",
    lifespan=lifespan,
)

# Configuration CORS pour que l'app Web de Haytam puisse interroger l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """
    Endpoint de santé — vérifie que le service est en marche.
    Utilisé par docker-compose pour le healthcheck.
    """
    return {
        "status": "ok",
        "service": "botalert-backend",
        "mqtt_host": settings.mqtt_host,
        "postgres_host": settings.postgres_host,
    }


@app.get("/devices", response_model=List[DeviceSummary])
async def list_devices():
    """
    GET /devices
    Retourne la liste de tous les appareils ayant envoyé au moins une mesure.
    """
    try:
        devices = await db.get_all_devices()
        results = []
        for d in devices:
            weight = d.get("weight_kg")
            percent = None
            if weight is not None:
                _, percent = calculate_gas_metrics(
                    weight,
                    tare_kg=settings.tare_kg,
                    bottle_capacity_kg=settings.bottle_capacity_kg
                )
            results.append(DeviceSummary(
                device_id=d["device_id"],
                last_seen=d.get("ts"),
                last_weight_kg=weight,
                last_gas_ppm=d.get("gas_ppm"),
                percent=percent,
            ))
        return results
    except Exception as e:
        log.error(f"Erreur dans list_devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/devices/{device_id}/readings", response_model=List[ReadingOut])
async def get_device_readings(
    device_id: str,
    limit: int = Query(default=100, ge=1, le=1000)
):
    """
    GET /devices/{id}/readings
    Retourne l'historique récent des mesures pour un appareil donné.
    """
    try:
        readings = await db.get_device_readings(device_id, limit=limit)
        return [
            ReadingOut(
                ts=r["ts"],
                device_id=r["device_id"],
                weight_kg=r["weight_kg"],
                gas_ppm=r["gas_ppm"],
            )
            for r in readings
        ]
    except Exception as e:
        log.error(f"Erreur dans get_device_readings({device_id}): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/devices/{device_id}/status", response_model=DeviceStatus)
async def get_device_status(device_id: str):
    """
    GET /devices/{id}/status
    Retourne l'état actuel calculé de l'appareil :
    - remaining_gas_kg : poids du gaz restant
    - percent : pourcentage de gaz restant (0 à 100%)
    - days_left : estimation du nombre de jours avant épuisement
    - status : "ok", "low_gas", "leak"
    """
    try:
        latest = await db.get_latest_reading(device_id)
        if not latest:
            raise HTTPException(
                status_code=404,
                detail=f"Aucune mesure trouvée pour l'appareil '{device_id}'"
            )

        weight_kg = latest["weight_kg"]
        gas_ppm = latest["gas_ppm"]
        ts = latest["ts"]

        # 1. Calcul du gaz restant et du pourcentage
        remaining_kg, percent = calculate_gas_metrics(
            weight_kg,
            tare_kg=settings.tare_kg,
            bottle_capacity_kg=settings.bottle_capacity_kg
        )

        # 2. Récupération des mesures sur la fenêtre de calcul (par défaut 7 jours)
        history = await db.get_device_readings_since(
            device_id,
            days=settings.consumption_days_window
        )
        history_tuples = [(r["ts"], r["weight_kg"]) for r in history]

        # 3. Calcul de la prédiction des jours restants
        days_left = calculate_days_left(
            remaining_gas_kg=remaining_kg,
            readings=history_tuples,
            tare_kg=settings.tare_kg
        )

        # 4. Statut global
        status_label = "ok"
        if gas_ppm >= settings.leak_ppm_threshold:
            status_label = "leak"
        elif percent <= settings.low_gas_threshold_pct:
            status_label = "low_gas"

        # 5. Dernier changement de bouteille
        alerts = await db.get_alerts(device_id=device_id, limit=10)
        last_change_ts = None
        for a in alerts:
            if a["alert_type"] == "bottle_change":
                last_change_ts = a["ts"]
                break

        return DeviceStatus(
            device_id=device_id,
            ts=ts,
            weight_kg=weight_kg,
            remaining_gas_kg=remaining_kg,
            percent=percent,
            days_left=days_left,
            gas_ppm=gas_ppm,
            status=status_label,
            last_bottle_change=last_change_ts,
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Erreur dans get_device_status({device_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alerts", response_model=List[AlertOut])
async def list_alerts(
    device_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500)
):
    """
    GET /alerts
    Retourne la liste des alertes (fuites, niveau bas, changement de bouteille).
    Optionnellement filtrable par device_id.
    """
    try:
        alerts = await db.get_alerts(device_id=device_id, limit=limit)
        return [
            AlertOut(
                id=a["id"],
                ts=a["ts"],
                device_id=a["device_id"],
                alert_type=a["alert_type"],
                message=a["message"],
                value=a["value"],
            )
            for a in alerts
        ]
    except Exception as e:
        log.error(f"Erreur dans list_alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
