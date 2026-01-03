from flask import Flask, render_template_string, jsonify
import threading
import time
import sqlite3
import os
from datetime import datetime
import serial
import re

app = Flask(__name__)

# Configuration
class Config:
    DB_NAME = 'industrial_data.db'
    SERIAL_PORT = 'COM3'  # VSPE: COM1 ↔ COM3
    BAUD_RATE = 9600

# Données en temps réel
current_data = {
    'vibration': None,
    'vibration_percent': None,
    'pressure': None,
    'pressure_percent': None,
    'status': None,
    'last_update': None,
    'data_source': 'attente_arduino',
    'serial_active': False
}

# Variables série
ser = None
serial_active = False

def init_db():
    """Initialise la base de données"""
    try:
        conn = sqlite3.connect(Config.DB_NAME)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS sensor_data
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                      vibration REAL,
                      vibration_percent INTEGER,
                      pressure INTEGER,
                      pressure_percent INTEGER,
                      status INTEGER)''')
        conn.commit()
        conn.close()
        print("✅ Base de données initialisée")
    except Exception as e:
        print(f"❌ Erreur BD: {e}")

def save_data(vibration, vibration_percent, pressure, pressure_percent, status):
    """Sauvegarde les données Arduino"""
    try:
        conn = sqlite3.connect(Config.DB_NAME)
        c = conn.cursor()
        c.execute('''INSERT INTO sensor_data 
                     (vibration, vibration_percent, pressure, pressure_percent, status) 
                     VALUES (?, ?, ?, ?, ?)''',
                  (vibration, vibration_percent, pressure, pressure_percent, status))
        conn.commit()
        conn.close()
        print(f"💾 Données sauvegardées: V:{vibration}g P:{pressure} E:{status}")
        return True
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")
        return False

# === LECTURE SÉRIE ARDUINO ===
def lire_arduino_serial():
    """Lit les données série d'Arduino en continu"""
    global current_data, ser, serial_active
    
    print(f"🔄 Tentative connexion série sur {Config.SERIAL_PORT}...")
    time.sleep(2)  # Attendre
    
    while True:
        try:
            if ser and hasattr(ser, 'is_open') and ser.is_open:
                ser.close()
                time.sleep(1)
            
            ser = serial.Serial(
                port=Config.SERIAL_PORT,
                baudrate=Config.BAUD_RATE,
                timeout=1
            )
            
            if ser.is_open:
                serial_active = True
                print(f"✅ Connexion série établie sur {Config.SERIAL_PORT}")
                current_data['serial_active'] = True
                current_data['data_source'] = f'arduino_{Config.SERIAL_PORT}'
                
                # Lecture continue
                while serial_active and ser and ser.is_open:
                    try:
                        if ser.in_waiting > 0:
                            line = ser.readline().decode('utf-8', errors='ignore').strip()
                            
                            if line and line != 'TEST_CONNEXION':
                                if line.startswith('DEBUG:'):
                                    line = line.replace('DEBUG:', '').strip()
                                
                                print(f"📨 Donnée brute: '{line}'")
                                traiter_donnees_arduino(line)
                                
                        time.sleep(0.1)
                        
                    except Exception as e:
                        print(f"⚠️ Erreur lecture: {e}")
                        time.sleep(1)
                        
        except Exception as e:
            print(f"❌ Erreur connexion: {e}")
            current_data['serial_active'] = False
            current_data['data_source'] = 'erreur_connexion'
            time.sleep(5)

def traiter_donnees_arduino(line):
    """Traite une ligne de données Arduino"""
    try:
        # Format Arduino: V:1.5(85%) P:500(83%) E:1
        vib_match = re.search(r'V:([\d.]+)\((\d+)%\)', line)
        press_match = re.search(r'P:(\d+)\((\d+)%\)', line)
        status_match = re.search(r'E:(\d+)', line)
        
        if vib_match and press_match and status_match:
            vibration = float(vib_match.group(1))
            vibration_percent = int(vib_match.group(2))
            pressure = int(press_match.group(1))
            pressure_percent = int(press_match.group(2))
            status = int(status_match.group(1))
            
            current_time = datetime.now()
            
            # Mettre à jour les données temps réel
            current_data.update({
                'vibration': vibration,
                'vibration_percent': vibration_percent,
                'pressure': pressure,
                'pressure_percent': pressure_percent,
                'status': status,
                'last_update': current_time.isoformat(),
                'data_source': 'arduino_temps_reel'
            })
            
            # Sauvegarder
            if save_data(vibration, vibration_percent, pressure, pressure_percent, status):
                print(f"✅ Données traitées et sauvegardées")
            
        elif "URGENCE" in line or "ARRET" in line:
            current_time = datetime.now()
            current_data.update({
                'status': 4,
                'last_update': current_time.isoformat(),
                'data_source': 'urgence_arduino'
            })
            print(f"🚨 URGENCE DÉTECTÉE")
            
        else:
            print(f"⚠️ Format non reconnu: {line}")
            
    except Exception as e:
        print(f"❌ Erreur traitement: {e}")

# === ROUTES API ===
@app.route('/api/current')
def api_current():
    """Retourne les données actuelles"""
    return jsonify(current_data)

@app.route('/api/history')
def api_history():
    """Retourne l'historique des données"""
    try:
        conn = sqlite3.connect(Config.DB_NAME)
        c = conn.cursor()
        c.execute('''SELECT timestamp, vibration, vibration_percent, pressure, pressure_percent, status 
                     FROM sensor_data 
                     ORDER BY timestamp DESC LIMIT 20''')
        data = c.fetchall()
        conn.close()
        
        history = []
        for row in data:
            history.append({
                'timestamp': row[0],
                'vibration': row[1],
                'vibration_percent': row[2],
                'pressure': row[3],
                'pressure_percent': row[4],
                'status': row[5]
            })
        
        print(f"📊 Historique: {len(history)} enregistrements")
        return jsonify(history)
    except Exception as e:
        print(f"❌ Erreur historique: {e}")
        return jsonify([])

@app.route('/api/status')
def api_status():
    """Retourne le statut de la connexion"""
    return jsonify({
        'serial_port': Config.SERIAL_PORT,
        'baud_rate': Config.BAUD_RATE,
        'serial_active': current_data['serial_active'],
        'data_source': current_data['data_source'],
        'last_data_received': current_data['last_update'],
        'has_data': current_data['vibration'] is not None,
        'vibration': current_data['vibration'],
        'pressure': current_data['pressure']
    })

# Le HTML TEMPLATE reste identique à celui que vous avez fourni
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Surveillance Industriel - Arduino COM3</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Arial', sans-serif; }
        body { background: #0f172a; color: #e2e8f0; min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        
        .header { 
            background: #1e293b; 
            padding: 20px; 
            border-radius: 10px; 
            margin-bottom: 20px; 
            border-left: 4px solid #3b82f6;
            text-align: center;
        }
        
        .header h1 { 
            color: #f8fafc; 
            font-size: 24px; 
            margin-bottom: 10px; 
        }
        
        .header .subtitle { 
            color: #94a3b8; 
            font-size: 14px;
            margin-bottom: 10px;
        }
        
        .connection-info {
            background: #1e293b;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #334155;
            text-align: center;
        }
        
        .status-bar { 
            display: grid; 
            grid-template-columns: repeat(4, 1fr); 
            gap: 15px; 
            margin-bottom: 20px; 
        }
        
        .status-card { 
            background: #1e293b; 
            padding: 20px; 
            border-radius: 8px; 
            border: 1px solid #334155;
            text-align: center;
            min-height: 120px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        
        .status-card.waiting { 
            border: 2px dashed #64748b;
            background: #1e293b;
        }
        
        .status-card.normal { border-color: #10b981; background: #064e3b; }
        .status-card.warning { border-color: #f59e0b; background: #78350f; }
        .status-card.critical { border-color: #ef4444; background: #7f1d1d; }
        
        .status-label { 
            font-size: 12px; 
            color: #94a3b8; 
            text-transform: uppercase; 
            margin-bottom: 10px; 
        }
        
        .status-value { 
            font-size: 24px; 
            font-weight: bold; 
            font-family: 'Courier New', monospace;
            margin-bottom: 5px;
        }
        
        .status-value.waiting {
            color: #64748b;
            font-size: 18px;
        }
        
        .status-unit { 
            font-size: 12px; 
            color: #64748b; 
        }
        
        .status-time { 
            font-size: 10px; 
            color: #64748b; 
            margin-top: 5px; 
        }
        
        .charts-container { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 20px; 
            margin-bottom: 20px; 
        }
        
        .chart-box { 
            background: #1e293b; 
            padding: 20px; 
            border-radius: 8px; 
            border: 1px solid #334155; 
        }
        
        .chart-title { 
            font-size: 16px; 
            margin-bottom: 15px; 
            color: #e2e8f0; 
        }
        
        .chart-wrapper { 
            height: 250px; 
        }
        
        .data-table { 
            background: #1e293b; 
            border-radius: 8px; 
            border: 1px solid #334155; 
            overflow: hidden; 
            margin-bottom: 20px;
        }
        
        .table-header { 
            background: #334155; 
            padding: 15px 20px; 
            font-weight: bold; 
            text-align: center;
        }
        
        .table-row { 
            display: grid; 
            grid-template-columns: 2fr 1fr 1fr 1fr 1fr; 
            padding: 12px 20px; 
            border-bottom: 1px solid #334155; 
        }
        
        .table-row.header { 
            background: #475569; 
            font-weight: bold; 
        }
        
        .table-row:last-child { 
            border-bottom: none; 
        }
        
        .empty-history {
            padding: 30px;
            text-align: center;
            color: #64748b;
            font-style: italic;
        }
        
        .last-update { 
            text-align: center; 
            color: #94a3b8; 
            font-size: 12px; 
            margin-top: 10px; 
        }
        
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 15px;
            border-radius: 6px;
            font-size: 12px;
            z-index: 1000;
            animation: fadeIn 0.5s;
        }
        
        .notification.success {
            background: #10b981;
            color: white;
            border-left: 3px solid #059669;
        }
        
        .notification.warning {
            background: #f59e0b;
            color: white;
            border-left: 3px solid #d97706;
        }
        
        .notification.error {
            background: #ef4444;
            color: white;
            border-left: 3px solid #dc2626;
        }
        
        .notification.info {
            background: #3b82f6;
            color: white;
            border-left: 3px solid #2563eb;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        @media (max-width: 768px) {
            .status-bar, .charts-container { grid-template-columns: 1fr; }
            .table-row { grid-template-columns: 1fr 1fr; font-size: 12px; }
        }
    </style>
</head>
<body>
    <div id="notificationContainer"></div>
    
    <div class="container">
        <div class="header">
            <h1>🏭 SURVEILLANCE INDUSTRIEL - ARDUINO COM3</h1>
            <div class="subtitle">Données temps réel depuis Arduino via COM1 → COM3</div>
            <div class="subtitle" id="portStatus">Connexion: En attente...</div>
        </div>
        
        <div class="connection-info" id="connectionInfo">
            <div>🔄 Connexion série sur <strong id="serialPort">COM3</strong> (baud: 9600)</div>
            <div>📡 Source: <span id="dataSource">Attente Arduino...</span></div>
            <div>⏱️ Dernière donnée: <span id="lastDataTime">Jamais</span></div>
        </div>

        <div class="status-bar">
            <div class="status-card waiting" id="vibrationCard">
                <div class="status-label">VIBRATION</div>
                <div class="status-value waiting" id="vibrationValue">--.-- g</div>
                <div class="status-unit" id="vibrationPercent">--%</div>
                <div class="status-time" id="vibrationTime">--:--:--</div>
            </div>
            
            <div class="status-card waiting" id="pressureCard">
                <div class="status-label">PRESSION</div>
                <div class="status-value waiting" id="pressureValue">---</div>
                <div class="status-unit" id="pressurePercent">--%</div>
                <div class="status-time" id="pressureTime">--:--:--</div>
            </div>
            
            <div class="status-card waiting" id="statusCard">
                <div class="status-label">STATUT SYSTÈME</div>
                <div class="status-value waiting" id="statusValue">ATTENTE</div>
                <div class="status-unit">Code: --</div>
                <div class="status-time" id="statusTime">--:--:--</div>
            </div>
            
            <div class="status-card" id="sourceCard">
                <div class="status-label">ÉTAT CONNEXION</div>
                <div class="status-value" id="connectionValue">⚪ ATTENTE</div>
                <div class="status-unit" id="connectionDetail">COM1 → COM3</div>
                <div class="status-time" id="connectionTime">--:--:--</div>
            </div>
        </div>

        <div class="charts-container">
            <div class="chart-box">
                <div class="chart-title">📈 VIBRATION - ÉVOLUTION</div>
                <div class="chart-wrapper">
                    <canvas id="vibrationChart"></canvas>
                </div>
                <div id="vibrationChartInfo">En attente de données...</div>
            </div>
            
            <div class="chart-box">
                <div class="chart-title">📊 PRESSION - ÉVOLUTION</div>
                <div class="chart-wrapper">
                    <canvas id="pressureChart"></canvas>
                </div>
                <div id="pressureChartInfo">En attente de données...</div>
            </div>
        </div>

        <div class="data-table">
            <div class="table-header">📋 HISTORIQUE DES DONNÉES</div>
            <div class="table-row header">
                <div>HORODATAGE</div><div>VIBRATION</div><div>% VIB</div><div>PRESSION</div><div>STATUT</div>
            </div>
            <div id="historyTable">
                <div class="empty-history">Aucune donnée reçue...</div>
            </div>
        </div>

        <div class="last-update">
            <span id="pageUpdate">Page chargée à: --:--:--</span> | 
            <span id="dataUpdate">Dernière donnée: --:--:--</span>
            <button onclick="checkStatus()" style="margin-left: 10px; padding: 5px 10px; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer;">
                🔍 Vérifier
            </button>
        </div>
    </div>

    <script>
        let vibrationChart, pressureChart;
        let historicalData = [];
        
        function initializeCharts() {
            const vibCtx = document.getElementById('vibrationChart').getContext('2d');
            vibrationChart = new Chart(vibCtx, {
                type: 'line', data: { labels: [], datasets: [{
                    label: 'Vibration (g)', data: [], borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)', borderWidth: 2, tension: 0.4, fill: true
                }]}, options: {
                    responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },
                    scales: {
                        x: { display: true, grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#94a3b8', maxTicksLimit: 6 } },
                        y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#94a3b8' } }
                    }
                }
            });

            const pressCtx = document.getElementById('pressureChart').getContext('2d');
            pressureChart = new Chart(pressCtx, {
                type: 'line', data: { labels: [], datasets: [{
                    label: 'Pression', data: [], borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)', borderWidth: 2, tension: 0.4, fill: true
                }]}, options: {
                    responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },
                    scales: {
                        x: { display: true, grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#94a3b8', maxTicksLimit: 6 } },
                        y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#94a3b8' } }
                    }
                }
            });
        }
        
        function updateData() {
            fetch('/api/current')
                .then(response => response.json())
                .then(data => {
                    updateDisplay(data);
                    updateConnectionStatus(data);
                    updateHistory();
                })
                .catch(error => {
                    console.error('Erreur:', error);
                });
        }
        
        function updateDisplay(data) {
            // Vibration
            const vibValue = data.vibration !== null ? data.vibration.toFixed(2) + ' g' : '--.-- g';
            const vibPercent = data.vibration_percent !== null ? data.vibration_percent + '%' : '--%';
            
            document.getElementById('vibrationValue').textContent = vibValue;
            document.getElementById('vibrationPercent').textContent = vibPercent;
            document.getElementById('vibrationTime').textContent = formatTime(data.last_update);
            
            // Pression
            const pressValue = data.pressure !== null ? data.pressure.toString() : '---';
            const pressPercent = data.pressure_percent !== null ? data.pressure_percent + '%' : '--%';
            
            document.getElementById('pressureValue').textContent = pressValue;
            document.getElementById('pressurePercent').textContent = pressPercent;
            document.getElementById('pressureTime').textContent = formatTime(data.last_update);
            
            // Statut
            updateStatus(data.status, data.last_update);
            
            // Source
            document.getElementById('dataSource').textContent = 
                data.data_source === 'arduino_temps_reel' ? 'Arduino (temps réel)' : data.data_source;
            document.getElementById('lastDataTime').textContent = 
                data.last_update ? formatTime(data.last_update) : 'Jamais';
            
            // Graphiques
            if (data.vibration !== null && data.pressure !== null) {
                updateCharts(data);
            }
            
            document.getElementById('pageUpdate').textContent = 
                'Page chargée à: ' + new Date().toLocaleTimeString('fr-FR');
            document.getElementById('dataUpdate').textContent = 
                'Dernière donnée: ' + formatTime(data.last_update);
        }
        
        function formatTime(timestamp) {
            if (!timestamp) return '--:--:--';
            try {
                return new Date(timestamp).toLocaleTimeString('fr-FR');
            } catch {
                return '--:--:--';
            }
        }
        
        function updateStatus(status, timestamp) {
            const card = document.getElementById('statusCard');
            const value = document.getElementById('statusValue');
            const time = document.getElementById('statusTime');
            
            if (status === null) {
                card.className = 'status-card waiting';
                value.textContent = 'ATTENTE';
                value.className = 'status-value waiting';
                document.querySelector('#statusCard .status-unit').textContent = 'Code: --';
                time.textContent = '--:--:--';
                return;
            }
            
            let text, cls;
            switch(status) {
                case 1: text = 'NORMAL'; cls = 'normal'; break;
                case 2: text = 'ALERTE'; cls = 'warning'; break;
                case 3: text = 'CRITIQUE'; cls = 'critical'; break;
                case 4: text = 'URGENCE'; cls = 'critical'; break;
                default: text = 'INCONNU'; cls = 'waiting';
            }
            
            card.className = `status-card ${cls}`;
            value.textContent = text;
            value.className = 'status-value';
            document.querySelector('#statusCard .status-unit').textContent = `Code: ${status}`;
            time.textContent = formatTime(timestamp);
        }
        
        function updateCharts(data) {
            if (!vibrationChart || !pressureChart) return;
            
            const now = new Date();
            const timeLabel = now.toLocaleTimeString('fr-FR');
            
            historicalData.push({
                time: timeLabel,
                vibration: data.vibration,
                pressure: data.pressure
            });
            
            if (historicalData.length > 20) historicalData.shift();
            
            vibrationChart.data.labels = historicalData.map(d => d.time);
            vibrationChart.data.datasets[0].data = historicalData.map(d => d.vibration);
            vibrationChart.update('none');
            
            pressureChart.data.labels = historicalData.map(d => d.time);
            pressureChart.data.datasets[0].data = historicalData.map(d => d.pressure);
            pressureChart.update('none');
            
            document.getElementById('vibrationChartInfo').textContent = 
                `Dernière: ${data.vibration.toFixed(2)}g | ${historicalData.length} points`;
            document.getElementById('pressureChartInfo').textContent = 
                `Dernière: ${data.pressure} | ${historicalData.length} points`;
        }
        
        function updateConnectionStatus(data) {
            const statusElem = document.getElementById('connectionStatus');
            const value = document.getElementById('connectionValue');
            const detail = document.getElementById('connectionDetail');
            const port = document.getElementById('portStatus');
            
            if (data.data_source.includes('arduino')) {
                statusElem.className = 'connection-status connected';
                value.textContent = '🟢 CONNECTÉ';
                detail.textContent = 'Arduino → COM1 → COM3';
                port.textContent = 'Connexion: Arduino connecté';
            } else if (data.data_source === 'erreur_connexion') {
                statusElem.className = 'connection-status disconnected';
                value.textContent = '🔴 ERREUR';
                detail.textContent = 'Port COM3 inaccessible';
                port.textContent = 'Connexion: Erreur COM3';
            } else {
                statusElem.className = 'connection-status waiting';
                value.textContent = '🟡 ATTENTE';
                detail.textContent = 'En attente Arduino...';
                port.textContent = 'Connexion: En attente';
            }
        }
        
        function updateHistory() {
            fetch('/api/history')
                .then(response => response.json())
                .then(history => {
                    const table = document.getElementById('historyTable');
                    
                    if (history.length === 0) {
                        table.innerHTML = '<div class="empty-history">Aucune donnée reçue...</div>';
                        return;
                    }
                    
                    let html = '';
                    history.slice(0, 10).forEach(item => {
                        const time = new Date(item.timestamp);
                        const timeStr = time.toLocaleTimeString('fr-FR');
                        
                        let statusText, statusColor;
                        switch(item.status) {
                            case 1: statusText = 'NORMAL'; statusColor = '#10b981'; break;
                            case 2: statusText = 'ALERTE'; statusColor = '#f59e0b'; break;
                            case 3: statusText = 'CRITIQUE'; statusColor = '#ef4444'; break;
                            case 4: statusText = 'URGENCE'; statusColor = '#dc2626'; break;
                            default: statusText = '--'; statusColor = '#64748b';
                        }
                        
                        html += `
                            <div class="table-row">
                                <div>${timeStr}</div>
                                <div>${item.vibration !== null ? item.vibration.toFixed(2) + ' g' : '--.--'}</div>
                                <div>${item.vibration_percent !== null ? item.vibration_percent + '%' : '--%'}</div>
                                <div>${item.pressure !== null ? item.pressure : '--'}</div>
                                <div style="color: ${statusColor}">${statusText}</div>
                            </div>
                        `;
                    });
                    
                    table.innerHTML = html;
                })
                .catch(error => console.error('Erreur historique:', error));
        }
        
        function checkStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(status => {
                    alert(`État système:
• Connexion: ${status.serial_active ? 'ACTIVE' : 'INACTIVE'}
• Source: ${status.data_source}
• Dernière donnée: ${status.last_data_received || 'Jamais'}
• Données reçues: ${status.has_data ? 'OUI' : 'NON'}
• Vibration: ${status.vibration || '--'}
• Pression: ${status.pressure || '--'}`);
                });
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            initializeCharts();
            updateData();
            updateHistory();
            setInterval(updateData, 2000);
            setInterval(updateHistory, 5000);
        });
    </script>
</body>
</html>
'''

@app.route('/')
def dashboard():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    init_db()
    
    # Démarrer la lecture série
    serial_thread = threading.Thread(target=lire_arduino_serial, daemon=True)
    serial_thread.start()
    
    print("=" * 60)
    print("🚀 SERVEUR ARDUINO - SANS DEBUG")
    print("=" * 60)
    print("📡 Port: COM3")
    print("🔌 VSPE: COM1 ↔ COM3")
    print("🌐 Site: http://localhost:5000")
    print("=" * 60)
    print("✅ Prêt à recevoir les données Arduino...")
    print("=" * 60)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)  # ← DEBUG DÉSACTIVÉ