"""
app/main.py — Point d'entrée du backend FastAPI
================================================
SQUELETTE créé par Mohamed Guergari (DevOps)
À compléter par Mohamed ElQadi (Backend)
================================================
"""

from fastapi import FastAPI

# Création de l'application FastAPI
app = FastAPI(
    title="BotAlert API",
    description="API de surveillance des bouteilles de gaz connectées",
    version="1.0.0",
)


@app.get("/health")
async def health_check():
    """
    Endpoint de santé — vérifie que le service est en marche.
    Utilisé par docker-compose pour le healthcheck.
    """
    return {"status": "ok", "service": "botalert-backend"}


# TODO (Mohamed ElQadi) : Implémenter les endpoints suivants
# GET  /devices                     → liste des appareils
# GET  /devices/{id}/readings       → historique des mesures
# GET  /devices/{id}/status         → état actuel (% gaz, jours restants)
# GET  /alerts                      → liste des alertes
