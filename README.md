# BotAlert — Système de Surveillance de Bouteilles de Gaz 🔥

## 📋 Présentation du Projet

Système IoT end-to-end qui surveille le niveau de gaz dans des bouteilles connectées :
- **Capteurs simulés / Matériel (ESP32)** → publient via **MQTT**
- **Backend FastAPI** → abonné MQTT, calculs métiers et stockage dans **TimescaleDB**
- **Dashboard Grafana** → visualisation temps réel + gestion des seuils
- **Telegram Bot** → notifications instantanées de fuite et de niveau bas

## 👥 Équipe

| Rôle | Membre | Responsabilité |
|------|--------|----------------|
| Cloud & DevOps | Mohamed Guergari | Infrastructure, Docker Compose, CI/CD, Mode Flotte (Fleet) |
| Backend & Data | Mohamed ElQadi | FastAPI, MQTT subscriber, calculs (% gaz, jours restants), API REST |
| Dashboard & Alertes | Haytam | Dashboard Grafana, Bot Telegram, slides et scénario de démo |
| Device & Hardware | ElMehdi | Virtual bottle (`virtual_bottle.py`), firmware ESP32 (HX711 + MQ-6) |

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
| `TARE_KG` | 14 kg | Poids de la bouteille vide |
| `BOTTLE_CAPACITY_KG` | 12 kg | Capacité totale en gaz |
| `LOW_GAS_THRESHOLD_PCT` | 15 % | Seuil d'alerte niveau bas |
| `LEAK_PPM_THRESHOLD` | 1000 ppm | Seuil d'alerte fuite (gaz_ppm) |

## 🚀 Démarrage Rapide (en moins de 5 minutes)

### Prérequis
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et lancé
- [Git](https://git-scm.com/) installé

### Étapes

```bash
# 1. Cloner le dépôt
git clone https://github.com/<org>/botalert.git
cd botalert

# 2. Créer le fichier de configuration local
cp .env.example .env

# 3. Lancer l'infrastructure et la simulation
docker-compose up -d

# 4. Vérifier l'état des conteneurs
docker-compose ps
```

### Accès aux Interfaces

| Service | URL | Identifiants |
|---------|-----|--------------|
| **Grafana** (dashboard) | http://localhost:3000 | `admin` / `admin_secret` |
| **API Backend** (Swagger) | http://localhost:8000/docs | — |
| **MQTT Broker** (Mosquitto) | localhost:1883 | — (accès anonyme en dev) |
| **Simulation ESP32 (Wokwi)** | [wokwi.com/projects/481623555764025345](https://wokwi.com/projects/481623555764025345) | — (accessible en 1 clic) |

## 🗂️ Structure du Projet

```
botalert/
├── .github/workflows/     # Pipeline CI/CD (lint, tests, build)
├── backend/               # Service FastAPI (Mohamed ElQadi)
│   ├── app/
│   ├── tests/
│   └── Dockerfile
├── simulator/             # Simulation IoT (ElMehdi & Guergari)
│   ├── virtual_bottle.py  # Simulation réaliste 1 bouteille (sessions cuisine, fuite)
│   ├── fleet_test.py      # Benchmark de montée en charge
│   └── Dockerfile
├── firmware/              # Code source ESP32 PlatformIO (ElMehdi)
│   ├── src/main.cpp
│   ├── include/config.h
│   ├── diagram.json       # Schéma de simulation Wokwi
│   ├── wokwi.toml
│   └── platformio.ini
├── hardware/              # Dossier de conception matérielle (ElMehdi)
│   ├── BOM_HARDWARE_PLAN.md # Liste des composants, budget MAD et demande au labo
│   └── WIRING_DIAGRAM.md  # Schéma de câblage et brochage GPIO/ADC1
├── infra/                 # Configuration de l'infrastructure
│   ├── mosquitto/         # mosquitto.conf
│   ├── timescaledb/       # init.sql (hypertables readings & alerts)
│   ├── grafana/           # Provisioning datasources & dashboards
│   └── chaos_test.py      # Test de résilience (arrêt du broker)
├── docs/                  # Schéma d'architecture & documentation
├── docker-compose.yml     # Orchestration multi-services
├── run.ps1                # Script utilitaire PowerShell pour Windows
├── .env.example           # Modèle de variables d'environnement
└── README.md
```

## 🧪 Tests & Vérifications

```bash
# Lancer les tests unitaires du backend
docker-compose exec backend pytest -v

# Consulter les logs d'un service en temps réel
docker-compose logs -f backend
docker-compose logs -f mosquitto
docker-compose logs -f virtual_bottle
```

## 🌍 Mode Flotte (Fleet Mode - 100 à 1000 maisons)

Pour tester la montée en charge avec 500 maisons :

**Sur Linux / macOS / Bash :**
```bash
NUM_DEVICES=500 docker-compose up -d --build simulator
```

**Sur Windows PowerShell :**
```powershell
$env:NUM_DEVICES=500
docker-compose up -d --build simulator
# Ou utiliser le script utilitaire :
.\run.ps1 fleet 500
```

## 🛠️ Commandes Utiles

```bash
# Arrêter tous les services
docker-compose stop

# Arrêter ET supprimer les volumes (réinitialisation complète)
docker-compose down -v

# Reconstruire les conteneurs après modification du code
docker-compose up -d --build

# Surveiller la consommation CPU / RAM
docker stats
```

## 📅 Timeline

| Jour | Échéance | Objectif |
|------|----------|----------|
| Mardi soir | ✅ Terminé | Repo créé, contrat partagé validé, docker-compose skeleton & CI |
| Mercredi midi | ⏳ En cours | Le simulateur publie, le backend ingère et stocke dans TimescaleDB |
| Mercredi soir | 🎯 Prévu | Flux complet de bout en bout validé sur une seule machine |
| Jeudi | 🎯 Prévu | Dashboard finalisé, alertes Telegram, Fleet Mode et répétition générale |
| Vendredi | 🎯 Prévu | Vérification finale 1 heure avant la soutenance |
