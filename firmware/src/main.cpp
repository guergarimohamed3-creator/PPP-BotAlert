/*
 * main.cpp — Firmware ESP32 pour BotAlert
 * =========================================
 * Auteur    : ElMehdi (Device)
 * Structure : Mohamed Guergari (DevOps)
 *
 * MATÉRIEL NÉCESSAIRE :
 *   - ESP32 DevKit v1
 *   - Capteur de poids : HX711 + cellule de charge 50 kg
 *   - Capteur de gaz   : MQ-6 (GPL / butane)
 *   - Buzzer (alerte locale)
 *
 * BRANCHEMENTS :
 *   HX711 :
 *     DOUT → GPIO 4   (DATA)
 *     SCK  → GPIO 5   (CLOCK)
 *     VCC  → 3.3V
 *     GND  → GND
 *
 *   MQ-6 :
 *     AO   → GPIO 34  (Analogique — lecture tension)
 *     VCC  → 5V (attention : le MQ-6 nécessite 5V)
 *     GND  → GND
 *
 *   Buzzer :
 *     +    → GPIO 2
 *     -    → GND
 *
 * CONTRAT MQTT (identique au simulateur Python) :
 *   Topic   : botalert/<DEVICE_ID>/telemetry
 *   Payload : {"device_id":"...","ts":"...","weight_kg":...,"gas_ppm":...}
 *
 * CONFIGURATION :
 *   Modifier les constantes dans config.h
 * =========================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <HX711.h>
#include <ArduinoJson.h>
#include "config.h"

// ─── Instances matérielles ────────────────────────────────────────────────
HX711   scale;
WiFiClient   wifiClient;
PubSubClient mqttClient(wifiClient);

// ─── Variables d'état ─────────────────────────────────────────────────────
unsigned long lastPublish = 0;
int           failCount   = 0;

// ─── Fonctions utilitaires ───────────────────────────────────────────────

void connectWiFi() {
    Serial.printf("[WiFi] Connexion à '%s'...\n", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\n[WiFi] ✅ Connecté ! IP: %s\n",
                      WiFi.localIP().toString().c_str());
    } else {
        Serial.println("\n[WiFi] ❌ Échec connexion WiFi. Redémarrage...");
        ESP.restart();
    }
}

void connectMQTT() {
    while (!mqttClient.connected()) {
        Serial.printf("[MQTT] Connexion à %s:%d...\n", MQTT_HOST, MQTT_PORT);

        if (mqttClient.connect(DEVICE_ID)) {
            Serial.println("[MQTT] ✅ Connecté !");
            failCount = 0;
        } else {
            failCount++;
            Serial.printf("[MQTT] ❌ Échec (état=%d). Retry dans 5s...\n",
                          mqttClient.state());
            delay(5000);

            // Si trop d'échecs, reconnexion WiFi
            if (failCount > 5) {
                Serial.println("[MQTT] Trop d'échecs → reconnexion WiFi");
                connectWiFi();
                failCount = 0;
            }
        }
    }
}

float readWeight() {
    /*
     * Lecture du capteur HX711.
     * Le facteur de calibration (SCALE_FACTOR) doit être déterminé
     * expérimentalement avec un poids connu (ex: 1 kg).
     * Formule : SCALE_FACTOR = lecture_brute / poids_réel_kg
     *
     * Pour la simulation Wokwi : retourner une valeur fictive.
     */
    if (!scale.is_ready()) {
        Serial.println("[HX711] ⚠️  Capteur non prêt");
        return -1.0;
    }
    float raw = scale.get_units(5);   // Moyenne sur 5 lectures
    return raw / SCALE_FACTOR;        // Conversion en kg
}

int readGasPPM() {
    /*
     * Lecture du MQ-6 (capteur de gaz GPL/butane).
     * Le MQ-6 sort une tension analogique (0-3.3V sur ESP32).
     *
     * Conversion approximative tension → ppm :
     *   - En dessous de 0.5V : air propre (< 200 ppm)
     *   - Au dessus de 2.0V  : fuite détectée (> 1000 ppm)
     *
     * Note : une calibration précise nécessite la datasheet du MQ-6
     * et un environnement contrôlé. Ici on fait une approximation linéaire.
     */
    int raw    = analogRead(MQ6_PIN);         // 0 à 4095 (12 bits ADC)
    float volt = raw * (3.3f / 4095.0f);      // Conversion en volts
    int ppm    = (int)(volt * 500);           // Approximation linéaire
    return ppm;
}

String buildPayload(float weight_kg, int gas_ppm) {
    /*
     * Construit le payload JSON selon le contrat partagé.
     * On utilise ArduinoJson pour éviter les bugs de formatage.
     */
    JsonDocument doc;
    doc["device_id"] = DEVICE_ID;
    doc["ts"]        = "2026-01-01T00:00:00Z";  // TODO: utiliser NTP pour l'heure réelle
    doc["weight_kg"] = serialized(String(weight_kg, 3));
    doc["gas_ppm"]   = gas_ppm;

    String output;
    serializeJson(doc, output);
    return output;
}

// ─── Setup ────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println("╔══════════════════════════════╗");
    Serial.println("║   BotAlert ESP32 Firmware    ║");
    Serial.println("╚══════════════════════════════╝");
    Serial.printf("Device ID : %s\n", DEVICE_ID);
    Serial.printf("MQTT Host : %s:%d\n", MQTT_HOST, MQTT_PORT);

    // Initialiser le capteur de poids HX711
    scale.begin(HX711_DOUT_PIN, HX711_SCK_PIN);
    scale.set_scale(SCALE_FACTOR);
    scale.tare();   // Mise à zéro (tare) au démarrage
    Serial.println("[HX711] ✅ Capteur initialisé, tare effectuée");

    // Initialiser le buzzer
    pinMode(BUZZER_PIN, OUTPUT);
    digitalWrite(BUZZER_PIN, LOW);

    // Connexion WiFi et MQTT
    connectWiFi();
    mqttClient.setServer(MQTT_HOST, MQTT_PORT);
    mqttClient.setKeepAlive(60);
    connectMQTT();

    Serial.println("\n✅ Système prêt. Publication toutes les "
                   + String(PUBLISH_INTERVAL_MS / 1000) + "s\n");
}

// ─── Loop ─────────────────────────────────────────────────────────────────
void loop() {
    // Maintenir la connexion MQTT
    if (!mqttClient.connected()) {
        connectMQTT();
    }
    mqttClient.loop();

    // Publier à l'intervalle défini
    unsigned long now = millis();
    if (now - lastPublish >= PUBLISH_INTERVAL_MS) {
        lastPublish = now;

        // Lire les capteurs
        float weight_kg = readWeight();
        int   gas_ppm   = readGasPPM();

        // Vérifier validité de la lecture poids
        if (weight_kg < 0) {
            Serial.println("[⚠️ ] Lecture poids invalide, skip");
            return;
        }

        // Alerte buzzer locale si fuite détectée
        if (gas_ppm > LEAK_THRESHOLD_PPM) {
            Serial.printf("[🚨] FUITE DÉTECTÉE ! gas_ppm=%d\n", gas_ppm);
            digitalWrite(BUZZER_PIN, HIGH);
            delay(200);
            digitalWrite(BUZZER_PIN, LOW);
        }

        // Construire et publier le payload
        String topic   = "botalert/" + String(DEVICE_ID) + "/telemetry";
        String payload = buildPayload(weight_kg, gas_ppm);

        bool ok = mqttClient.publish(topic.c_str(), payload.c_str(), false);

        Serial.printf("[MQTT] %s | %.3f kg | %d ppm → %s\n",
                      ok ? "✅" : "❌",
                      weight_kg,
                      gas_ppm,
                      topic.c_str());

        if (ok) {
            Serial.println("       Payload : " + payload);
        }
    }
}
