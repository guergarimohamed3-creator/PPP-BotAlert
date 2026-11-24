-- ============================================================
-- init.sql — Script d'initialisation de la base de données
-- ============================================================
-- EXPLICATION :
--   Ce script est exécuté AUTOMATIQUEMENT par TimescaleDB
--   au premier démarrage du conteneur. Il crée la structure
--   de la base de données (les tables) que le backend utilisera.
--
--   On utilise "CREATE TABLE IF NOT EXISTS" pour que le script
--   soit idempotent (sans erreur s'il est rejoué).
-- ============================================================

-- Activer l'extension TimescaleDB sur cette base de données
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ============================================================
-- TABLE 1 : readings — Les mesures des capteurs
-- ============================================================
-- Chaque ligne = un message MQTT reçu depuis une bouteille.
-- ============================================================
CREATE TABLE IF NOT EXISTS readings (
    -- ts : Timestamp ISO 8601 (ex: "2026-11-25T18:30:00Z")
    --      C'est la colonne "temps" utilisée par TimescaleDB.
    ts          TIMESTAMPTZ        NOT NULL,

    -- device_id : Identifiant unique de la maison (ex: "home-001")
    device_id   TEXT               NOT NULL,

    -- weight_kg : Poids total de la bouteille mesuré par le capteur
    weight_kg   DOUBLE PRECISION   NOT NULL,

    -- gas_ppm : Concentration de gaz dans l'air (détecteur de fuite)
    gas_ppm     INTEGER            NOT NULL
);

-- Transformer la table en "hypertable" TimescaleDB.
-- Cela partitionne automatiquement les données par intervalles de temps
-- (par défaut 7 jours), ce qui accélère ÉNORMÉMENT les requêtes sur
-- de grandes plages temporelles (500-1000 appareils sur plusieurs jours).
SELECT create_hypertable('readings', 'ts', if_not_exists => TRUE);

-- Index sur device_id pour accélérer les requêtes par appareil
CREATE INDEX IF NOT EXISTS idx_readings_device_id ON readings (device_id, ts DESC);

-- ============================================================
-- TABLE 2 : alerts — Les événements d'alerte
-- ============================================================
-- Chaque ligne = une alerte générée par le backend.
-- Types d'alertes : "low_gas" ou "leak"
-- ============================================================
CREATE TABLE IF NOT EXISTS alerts (
    -- id : Identifiant unique de l'alerte (auto-incrémenté)
    id          SERIAL             PRIMARY KEY,

    -- ts : Moment où l'alerte a été détectée
    ts          TIMESTAMPTZ        NOT NULL DEFAULT NOW(),

    -- device_id : La maison concernée
    device_id   TEXT               NOT NULL,

    -- alert_type : Type d'alerte ("low_gas" ou "leak")
    alert_type  TEXT               NOT NULL,

    -- message : Description lisible de l'alerte
    message     TEXT               NOT NULL,

    -- value : La valeur qui a déclenché l'alerte (% gaz ou ppm)
    value       DOUBLE PRECISION   NOT NULL
);

-- Index pour retrouver rapidement les alertes d'un appareil
CREATE INDEX IF NOT EXISTS idx_alerts_device_id ON alerts (device_id, ts DESC);

-- ============================================================
-- Données de démo (optionnel, pour tester immédiatement)
-- ============================================================
-- INSERT INTO readings (ts, device_id, weight_kg, gas_ppm)
-- VALUES (NOW(), 'home-001', 18.4, 12);
