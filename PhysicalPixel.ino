#include <LiquidCrystal.h>

// ---------------------------------------------
// 1. DÉFINITION DES BROCHES
// ---------------------------------------------
const int BOUTON_URGENCE = 6;
const int CAPTEUR_VIBRATION = A0;
const int CAPTEUR_PRESSION = A1;
const int LED_VERTE = 5;
const int LED_JAUNE = 3;
const int LED_ROUGE = 2;
const int BUZZER = 4;
const int RELAIS = 7;

// LCD: (RS, E, D4, D5, D6, D7)
LiquidCrystal lcd(8, 9, 10, 11, 12, 13);

// ---------------------------------------------
// 2. CONSTANTES ET VARIABLES (MISES À JOUR)
// ---------------------------------------------
float vibrationValue = 0.0;
float pressionValue = 0.0;
int etatCode = 1;
bool systemeBloque = false;
unsigned long dernierBeep = 0;

// Valeurs normales (100%)
const float VIBRATION_NORMALE = 1.5;
const float PRESSION_NORMALE = 500.0;

// Seuils de danger fixes (pourcentage)
const int SEUIL_ALERTE = 133;
const int SEUIL_CRITIQUE = 187;

// Variables de filtrage
float vibrationFiltree = 0.0;
float pressionFiltree = 0.0;
const float ALPHA = 0.3;

// NOUVEAU: Variables pour l'analyse de tendance (Dérive)
float vibrationPrecedente = 0.0;
float pressionPrecedente = 0.0;
// Dérive max tolérée entre deux lectures (à ajuster selon la fréquence du loop)
const float SEUIL_DERIVE_VIB = 0.05; // Ex: si la vibration augmente de 0.05g d'un coup
const float SEUIL_DERIVE_PRESS = 5.0; // Ex: si la pression augmente de 5.0 unités d'un coup

// ---------------------------------------------
// 3. SETUP
// ---------------------------------------------
void setup() {
    Serial.begin(9600);
    
    // Configuration des broches
    pinMode(BOUTON_URGENCE, INPUT_PULLUP);
    pinMode(RELAIS, OUTPUT);
    pinMode(LED_VERTE, OUTPUT);
    pinMode(LED_JAUNE, OUTPUT);
    pinMode(LED_ROUGE, OUTPUT);
    pinMode(BUZZER, OUTPUT);
    
    // Initialisation LCD
    lcd.begin(16, 2);
    lcd.print("Systeme Industriel");
    lcd.setCursor(0, 1);
    lcd.print("Pred. Maintenance");
    
    // État initial
    digitalWrite(RELAIS, HIGH);
    etatNormal();
    
    delay(2000);
    lcd.clear();
}

// ---------------------------------------------
// 4. LOOP PRINCIPALE
// ---------------------------------------------
void loop() {
    // Surveillance bouton urgence
    if (digitalRead(BOUTON_URGENCE) == LOW) {
        delay(50);
        if (digitalRead(BOUTON_URGENCE) == LOW) {
            arretUrgenceSysteme();
            return;
        }
    }

    if (!systemeBloque) {
        lireCapteurs();
        determinerEtat();
        
        static unsigned long dernierEnvoi = 0;
        if (millis() - dernierEnvoi >= 2000) {
            envoyerDonneesSerial();
            dernierEnvoi = millis();
        }

        gererLEDs();
        gererSons();
        afficherLCD();
    } else {
        gestionSystemeBloque();
    }
    
    delay(50);
}

// ---------------------------------------------
// 5. FONCTIONS DE LECTURE ET D'ÉTAT (MISES À JOUR)
// ---------------------------------------------

int calculerPourcentage(float valeur, float normale) {
    if (normale == 0) return 0;
    return constrain((int)((valeur / normale) * 100), 0, 300);
}

float convertirVibration(int raw) {
    return (raw / 1023.0) * 3.0; // 0-3g
}

float convertirPression(int raw) {
    return (raw / 1023.0) * 1000.0; // 0-1000 unités
}

float filtrePasseBas(float ancienne, float nouvelle, float alpha) {
    return alpha * nouvelle + (1 - alpha) * ancienne;
}

void lireCapteurs() {
    // 1. Enregistrer les valeurs filtrées actuelles comme les 'précédentes' pour le calcul de dérive
    vibrationPrecedente = vibrationValue;
    pressionPrecedente = pressionValue;
    
    // 2. Lecture brute et conversion
    int rawVib = analogRead(CAPTEUR_VIBRATION);
    int rawPress = analogRead(CAPTEUR_PRESSION);
    
    float vibBrute = convertirVibration(rawVib);
    float pressBrute = convertirPression(rawPress);
    
    // 3. Filtrage et mise à jour des valeurs
    vibrationFiltree = filtrePasseBas(vibrationFiltree, vibBrute, ALPHA);
    pressionFiltree = filtrePasseBas(pressionFiltree, pressBrute, ALPHA);
    
    vibrationValue = vibrationFiltree;
    pressionValue = pressionFiltree;
}

void determinerEtat() {
    int p_vib = calculerPourcentage(vibrationValue, VIBRATION_NORMALE);
    int p_press = calculerPourcentage(pressionValue, PRESSION_NORMALE);
    
    // CALCUL NOUVEAU: Taux de Dérive (valeur absolue de la différence)
    float deriveVib = abs(vibrationValue - vibrationPrecedente);
    float derivePress = abs(pressionValue - pressionPrecedente);

    bool deriveCritique = (deriveVib >= SEUIL_DERIVE_VIB) ||
                          (derivePress >= SEUIL_DERIVE_PRESS);
    
    // CONDITIONS DE SEUILS FIXES
    bool critique = (p_vib >= SEUIL_CRITIQUE) ||
                    (p_press >= 170) ||
                    (p_press <= 30);
    
    bool alerte = (p_vib >= SEUIL_ALERTE && p_vib < SEUIL_CRITIQUE) ||
                  (p_press >= 140 && p_press < 170) ||
                  (p_press <= 40 && p_press > 30);
    
    // LOGIQUE DE PRIORITÉ (Critique > Dérive > Alerte > Normal)
    
    if (critique) {
        etatCode = 3; // ALERTE ROUGE (Seuil dépassé)
        digitalWrite(RELAIS, LOW); // Arrêt immédiat
    } else if (deriveCritique) {
        etatCode = 2; // ALERTE JAUNE (Tendance d'augmentation rapide)
        digitalWrite(RELAIS, HIGH); // Garde la machine en marche mais alerte l'opérateur
    } else if (alerte) {
        etatCode = 2; // AVERTISSEMENT (Seuil atteint)
        digitalWrite(RELAIS, HIGH);
    } else {
        etatCode = 1; // NORMAL
        digitalWrite(RELAIS, HIGH);
    }
}

// ---------------------------------------------
// 6. FONCTIONS D'AFFICHAGE ET DE PÉRIPHÉRIQUES (MISES À JOUR)
// ---------------------------------------------

void envoyerDonneesSerial() {
    int p_vib = calculerPourcentage(vibrationValue, VIBRATION_NORMALE);
    int p_press = calculerPourcentage(pressionValue, PRESSION_NORMALE);
    
    // Format EXACT comme spécifié
    String donnees = "V:" + String(vibrationValue, 1) + 
                     "(" + String(p_vib) + "%) " +
                     "P:" + String((int)pressionValue) + 
                     "(" + String(p_press) + "%) " +
                     "E:" + String(etatCode);
    
    Serial.println(donnees);
}

void arretUrgenceSysteme() {
    digitalWrite(RELAIS, LOW);
    digitalWrite(LED_VERTE, LOW);
    digitalWrite(LED_JAUNE, LOW);
    digitalWrite(LED_ROUGE, HIGH);
    tone(BUZZER, 1000);
    
    lcd.clear();
    lcd.print("*** ARRET URGENCE ***");
    lcd.setCursor(0, 1);
    lcd.print("Systeme bloque");
    
    systemeBloque = true;
    etatCode = 4;
    
    Serial.println("V:0.0(0%) P:0(0%) E:4");
}

void gestionSystemeBloque() {
    static unsigned long dernierClignotement = 0;
    static unsigned long dernierBuzzer = 0;
    static bool buzzerOn = false;
    
    // LED rouge clignote
    if (millis() - dernierClignotement >= 500) {
        digitalWrite(LED_ROUGE, !digitalRead(LED_ROUGE));
        dernierClignotement = millis();
    }
    
    // Buzzer pulsé
    if (millis() - dernierBuzzer >= 1000) {
        buzzerOn = !buzzerOn;
        if (buzzerOn) {
            tone(BUZZER, 800);
        } else {
            noTone(BUZZER);
        }
        dernierBuzzer = millis();
    }
}

void gererLEDs() {
    static unsigned long dernierChangement = 0;
    unsigned long maintenant = millis();
    
    switch(etatCode) {
        case 1:
            digitalWrite(LED_VERTE, HIGH);
            digitalWrite(LED_JAUNE, LOW);
            digitalWrite(LED_ROUGE, LOW);
            break;
        case 2:
            digitalWrite(LED_VERTE, LOW);
            digitalWrite(LED_ROUGE, LOW);
            // La LED Jaune clignote
            if (maintenant - dernierChangement >= 1000) {
                digitalWrite(LED_JAUNE, !digitalRead(LED_JAUNE));
                dernierChangement = maintenant;
            }
            break;
        case 3:
            digitalWrite(LED_VERTE, LOW);
            digitalWrite(LED_JAUNE, LOW);
            // La LED Rouge clignote
            if (maintenant - dernierChangement >= 500) {
                digitalWrite(LED_ROUGE, !digitalRead(LED_ROUGE));
                dernierChangement = maintenant;
            }
            break;
    }
}

void gererSons() {
    if (systemeBloque) return;
    
    unsigned long maintenant = millis();
    
    switch(etatCode) {
        case 1:
            noTone(BUZZER);
            break;
        case 2:
            if (maintenant - dernierBeep >= 3000) {
                tone(BUZZER, 800, 200);
                dernierBeep = maintenant;
            }
            break;
        case 3:
            if (maintenant - dernierBeep >= 500) {
                tone(BUZZER, 1200, 300);
                dernierBeep = maintenant;
            }
            break;
    }
}

void afficherLCD() {
    static unsigned long dernierAffichage = 0;
    
    // Calcul de la dérive pour l'affichage conditionnel
    float deriveVib = abs(vibrationValue - vibrationPrecedente);
    float derivePress = abs(pressionValue - pressionPrecedente);
    bool isDeriveAlert = (deriveVib >= SEUIL_DERIVE_VIB) || (derivePress >= SEUIL_DERIVE_PRESS);

    if (millis() - dernierAffichage >= 500) {
        // Ligne 1: État
        lcd.setCursor(0, 0);
        switch(etatCode) {
            case 1: lcd.print("NORMAL        "); break;
            case 2: 
                // Affiche 'Tendance' si l'alerte est causée par l'accélération (plus intelligent)
                if (isDeriveAlert) {
                    lcd.print("TENDANCE ROUGE"); 
                } else {
                    lcd.print("AVERTISSEMENT "); // Avertissement simple (seuil fixe)
                }
                break;
            case 3: lcd.print("ALERTE ROUGE  "); break;
            case 4: lcd.print("URGENCE       "); break;
        }
        
        // Ligne 2: Valeurs
        lcd.setCursor(0, 1);
        int p_vib = calculerPourcentage(vibrationValue, VIBRATION_NORMALE);
        int p_press = calculerPourcentage(pressionValue, PRESSION_NORMALE);
        
        // Affichage Vibration
        lcd.print("V:");
        lcd.print(vibrationValue, 1);
        lcd.print("(");
        if (p_vib < 100) lcd.print("0");
        if (p_vib < 10) lcd.print("0");
        lcd.print(p_vib);
        lcd.print("%)");
        
        // Affichage Pression
        lcd.setCursor(10, 1);
        lcd.print("P:");
        lcd.print((int)pressionValue);
        lcd.print("(");
        if (p_press < 100) lcd.print("0");
        if (p_press < 10) lcd.print("0");
        lcd.print(p_press);
        lcd.print("%)");
        
        dernierAffichage = millis();
    }
}

void etatNormal() {
    digitalWrite(LED_VERTE, HIGH);
    digitalWrite(LED_JAUNE, LOW);
    digitalWrite(LED_ROUGE, LOW);
    digitalWrite(RELAIS, HIGH);
    noTone(BUZZER);
    etatCode = 1;
}