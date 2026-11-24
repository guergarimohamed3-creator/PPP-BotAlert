# BotAlert — Architecture du Système

## Schéma d'Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        COUCHE CAPTEURS / SIMULATION                 │
│                                                                     │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐      ┌───────────┐   │
│  │ home-001  │  │ home-002  │  │ home-003  │ ...  │ home-N    │   │
│  │ (simulé)  │  │ (simulé)  │  │ (simulé)  │      │ N≤1000    │   │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘      └─────┬─────┘  │
│        │              │              │                    │         │
│        └──────────────┴──────────────┴────────────────────┘        │
│                              │  MQTT QoS 1                          │
│                    topic: botalert/<id>/telemetry                   │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      COUCHE TRANSPORT (MQTT)                         │
│                                                                      │
│              ┌─────────────────────────────┐                        │
│              │    Eclipse Mosquitto 2.0     │                        │
│              │    Broker MQTT               │                        │
│              │    Port 1883 (MQTT)          │                        │
│              │    Port 9001 (WebSocket)     │                        │
│              │    Persistance activée       │                        │
│              └──────────────┬──────────────┘                        │
│                             │  Subscribe botalert/+/telemetry        │
└─────────────────────────────┼────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     COUCHE BACKEND (FastAPI)                         │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                   FastAPI + MQTT Subscriber                   │  │
│  │                                                               │  │
│  │  1. Reçoit le message JSON MQTT                               │  │
│  │  2. Valide le payload (device_id, ts, weight_kg, gas_ppm)    │  │
│  │  3. Calcule :                                                 │  │
│  │     - remaining_kg = weight_kg - tare_kg (14kg)              │  │
│  │     - percent = remaining_kg / 12kg × 100                    │  │
│  │     - days_left = remaining / avg_daily_consumption           │  │
│  │  4. Détecte alertes (low_gas < 15%, leak > 1000 ppm)         │  │
│  │  5. Stocke dans TimescaleDB                                   │  │
│  │                                                               │  │
│  │  REST API :                                                   │  │
│  │  GET /devices                    → liste des appareils        │  │
│  │  GET /devices/{id}/readings      → historique mesures         │  │
│  │  GET /devices/{id}/status        → % gaz + jours restants    │  │
│  │  GET /alerts                     → alertes actives            │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
└──────────────────────────────┼───────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     COUCHE DONNÉES (TimescaleDB)                     │
│                                                                      │
│  ┌────────────────────────┐    ┌────────────────────────────────┐   │
│  │   Table : readings     │    │   Table : alerts               │   │
│  │   (hypertable)         │    │                                │   │
│  │                        │    │   id          SERIAL PK        │   │
│  │   ts         TIMESTAMP │    │   ts          TIMESTAMP        │   │
│  │   device_id  TEXT      │    │   device_id   TEXT             │   │
│  │   weight_kg  DOUBLE    │    │   alert_type  TEXT             │   │
│  │   gas_ppm    INTEGER   │    │   message     TEXT             │   │
│  │                        │    │   value       DOUBLE           │   │
│  │   Partitionné par 7j   │    │                                │   │
│  │   Index sur device_id  │    │                                │   │
│  └────────────────────────┘    └────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────┬───────────────────────────────────────┘
                               │  Connexion PostgreSQL directe
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    COUCHE VISUALISATION & ALERTES                    │
│                                                                      │
│  ┌──────────────────────────┐    ┌──────────────────────────────┐   │
│  │   Grafana 11.3           │    │   Telegram Bot               │   │
│  │                          │    │   (Haytam)                   │   │
│  │   - Jauge gaz restant    │    │                              │   │
│  │   - Courbe poids/temps   │    │   Notification en < 5s       │   │
│  │   - Niveau ppm           │    │   si low_gas ou leak         │   │
│  │   - Appareils actifs     │    │                              │   │
│  │   - Table des alertes    │    │                              │   │
│  │   - Débit MQTT msg/s     │    │                              │   │
│  │                          │    │                              │   │
│  │   Refresh : 5 secondes   │    │                              │   │
│  └──────────────────────────┘    └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Stack Technique

| Couche | Technologie | Rôle |
|--------|-------------|------|
| Transport | Eclipse Mosquitto 2.0 | Broker MQTT léger, persistance QoS 1 |
| Backend | FastAPI (Python 3.12) | API REST + subscriber MQTT |
| Base de données | TimescaleDB (PostgreSQL 16) | Stockage time-series optimisé |
| Dashboard | Grafana 11.3 | Visualisation temps réel |
| Alertes | Telegram Bot API | Notifications push |
| Infrastructure | Docker Compose | Orchestration des services |
| CI/CD | GitHub Actions | Lint, tests, build automatiques |

## Flux de Données Complet

```
Capteur IoT
    │
    │  MQTT Publish
    │  topic: botalert/home-001/telemetry
    │  payload: {"device_id":"home-001","ts":"...","weight_kg":18.4,"gas_ppm":12}
    ▼
Mosquitto (Broker)
    │
    │  MQTT Subscribe (botalert/+/telemetry)
    ▼
Backend FastAPI
    │  ├── Validation JSON
    │  ├── Calcul % gaz restant
    │  ├── Calcul jours restants
    │  ├── Détection alertes
    │  └── Stockage TimescaleDB
    ▼
TimescaleDB
    │
    ├──► Grafana ──► Dashboard en temps réel
    └──► Backend ──► Telegram Bot ──► Notification push
```

## État du Projet

| Composant | État | Responsable |
|-----------|------|-------------|
| Infrastructure Docker | ✅ Fait | Guergari |
| Broker MQTT | ✅ Fait | Guergari |
| Base de données + tables | ✅ Fait | Guergari |
| CI/CD GitHub Actions | ✅ Fait | Guergari |
| Simulateur IoT (1 maison) | ✅ Fait | Simulateur |
| Fleet Mode (100-1000) | ✅ Fait | Guergari |
| Test de résilience | ✅ Fait | Guergari |
| Backend FastAPI | 🔄 En cours | ElQadi |
| Endpoints REST | 🔄 En cours | ElQadi |
| Dashboard Grafana | 🔄 En cours | Haytam |
| Telegram Bot | 🔄 En cours | Haytam |
| Firmware réel | 📋 Semaines suivantes | - |
| Kubernetes (scaling) | 📋 Semaines suivantes | - |
| Modèle de prédiction ML | 📋 Semaines suivantes | - |

## Choix Techniques Justifiés

### Pourquoi MQTT ?
- **Léger** : payload minimal, idéal pour capteurs IoT avec peu de RAM
- **Pub/Sub** : découple les capteurs du backend (un broker pour N capteurs)
- **QoS 1** : garantit la livraison même en cas de déconnexion temporaire

### Pourquoi TimescaleDB ?
- **Extension PostgreSQL** : compatible avec tous les outils PostgreSQL standard
- **Hypertable** : partitionnement automatique par temps → requêtes rapides sur grandes plages
- **Compression** : données anciennes compressées automatiquement

### Pourquoi Docker Compose ?
- **Reproductible** : identique sur toutes les machines (Windows, Mac, Linux)
- **Isolé** : chaque service dans son conteneur, pas de conflits de versions
- **Démarrage rapide** : `docker compose up` = tout en < 5 minutes
