# BotAlert — Schéma Électrique & Guide de Câblage

## 1. Tableau de Brochage (Pinout ESP32)

| Composant | Broche Module | Broche ESP32 | Signal / Tension | Description |
| :--- | :--- | :--- | :--- | :--- |
| **HX711 (Pesée)** | VCC | `3.3V` (ou `5V`) | 3.3V DC | Alimentation de l'amplificateur |
| | GND | `GND` | Masse | Masse commune |
| | DT (DOUT) | `GPIO 4` | Entrée Numérique | Données série 24 bits |
| | SCK (CLK) | `GPIO 5` | Sortie Numérique | Horloge générée par l'ESP32 |
| **MQ-6 (Gaz)** | VCC | `5V` (`VIN`) | 5V DC | Alimentation du filament chauffant |
| | GND | `GND` | Masse | Masse commune |
| | AO (Analog) | `GPIO 34` | Entrée Analogique | Lecture tension proportionnelle au gaz (ADC1_CH6) |
| **Buzzer Actif** | VCC / (+) | `GPIO 2` | Sortie Numérique | Déclenchement de l'alarme sonore |
| | GND / (-) | `GND` | Masse | Masse commune |

> [!IMPORTANT]
> **Règle critique ADC ESP32 :**
> Ne jamais brancher le capteur MQ-6 sur une broche de l'ADC2 (GPIO 0, 2, 4, 12, 13, 14, 15, 25, 26, 27). L'activation du Wi-Fi bloque l'ADC2. Nous utilisons **GPIO 34 (ADC1)** qui fonctionne parfaitement en continu avec le Wi-Fi activé.

---

## 2. Câblage de la Balance (4 jauges de 50 kg)

Pour supporter une bouteille de gaz butane marocaine de 12 kg (qui pèse environ 26 kg au total avec sa carcasse en acier de 14 kg), on utilise 4 jauges de contrainte de 50 kg disposées aux 4 coins d'un plateau circulaire :

```
[Coin Haut-Gauche]  ────── E+ (Excitation+) ──────┐
[Coin Haut-Droite]  ────── E- (Excitation-) ──────┤
[Coin Bas-Gauche]   ────── A+ (Signal +)    ──────┼──> Module HX711 ──> ESP32 (GPIO 4, 5)
[Coin Bas-Droite]   ────── A- (Signal -)    ──────┘
```
