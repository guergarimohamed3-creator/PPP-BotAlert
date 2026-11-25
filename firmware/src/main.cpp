/*
 * main.cpp — Firmware ESP32 pour BotAlert
 * =========================================
 * Auteur    : ElMehdi (Device / Hardware) & Mohamed Guergari (DevOps)
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
 *     AO   → GPIO 34  (Analogique ADC1 — lecture tension)
 *     VCC  → 5V (le filament de chauffe du MQ-6 nécessite 5V)
 *     GND  → GND
 *
 *   Buzzer :
 *     +    → GPIO 2
 *     -    → GND
 *
 * CONTRAT MQTT (identique au simulateur Python) :
 *   Topic   : botalert/<DEVICE_ID>/telemetry
 *   Payload : {"device_id":"...","ts":"...","weight_kg":...,"gas_ppm":...}
 * =========================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <HX711.h>
#include <ArduinoJson.h>
#include <time.h>
#include "config.h"

// ─── Instances matérielles ────────────────────────────────────────────────
HX711        scale;
WiFiClient   wifiClient;
PubSubClient mqttClient(wifiClient);

// ─── Variables d'état ─────────────────────────────────────────────────────
unsigned long lastPublish = 0;
int           failCount   = 0;
bool          ntpSynced   = false;

// ─── Fonctions utilitaires ───────────────────────────────────────────────

void setupNTP() {
    Serial.println("[NTP] Synchronisation de l'heure UTC (pool.ntp.org)...");
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
    struct tm timeinfo;
    if (getLocalTime(&timeinfo, 3000)) {
        Serial.println("[NTP] ✅ Heure UTC synchronisée.");
        ntpSynced = true;
    } else {
        Serial.println("[NTP] ⚠️  Synchronisation en cours...");
    }
}

String getIsoUtcTimestamp() {
    struct tm timeinfo;
    if (getLocalTime(&timeinfo, 100)) {
        char buf[30];
        strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
        return String(buf);
    }
    // Horodatage de secours si NTP pas encore synchronisé
    unsigned long secs = millis() / 1000;
    char fallback[30];
    snprintf(fallback, sizeof(fallback), "2026-11-25T12:%02lu:%02luZ", (secs / 60) % 60, secs % 60);
    return String(fallback);
}

void connectWiFi() {
    Serial.printf("[WiFi] Connexion à '%s'...\n", WIFI_SSID);
    WiFi.mode(WIFI_STA);
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
        setupNTP();
    } else {
        Serial.println("\n[WiFi] ❌ Échec connexion WiFi. Nouvelle tentative dans la boucle...");
    }
}

void connectMQTT() {
    if (WiFi.status() != WL_CONNECTED) return;

    while (!mqttClient.connected()) {
        Serial.printf("[MQTT] Connexion à %s:%d...\n", MQTT_HOST, MQTT_PORT);

        String clientId = "ESP32-BotAlert-" + String(DEVICE_ID);
        if (mqttClient.connect(clientId.c_str())) {
            Serial.println("[MQTT] ✅ Connecté !");
            failCount = 0;
        } else {
            failCount++;
            Serial.printf("[MQTT] ❌ Échec (état=%d). Retry dans 5s...\n",
                          mqttClient.state());
            delay(5000);

            if (failCount > 5) {
                Serial.println("[MQTT] Trop d'échecs → reconnexion WiFi");
                connectWiFi();
                failCount = 0;
                break;
            }
        }
    }
}

float readWeight() {
    if (!scale.is_ready()) {
        // En simulation Wokwi ou si non branché, lecture nominale ~18.4 kg
        return 18.4f;
    }
    float raw = scale.get_units(5);
    float weight = raw / SCALE_FACTOR;
    return roundf(weight * 10.0f) / 10.0f;
}

int readGasPPM() {
    int raw = analogRead(MQ6_PIN);   // 0 à 4095 (12 bits ADC sur GPIO 34)
    if (raw <= 20) {
        return 12; // Air propre baseline
    }
    float volt = raw * (3.3f / 4095.0f);
    int ppm = (int)(volt * 500);     // Approximation linéaire pour la démo
    return ppm;
}

String buildPayload(float weight_kg, int gas_ppm) {
    JsonDocument doc;
    doc["device_id"] = DEVICE_ID;
    doc["ts"]        = getIsoUtcTimestamp();
    doc["weight_kg"] = serialized(String(weight_kg, 1));
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
    scale.tare();
    Serial.println("[HX711] ✅ Capteur initialisé");

    // Initialiser le buzzer
    pinMode(BUZZER_PIN, OUTPUT);
    digitalWrite(BUZZER_PIN, LOW);

    // Connexion WiFi et MQTT
    connectWiFi();
    mqttClient.setServer(MQTT_HOST, MQTT_PORT);
    mqttClient.setKeepAlive(60);

    Serial.println("\n✅ Système prêt. Publication toutes les "
                   + String(PUBLISH_INTERVAL_MS / 1000) + "s\n");
}

// ─── Loop ─────────────────────────────────────────────────────────────────
void loop() {
    if (WiFi.status() == WL_CONNECTED) {
        if (!mqttClient.connected()) {
            connectMQTT();
        }
        mqttClient.loop();
    }

    unsigned long now = millis();
    if (now - lastPublish >= PUBLISH_INTERVAL_MS) {
        lastPublish = now;

        float weight_kg = readWeight();
        int   gas_ppm   = readGasPPM();

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

        String topic   = "botalert/" + String(DEVICE_ID) + "/telemetry";
        String payload = buildPayload(weight_kg, gas_ppm);

        bool ok = false;
        if (mqttClient.connected()) {
            ok = mqttClient.publish(topic.c_str(), payload.c_str(), false);
        }

        Serial.printf("[MQTT] %s | %.1f kg | %d ppm → %s\n",
                      ok ? "✅" : "⚠️",
                      weight_kg,
                      gas_ppm,
                      topic.c_str());

        Serial.println("       Payload : " + payload);
    }

    delay(20);
}
