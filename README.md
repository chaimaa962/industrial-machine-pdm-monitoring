# industrial-machine-pdm-monitoring

## 🏭 Système de Surveillance Industrielle pour Maintenance Prédictive

## 📋 Aperçu du Projet
Ce projet implémente un **système intelligent de surveillance industrielle** utilisant **Arduino Uno** pour la **maintenance prédictive (PdM)**. Le système surveille les vibrations et la pression des machines en temps réel, détecte les anomalies et fournit des alertes précoces via des indicateurs locaux et une interface web.

## 🎯 Fonctionnalités Principales
- ✅ Surveillance en temps réel des vibrations (0-3g) et pression (0-1000 unités)
- ✅ Algorithme intelligent de détection de dérive pour alertes précoces
- ✅ Système hiérarchique à 5 niveaux (Normal → Urgence)
- ✅ Interface locale : LCD 16x2 + LEDs RVB + Buzzer
- ✅ Interface web avec graphiques en direct et historique
- ✅ Bouton d'arrêt d'urgence avec temps de réponse <50ms
- ✅ Communication série avec 99.8% de fiabilité

---

## 📸 Photos du Projet

### 1. Schéma Électrique Complet
![Schéma du Circuit](schéma)
*Schéma électrique complet réalisé sous Proteus montrant toutes les connexions*

### 2. Montage Arduino
![Montage Arduino](images/arduino_setup.jpg)
*Photo du montage Arduino complet avec tous les capteurs*

### 3. Interface Web
![Dashboard Web](images/web_interface.png)
*Capture d'écran de l'interface web en temps réel*

### 4. Affichage LCD
![Écran LCD](images/lcd_display.jpg)
*Photo de l'écran LCD affichant les valeurs*

---

## 🔧 Comment la Communication COM1 ↔ COM3 Fonctionne

### 🔄 Flux de Communication Série :
