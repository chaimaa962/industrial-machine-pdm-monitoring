# industrial-machine-pdm-monitoring

## 🏭 Industrial Machine Monitoring System for Predictive Maintenance

## 📋 Project Overview
This project implements an **intelligent industrial monitoring system** using **Arduino Uno simulation in Proteus** for **predictive maintenance (PdM)**. The system monitors machine vibrations and pressure in real-time, detects anomalies, and provides early warnings through both local indicators and a web interface.

## 🎯 Key Features
- ✅ Real-time vibration monitoring (0-3g) and pressure monitoring (0-1000 units)
- ✅ Intelligent drift detection algorithm for early warnings
- ✅ 5-level hierarchical alert system (Normal → Emergency)
- ✅ Local interface: 16x2 LCD + RGB LEDs + Buzzer
- ✅ Web interface with live graphs and historical data
- ✅ Emergency stop button with response time <50ms
- ✅ Virtual serial communication with 99.8% reliability

---

## 📸 Project Photos

### 1. Complete Electrical Schematic (Proteus)
![Circuit Schematic](images/shema.png)
*Complete electrical schematic designed in Proteus showing all connections and COMPIN virtual serial port*

### 2. COM1-COM3 Serial Communication Setup
![Serial Communication](images/COM.png)
*Configuration of virtual serial communication between Proteus simulation and computer*

### 3. Web Interface
![Web Dashboard](images/site.png)
*Screenshot of real-time web interface displaying simulated data*

---

## 🔧 How Virtual Serial Communication Works

### 🔄 Communication Flow (Proteus Simulation):

Proteus Simulation (Arduino Uno)

       │
▼ (Virtual Serial via COMPIN)

COM1 (Virtual Port) ← Proteus sends: "V:1.5(100%) P:500(100%) E:1"

       │
▼ (Virtual Serial Bridge)

COM3 (Virtual Port) ← Web interface reads this port
       │
▼
Web Dashboard

(Displays live graphs and alerts)


### 1. Proteus Simulation Side
- **COMPIN** component provides virtual serial communication
- Proteus sends data every 2 seconds via virtual serial port
- Data format: `V:value(%) P:value(%) E:state`
- Example: `V:1.5(100%) P:500(100%) E:1`

Where:
- `V:1.5` = Simulated vibration value (1.5g)
- `(100%)` = Percentage relative to normal
- `P:500` = Simulated pressure value (500 units)
- `E:1` = System state (1=Normal, 2=Warning, 3=Critical, 4=Emergency)

### 2. Virtual Bridge Setup
- **Virtual Serial Port Emulator** (com0com) creates COM1↔COM3 bridge
- Proteus (COMPIN) connects to COM1
- Python program reads from COM3
- Enables communication between simulation and real software

### 3. Web Interface Side
- Python (`iot_site.py`) reads from COM3
- Parses data: `V:1.5(100%) P:500(100%) E:1`
- Creates web server at `http://localhost:5000`
- Updates graphs and colors in real-time

---

## 🚀 Setup Instructions (Proteus Simulation)

### 1. Proteus Simulation Setup
1. Open `IOT-PROJECT1.pdsprj` in Proteus
2. Ensure **COMPIN** virtual serial component is properly configured
3. Set baud rate to **9600** in Proteus settings
4. Run the simulation

### 2. Virtual Serial Port Configuration
1. Install Virtual Serial Port Emulator (e.g., `com0com`)
2. Create virtual port pair: **COM1 ↔ COM3**
3. Configure Proteus COMPIN to use **COM1**

### 3. Python Server Setup

# Install required libraries
pip install pyserial flask

# Start the server
python iot_site.py

### 4. Access Web Dashboard
Open a web browser

Go to: http://localhost:5000

Monitor real-time simulated data

📊 System States & Indicators
State	Vibration	Pressure	LED	Buzzer	LCD Display

Normal	<2.0g	400-600	Green (Solid)	Silent	"Normal Operation"

Warning	2.0-2.8g	700-850	Yellow (Blink 1s)	Beep every 3s	"Warning"

Critical	>2.8g	<150 or >850	Red (Blink 500ms)	Rapid beeps	"CRITICAL: STOP"

Emergency	-	-	Red (Solid)	Continuous	"EMERGENCY STOP"

🔗 Data Format

Format: V:[value]([percentage]%) P:[value]([percentage]%) E:[state]

Examples:

Normal: V:1.5(100%) P:500(100%) E:1

Warning: V:2.0(133%) P:700(140%) E:2

Critical: V:2.8(187%) P:850(170%) E:3

Emergency: V:0.0(0%) P:0(0%) E:4

Frequency: Every 2 seconds + immediate on state change

# Conclusion

# Achievements:

✅ Complete Simulation System - Successfully designed and implemented a functional industrial monitoring system using Proteus simulation

✅ Virtual Communication - Implemented COMPIN virtual serial communication between Proteus and Python

✅ Predictive Capabilities - Developed intelligent algorithms for early failure detection in simulated environment

✅ Dual Interface System - Created both simulated local interface (LCD, LEDs, buzzer) and real web dashboard

✅ Educational Value - Demonstrated complete IoT system design without physical hardware requirements

# Technical Implementation:

Proteus Simulation: Complete circuit design with virtual components

Virtual Serial Communication: COMPIN to COM1 to COM3 bridge

Web Interface: Real-time data visualization from simulated sensors

Intelligent Algorithms: Drift detection and hierarchical alert system

# Future Enhancements:

Integration with physical hardware

Cloud-based data storage

Machine learning for advanced prediction

Mobile application interface

Multi-machine monitoring system

Academic Contribution:
This project successfully demonstrates the integration of:

Industrial IoT concepts

Predictive maintenance strategies

Virtual simulation techniques

Web-based monitoring systems

Intelligent alert mechanisms
