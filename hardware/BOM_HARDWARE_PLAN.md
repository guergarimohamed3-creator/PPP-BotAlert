# BotAlert — Spécification Matérielle & Demande de Dotation
## Projet Professionnel Personnalisé (PPP) - INE2 / INPT

**Responsable Matériel :** ElMehdi  
**Encadrant :** Session du Vendredi  

---

### 1. Stratégie Matérielle pour la Soutenance
Pour la démonstration auprès du professeur :
1. **Démonstration logicielle temps réel** : 100% opérationnelle via la bouteille virtuelle (`simulator/virtual_bottle.py`) et la simulation du microcontrôleur sur **Wokwi** (`firmware/diagram.json`).
2. **Dossier de conception matérielle complet** : Schéma électrique, équilibrage du pont de Wheatstone, code C++ testé, gestion des conflits ADC/Wi-Fi.
3. **Demande de dotation au Laboratoire / Département INE** : Présenter la présente fiche pour obtenir les composants réels en vue de la phase de prototypage physique.

---

### 2. Fiche de Demande de Matériel (À soumettre au Professeur)

| Réf | Composant | Spécifications Requises | Qté | Justification Technique dans BotAlert | Prix Est. (MAD) |
| :--- | :--- | :--- | :---: | :--- | :---: |
| **1** | **ESP32 NodeMCU DevKit V1** | Microcontrôleur 32-bit, Wi-Fi 2.4 GHz 802.11 b/g/n, ADC1 | 1 | Nœud passerelle IoT (Wi-Fi, MQTT, NTP UTC, alarme locale) | ~70 MAD |
| **2** | **Module HX711** | Convertisseur A/N 24 bits haute précision | 1 | Amplification et numérisation différentielle des jauges de pesée | ~25 MAD |
| **3** | **Kit 4 jauges de pesée 50 kg + PCB de combinaison** | 4 demi-ponts montés en pont de Wheatstone complet (200 kg max) | 1 kit | Pesée continue de la bouteille (Tare: 14 kg + Gaz: 12 kg = ~26 kg brut). 4 points d'appui pour la stabilité mécanique. | ~100 MAD |
| **4** | **Capteur de Gaz MQ-6** | Capteur SnO2 sensible au Butane/GPL (100 - 10000 ppm) | 1 | Détection précoce des fuites de gaz butane domestique (seuil > 1000 ppm) | ~40 MAD |
| **5** | **Buzzer Actif 5V / 3.3V** | Alarme piézoélectrique continue | 1 | Avertisseur sonore instantané sur place en cas de fuite | ~10 MAD |
| **6** | **Plaque d'essai (Breadboard) & Câblage** | Breadboard 830 points + câbles Dupont (M-M, M-F) | 1 lot | Prototypage et interconnexion | ~35 MAD |

---

### 3. Argumentaire Technique
- **Code prêt à flasher** : Le firmware PlatformIO (`firmware/src/main.cpp`) est déjà écrit, calibré et conforme au contrat JSON.
- **Sécurité et compatibilité** : Branchement du MQ-6 exclusivement sur **ADC1 (GPIO 34)** pour éviter le conflit matériel connu de l'ESP32 où l'activation du Wi-Fi désactive les canaux ADC2.
