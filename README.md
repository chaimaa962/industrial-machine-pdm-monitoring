# industrial-machine-pdm-monitoring
Arduino-based industrial machine monitoring system for predictive maintenance with web interface.project 2025/2026.

📡 How COM1 ↔ COM3 Communication Works
🔄 Serial Communication Flow:
Arduino Board
    │
    ▼ (Serial Data via USB)
COM1 (Physical Port) ← Arduino sends: "V:1.5(100%) P:500(100%) E:1"
    │
    ▼ (Virtual Serial Bridge)
COM3 (Virtual Port) ← Web Interface reads this port
    │
    ▼
Web Browser Dashboard
    (Displays live graphs & alerts)

🔧 Hardware ↔ Software Connection:
1. Arduino Side (Physical - COM1)
Arduino connects to computer via USB cable

Computer recognizes it as COM1 (or COMx) serial port

Arduino sends data every 2 seconds in this format:
V:1.5(100%) P:500(100%) E:1
Where:

V:1.5 = Vibration value (1.5g)

(100%) = Percentage of normal

P:500 = Pressure value (500 units)

E:1 = System state (1=Normal, 2=Warning, 3=Critical, 4=Emergency)

2. Computer Side (Virtual Bridge - COM3)
Virtual Serial Port Emulator creates COM1→COM3 bridge

Why? Because some web browsers can't read COM1 directly

Software example: com0com or Virtual Serial Port Driver

3. Web Interface Side
JavaScript reads from COM3 using Web Serial API

Parses the data: V:1.5(100%) P:500(100%) E:1

Updates graphs and colors in real-time
