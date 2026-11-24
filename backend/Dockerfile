# ============================================================
# Dockerfile — Backend FastAPI
# ============================================================
# EXPLICATION DU Dockerfile (à expliquer au prof) :
#
#   Un Dockerfile est une "recette" pour créer une image Docker.
#   Une image = un environnement isolé avec tout ce qu'il faut
#   pour faire tourner notre application, sans dépendre de ce
#   qui est installé sur la machine hôte.
#
#   On utilise "python:3.12-slim" : version Python légère
#   (slim = sans les outils inutiles, image plus petite).
# ============================================================

# --- Étape 1 : Choisir l'image de base ---
# "FROM" = "Je commence depuis cette image existante"
FROM python:3.12-slim

# --- Étape 2 : Répertoire de travail dans le conteneur ---
# Toutes les commandes suivantes s'exécutent dans /app
WORKDIR /app

# --- Étape 3 : Copier et installer les dépendances ---
# On copie requirements.txt EN PREMIER (optimisation du cache Docker).
# Explication : si le code change mais pas les dépendances,
# Docker réutilise le cache de cette étape (plus rapide).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Étape 4 : Copier tout le code de l'application ---
COPY . .

# --- Étape 5 : Exposer le port ---
# EXPOSE = documenter que l'application écoute sur ce port
# (le vrai mapping de port se fait dans docker-compose.yml)
EXPOSE 8000

# --- Étape 6 : Commande de démarrage ---
# uvicorn = serveur ASGI pour FastAPI
# --host 0.0.0.0 = écouter sur toutes les interfaces (pas seulement localhost)
# --reload = redémarrer si le code change (utile en développement)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
