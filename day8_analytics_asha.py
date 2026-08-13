import os
import json
import random
import sqlite3
from datetime import datetime
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

# Load environment variables from .env
def load_env_file(filepath=".env"):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip("'\"")

load_env_file()

MURF_API_KEY = os.getenv("MURF_API_KEY")
DB_FILE = "call_analytics.db"

# Initialize SQLite Database for Call Analytics
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            status TEXT,
            failure_reason TEXT,
            queries_count INTEGER,
            has_escalation INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()

def record_call_outcome(status, failure_reason="N/A", queries_count=1, has_escalation=0):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO calls (timestamp, status, failure_reason, queries_count, has_escalation)
        VALUES (?, ?, ?, ?, ?)
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), status, failure_reason, queries_count, has_escalation))
    conn.commit()
    conn.close()

def get_analytics_data():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM calls")
    total_calls = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM calls WHERE status = 'SUCCESS'")
    successful_calls = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM calls WHERE status = 'FAILED'")
    failed_calls = cursor.fetchone()[0]
    
    cursor.execute("SELECT failure_reason, COUNT(*) FROM calls WHERE status = 'FAILED' GROUP BY failure_reason")
    failure_breakdown = dict(cursor.fetchall())
    
    cursor.execute("SELECT id, timestamp, status, failure_reason, queries_count FROM calls ORDER BY id DESC LIMIT 5")
    recent_calls = cursor.fetchall()
    
    conn.close()
    
    success_rate = round((successful_calls / total_calls * 100), 1) if total_calls > 0 else 0.0
    
    return {
        "total_calls": total_calls,
        "successful_calls": successful_calls,
        "failed_calls": failed_calls,
        "success_rate": success_rate,
        "failure_breakdown": failure_breakdown,
        "recent_calls": recent_calls
    }

INVENTORY = {
    "turmeric": {"name": "Organic Turmeric Powder", "price": 120, "discount": 15, "unit": "250g", "stock": 15},
    "saree": {"name": "Handloom Cotton Saree", "price": 1850, "discount": 200, "unit": "piece", "stock": 4},
    "honey": {"name": "Raw Honey", "price": 350, "discount": 30, "unit": "500g", "stock": 8},
    "rice": {"name": "Basmati Rice", "price": 90, "discount": 10, "unit": "1kg", "stock": 25}
}

session_state = {
    "pending_escalation": False,
    "issue_type": None,
    "user_query": None,
    "query_count": 0
}

def generate_murf_tts(text):
    if not MURF_API_KEY:
        return ""

    url = "https://api.murf.ai/v1/speech/generate"
    headers = {
        "api-key": MURF_API_KEY,
        "token": MURF_API_KEY,
        "Content-Type": "application/json"
    }
    payload = json.dumps({
        "voiceId": "en-IN-aarav",
        "style": "Conversational",
        "text": text,
        "format": "MP3"
    }).encode('utf-8')

    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req) as resp:
            res_data = json.loads(resp.read().decode())
            return res_data.get("audioFile", "")
    except Exception as e:
        print(f"TTS Error: {e}")
        return ""

def process_query(query_text):
    global session_state
    query_clean = query_text.lower().strip()
    session_state["query_count"] += 1

    # End call commands
    if query_clean in ["hangup", "end call", "bye", "exit", "quit"]:
        if session_state["query_count"] > 1:
            record_call_outcome("SUCCESS", failure_reason="N/A", queries_count=session_state["query_count"])
            msg = "Call ended successfully. Thank you for calling Asha AI Kirana Store!"
        else:
            record_call_outcome("FAILED", failure_reason="User Hangup Prematurely", queries_count=session_state["query_count"])
            msg = "Call ended before enquiry completion."
        session_state = {"pending_escalation": False, "issue_type": None, "user_query": None, "query_count": 0}
        return msg

    if session_state["pending_escalation"]:
        if any(word in query_clean for word in ["yes", "yeah", "ok", "sure", "proceed", "agree"]):
            ref_id = f"REF-{random.randint(1000, 9999)}"
            record_call_outcome("SUCCESS", failure_reason="N/A", queries_count=session_state["query_count"], has_escalation=1)
            
            session_state["pending_escalation"] = False
            session_state["issue_type"] = None
            session_state["user_query"] = None
            session_state["query_count"] = 0
            
            return f"Thank you. Support ticket created with Reference ID {ref_id}. Store manager will contact you within 24 hours."
        else:
            record_call_outcome("FAILED", failure_reason="Consent Declined", queries_count=session_state["query_count"])
            session_state["pending_escalation"] = False
            session_state["issue_type"] = None
            session_state["user_query"] = None
            session_state["query_count"] = 0
            return "Understood. I have not created a support ticket. Call marked as completed."

    if any(k in query_clean for k in ["refund", "dispute", "double charged", "wrong payment", "fraud"]):
        session_state["pending_escalation"] = True
        session_state["issue_type"] = "Payment Dispute"
        session_state["user_query"] = query_text
        return "I see that you have a payment dispute. May I have your permission to escalate this to our store manager?"

    if any(k in query_clean for k in ["damaged", "broken", "quality issue"]):
        session_state["pending_escalation"] = True
        session_state["issue_type"] = "Quality Complaint"
        session_state["user_query"] = query_text
        return "I apologize for the damaged item. May I have your permission to share your details with our store owner?"

    for key, details in INVENTORY.items():
        if key in query_clean or details["name"].lower() in query_clean:
            final_price = details["price"] - details["discount"]
            # Mark call successful upon retrieving catalog info
            record_call_outcome("SUCCESS", failure_reason="N/A", queries_count=session_state["query_count"])
            return f"Namaste! For {details['name']}, price is ₹{details['price']}. Discount: ₹{details['discount']}. Final: ₹{final_price}. Stock: {details['stock']} units."

    # Unrecognized query
    record_call_outcome("FAILED", failure_reason="Incomplete Enquiry / Unknown Product", queries_count=session_state["query_count"])
    return "Namaste! Product not found in catalog. Try asking for turmeric, saree, honey, or rice."

# Glassmorphism Dashboard UI HTML
HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Day 8 - Asha AI Call Analytics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #311042 100%);
            color: #f8fafc;
            margin: 0;
            padding: 16px;
            min-height: 100vh;
        }
        .container { max-width: 950px; margin: auto; display: flex; flex-direction: column; gap: 20px; }
        
        /* Glassmorphism Card Style */
        .glass-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }

        .header { display: flex; justify-content: space-between; align-items: center; }
        h2, h3 { margin: 0; color: #fb923c; }
        .subtitle { font-size: 12px; color: #cbd5e1; margin-top: 4px; }

        /* Metric Grid */
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-top: 10px; }
        .metric-box {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 16px;
            text-align: center;
        }
        .metric-val { font-size: 28px; font-weight: bold; margin-top: 6px; }
        .val-total { color: #38bdf8; }
        .val-success { color: #4ade80; }
        .val-failed { color: #f87171; }
        .val-rate { color: #facc15; }

        .dashboard-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        @media (max-width: 768px) { .dashboard-layout { grid-template-columns: 1fr; } }

        .chat-box { height: 200px; overflow-y: auto; background: rgba(0, 0, 0, 0.2); border-radius: 8px; padding: 10px; margin: 12px 0; border: 1px solid rgba(255,255,255,0.05); display: flex; flex-direction: column; gap: 6px; }
        .msg { padding: 8px 12px; border-radius: 6px; font-size: 13px; max-width: 85%; }
        .user { background: #0284c7; align-self: flex-end; }
        .asha { background: #16a34a; align-self: flex-start; }

        .input-row { display: flex; gap: 8px; }
        input { flex: 1; padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.2); background: rgba(0,0,0,0.3); color: #fff; outline: none; }
        button { padding: 10px 18px; border: none; background: #f97316; color: #000; font-weight: bold; border-radius: 8px; cursor: pointer; }

        table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.08); }
        th { color: #fb923c; }
        .badge-success { color: #4ade80; font-weight: bold; }
        .badge-failed { color: #f87171; font-weight: bold; }
        audio { width: 100%; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <!-- Dashboard Header & Metrics -->
        <div class="glass-card">
            <div class="header">
                <div>
                    <h2>Asha AI Call Analytics Dashboard</h2>
                    <div class="subtitle">Day 8: Real-Time Performance & Call Outcome Tracking</div>
                </div>
            </div>

            <div class="metrics-grid">
                <div class="metric-box">
                    <div class="subtitle">Total Calls</div>
                    <div class="metric-val val-total" id="m-total">0</div>
                </div>
                <div class="metric-box">
                    <div class="subtitle">Successful Calls</div>
                    <div class="metric-val val-success" id="m-success">0</div>
                </div>
                <div class="metric-box">
                    <div class="subtitle">Failed Calls</div>
                    <div class="metric-val val-failed" id="m-failed">0</div>
                </div>
                <div class="metric-box">
                    <div class="subtitle">Success Rate</div>
                    <div class="metric-val val-rate" id="m-rate">0%</div>
                </div>
            </div>
        </div>

        <div class="dashboard-layout">
            <!-- Agent Interaction Window -->
            <div class="glass-card">
                <h3>Live Call Simulation</h3>
                <div class="chat-box" id="chat">
                    <div class="msg asha"><b>Asha AI:</b> Namaste! Ask product rates or test call scenarios.</div>
                </div>
                <div class="input-row">
                    <input type="text" id="query" placeholder="Ask price or type 'hangup'..." onkeypress="if(event.key==='Enter') sendQuery()">
                    <button onclick="sendQuery()">Call</button>
                </div>
                <audio id="player" controls style="display:none;"></audio>
            </div>

            <!-- Chart Analytics -->
            <div class="glass-card">
                <h3>Outcome Distribution</h3>
                <div style="height: 200px; display: flex; justify-content: center;">
                    <canvas id="outcomeChart"></canvas>
                </div>
            </div>
        </div>

        <!-- Call History Log -->
        <div class="glass-card">
            <h3>Recent Call Logs (Privacy Protected)</h3>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Timestamp</th>
                        <th>Status</th>
                        <th>Failure / Reason</th>
                        <th>Queries</th>
                    </tr>
                </thead>
                <tbody id="logs-body">
                    <tr><td colspan="5">Loading logs...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        let chartInstance = null;

        function initChart(success, failed) {
            const ctx = document.getElementById('outcomeChart').getContext('2d');
            if(chartInstance) chartInstance.destroy();

            chartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Success', 'Failed'],
                    datasets: [{
                        data: [success, failed],
                        backgroundColor: ['#4ade80', '#f87171'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: '#f8fafc' } } }
                }
            });
        }

        async function fetchAnalytics() {
            let res = await fetch('/api/analytics');
            let data = await res.json();

            document.getElementById('m-total').innerText = data.total_calls;
            document.getElementById('m-success').innerText = data.successful_calls;
            document.getElementById('m-failed').innerText = data.failed_calls;
            document.getElementById('m-rate').innerText = data.success_rate + '%';

            initChart(data.successful_calls, data.failed_calls);

            let tbody = document.getElementById('logs-body');
            if(data.recent_calls.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5">No calls logged yet.</td></tr>';
                return;
            }

            tbody.innerHTML = data.recent_calls.map(c => `
                <tr>
                    <td>#${c[0]}</td>
                    <td>${c[1]}</td>
                    <td class="${c[2] === 'SUCCESS' ? 'badge-success' : 'badge-failed'}">${c[2]}</td>
                    <td>${c[3]}</td>
                    <td>${c[4]}</td>
                </tr>
            `).join('');
        }

        async function sendQuery() {
            let input = document.getElementById('query');
            let text = input.value.trim();
            if(!text) return;

            let chat = document.getElementById('chat');
            chat.innerHTML += `<div class="msg user"><b>Caller:</b> ${text}</div>`;
            input.value = '';

            let res = await fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: text})
            });
            let data = await res.json();

            chat.innerHTML += `<div class="msg asha"><b>Asha AI:</b> ${data.speech}</div>`;
            chat.scrollTop = chat.scrollHeight;

            if(data.audio) {
                let player = document.getElementById('player');
                player.src = data.audio;
                player.style.display = 'block';
                player.play();
            }

            fetchAnalytics();
        }

        fetchAnalytics();
    </script>
</body>
</html>
"""

class AshaAIRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/analytics':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(get_analytics_data()).encode('utf-8'))
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            req_json = json.loads(post_data.decode('utf-8'))
            caller_query = req_json.get("query", "")
            
            response_text = process_query(caller_query)
            audio_url = generate_murf_tts(response_text)
            
            reply_payload = {
                "speech": response_text,
                "audio": audio_url
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(reply_payload).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

def run_server():
    server_address = ('127.0.0.1', 8000)
    httpd = HTTPServer(server_address, AshaAIRequestHandler)
    print("=======================================================")
    print("🚀 Day 8 Asha AI Glassmorphism Dashboard on http://127.0.0.1:8000")
    print("=======================================================")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()

