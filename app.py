from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import sqlite3
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_NAME = 'sensor_data.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sensor_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    temperature REAL,
                    humidity REAL,
                    noise INTEGER,
                    luminance INTEGER
                )''')
    conn.commit()
    conn.close()

@app.route('/data', methods=['POST'])
def receive_data():
    data = request.json
    if not data:
        return jsonify({'status': 'fail', 'reason': 'No JSON'}), 400

    try:
        temperature = float(data['temperature'])
        humidity = float(data['humidity'])
        noise = int(data['noise'])
        luminance = int(data['luminance'])
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO sensor_data (timestamp, temperature, humidity, noise, luminance) VALUES (?, ?, ?, ?, ?)",
                  (timestamp, temperature, humidity, noise, luminance))
        conn.commit()
        conn.close()

        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/latest')
def latest_data():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT timestamp, noise FROM sensor_data ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    rows.reverse()  # So oldest is first
    return jsonify(rows)

@app.route('/chart')
def chart_page():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Live Temperature Chart</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <h2>Live Temperature (last 50 readings)</h2>
        <canvas id="tempChart" width="800" height="400"></canvas>
        <script>
            let chart;

            async function fetchDataAndUpdateChart() {
                const response = await fetch('/latest');
                const data = await response.json();
                const labels = data.map(row => row[0]);  // timestamps
                const temps = data.map(row => row[1]);   // temperatures

                if (!chart) {
                    const ctx = document.getElementById('tempChart').getContext('2d');
                    chart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: 'Temperature (°C)',
                                data: temps,
                                borderWidth: 2,
                                borderColor: 'blue',
                                fill: false,
                                tension: 0.1
                            }]
                        },
                        options: {
                            responsive: true,
                            animation: false,
                            scales: {
                                x: {
                                    ticks: { maxTicksLimit: 10 }
                                },
                                y: {
                                    beginAtZero: true
                                }
                            }
                        }
                    });
                } else {
                    chart.data.labels = labels;
                    chart.data.datasets[0].data = temps;
                    chart.update();
                }
            }

            // Initial load
            fetchDataAndUpdateChart();

            // Update every 5 seconds
            setInterval(fetchDataAndUpdateChart, 5000);
        </script>
    </body>
    </html>
    ''')


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=80)
