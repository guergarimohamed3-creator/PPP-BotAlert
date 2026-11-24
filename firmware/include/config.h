/*
 * config.h — Configuration matérielle et réseau du firmware ESP32
 * ================================================================
 * INSTRUCTION :
 *   Modifier ce fichier selon votre configuration réseau et câblage.
 *   Ne jamais commiter les vrais mots de passe WiFi sur GitHub !
 *   (Ce fichier est un exemple — les vraies valeurs vont dans un
 *    fichier secrets.h non versionné, ou via build_flags dans platformio.ini)
 * ================================================================
 */
#pragma once

// ─── Identification de l'appareil ────────────────────────────────────────
#define DEVICE_ID       "home-001"   // Changer pour chaque bouteille physique

// ─── Réseau WiFi ────────────────────────────────────────────────────────────
#define WIFI_SSID       "MON_WIFI"       // Nom du réseau WiFi
#define WIFI_PASSWORD   "MON_MOT_DE_PASSE"  // Mot de passe WiFi

// ─── Broker MQTT ─────────────────────────────────────────────────────────────
// En démo : adresse IP de l'ordinateur qui fait tourner docker-compose
// En production : adresse du serveur cloud
#define MQTT_HOST       "192.168.1.100"  // ← Remplacer par votre IP
#define MQTT_PORT       1883

// ─── Broches GPIO ────────────────────────────────────────────────────────────
#define HX711_DOUT_PIN  4     // HX711 Data
#define HX711_SCK_PIN   5     // HX711 Clock
#define MQ6_PIN         34    // MQ-6 sortie analogique (GPIO 34 = ADC1_CH6)
#define BUZZER_PIN      2     // Buzzer alerte locale

// ─── Calibration capteur de poids ───────────────────────────────────────────
// COMMENT CALIBRER :
//   1. Poser un poids connu (ex: 1 kg) sur la cellule de charge
//   2. Lire la valeur brute dans le moniteur série : scale.get_units(10)
//   3. SCALE_FACTOR = valeur_brute / 1.0
#define SCALE_FACTOR    420.0f   // ← À ajuster après calibration réelle

// ─── Paramètres métier ───────────────────────────────────────────────────────
#define TARE_KG             14.0f    // Poids bouteille vide (kg)
#define BOTTLE_CAPACITY_KG  12.0f   // Capacité en gaz (kg)
#define LEAK_THRESHOLD_PPM  1000    // Seuil d'alerte fuite (ppm)
#define LOW_GAS_THRESHOLD   15      // Seuil alerte niveau bas (%)

// ─── Timing ──────────────────────────────────────────────────────────────────
#define PUBLISH_INTERVAL_MS  10000   // 10 secondes entre chaque publication
