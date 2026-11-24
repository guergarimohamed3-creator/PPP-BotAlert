# BotAlert — Système de Surveillance de Bouteilles de Gaz 🔥

## 📋 Présentation du Projet

Système IoT end-to-end qui surveille le niveau de gaz dans des bouteilles connectées :
- **Capteurs simulés** → publient via **MQTT**
- **Backend FastAPI** → abonné MQTT, stocke dans **TimescaleDB**
- **Grafana Dashboard** → visualisation temps réel + alertes
- **Telegram Bot** → notifications de fuite et niveau bas

## 👥 Équipe

| Rôle | Membre | Responsabilité |
|------|--------|----------------|
| Cloud & DevOps | Mohamed Guergari | Infrastructure, Docker, CI/CD, Fleet |
| Backend & Data | Mohamed ElQadi | FastAPI, MQTT subscriber, logique métier |
| Dashboard & Alertes | Haytam | Grafana, Telegram bot, démo |
| Simulateur | (membre 4) | Générateur de données MQTT |

## 📡 Contrat MQTT Partagé (NE PAS MODIFIER)

**Topic :** `botalert/<device_id>/telemetry`

**Payload JSON :**
```json
{
  "device_id": "home-001",
  "ts": "2026-11-25T18:30:00Z",
  "weight_kg": 18.4,
  "gas_ppm": 12
}
```

## ⚙️ Paramètres par Défaut

| Paramètre | Valeur | Description |
|-----------|--------|-------------|
| `TARE_KG` | 14 kg | Poids bouteille vide |
| `BOTTLE_CAPACITY_KG` | 12 kg | Capacité en gaz |
| `LOW_GAS_THRESHOLD_PCT` | 15 % | Seuil alerte niveau bas |
| `LEAK_PPM_THRESHOLD` | 1000 ppm | Seuil alerte fuite |

## 🚀 Démarrage Rapide (en moins de 5 minutes)

### Prérequis
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé
- [Git](https://git-scm.com/) installé

### Étapes

```bash
# 1. Cloner le dépôt
git clone https://github.com/<org>/botalert.git
cd botalert

# 2. Créer le fichier de configuration
cp .env.example .env

# 3. Lancer tous les services
docker compose up -d

# 4. Vérifier que tout est en marche
docker compose ps
```

### Accès aux Interfaces

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** (dashboard) | http://localhost:3000 | admin / admin_secret |
| **API Backend** | http://localhost:8000/docs | — |
| **MQTT Broker** | localhost:1883 | — (accès anonyme) |

## 🗂️ Structure du Projet

```
botalert/
├── .github/workflows/     # Pipeline CI/CD (lint, tests, build)
├── backend/               # Service FastAPI (Mohamed ElQadi)
│   ├── app/
│   ├── tests/
│   └── Dockerfile
├── simulator/             # Simulateur de capteurs IoT
│   └── Dockerfile
├── infra/                 # Configuration de l'infrastructure
│   ├── mosquitto/         # Config broker MQTT
│   ├── timescaledb/       # Script SQL d'initialisation
│   └── grafana/           # Provisioning automatique Grafana
├── docs/                  # Schéma d'architecture + slides
├── docker-compose.yml     # Orchestration complète
├── .env.example           # Modèle de configuration
└── README.md
```

## 🧪 Tests

```bash
# Lancer les tests du backend
docker compose exec backend pytest -v

# Vérifier les logs d'un service
docker compose logs -f backend
docker compose logs -f mosquitto
```

## 🌍 Mode Flotte (Fleet Mode)

Pour simuler 500 maisons :
```bash
NUM_DEVICES=500 docker compose up -d simulator
```

## 🛠️ Commandes Utiles

```bash
# Arrêter tous les services
docker compose down

# Arrêter ET effacer les données (reset complet)
docker compose down -v

# Reconstruire les images après modification du code
docker compose up -d --build

# Voir les métriques de performance
docker stats
```

## 📅 Timeline

| Jour | Objectif |
|------|----------|
| Mardi soir | ✅ Repo créé, docker-compose skeleton |
| Mercredi midi | Simulateur publie, backend stocke |
| Mercredi soir | Flow complet sur un laptop |
| Jeudi | Dashboard, alertes, fleet mode, répétition |
| Vendredi | Vérification finale 1h avant la séance |
