# Firmware ESP32 — BotAlert

## Matériel requis

| Composant | Référence | Rôle |
|-----------|-----------|------|
| Microcontrôleur | ESP32 DevKit v1 | Cerveau du système |
| Capteur poids | HX711 + cellule 50 kg | Mesurer le poids de la bouteille |
| Capteur gaz | MQ-6 | Détecter une fuite GPL/butane |
| Buzzer | 5V passif | Alerte sonore locale |
| Breadboard | Standard | Montage sans soudure |
| Câbles Dupont | M-M et M-F | Connexions |

## Schéma de câblage

```
ESP32 DevKit v1
├── GPIO 4  ──────► HX711 DOUT (data)
├── GPIO 5  ──────► HX711 SCK  (clock)
├── GPIO 34 ──────► MQ-6  AO   (analogique)
├── GPIO 2  ──────► Buzzer +
├── 3.3V    ──────► HX711 VCC
├── 5V      ──────► MQ-6  VCC  (attention : 5V requis)
└── GND     ──────► HX711 GND, MQ-6 GND, Buzzer -
```

## Installation PlatformIO

```bash
# 1. Installer PlatformIO CLI
pip install platformio

# 2. Compiler le firmware
cd firmware/
pio run

# 3. Flasher sur l'ESP32 (connecté en USB)
pio run --target upload

# 4. Moniteur série pour debug
pio device monitor
```

## Calibration du capteur de poids (HX711)

1. Lancer le firmware sans charge
2. Lire la valeur brute dans le moniteur série
3. Poser un poids connu (1 kg) sur la cellule
4. Calculer : `SCALE_FACTOR = valeur_brute / 1.0`
5. Mettre à jour `config.h`

## Test en simulation (Wokwi)

Sans hardware, tester sur [wokwi.com](https://wokwi.com) :
1. Créer un nouveau projet ESP32
2. Copier le contenu de `src/main.cpp`
3. Ajouter les composants HX711 et MQ-6 dans le diagramme
4. Lancer la simulation
