import os
import json
import random
import sqlite3
from datetime import datetime
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

# Load Environment Variables from .env file
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
DB_FILE = "asha_platform.db"

# Initialize SQLite Database (Day 4 & Day 6)
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Calls Log Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            call_type TEXT,
            status TEXT,
            sentiment TEXT,
            failure_reason TEXT,
            queries_count INTEGER,
            active_agent TEXT,
            language TEXT
        )
    """)
    
    # Inventory Table (Day 4)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            key TEXT PRIMARY KEY,
            name TEXT,
            price INTEGER,
            discount INTEGER,
            unit TEXT,
            stock INTEGER
        )
    """)
    
    # Populate Default Inventory if empty
    cursor.execute("SELECT COUNT(*) FROM inventory")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
            INSERT INTO inventory VALUES (?, ?, ?, ?, ?, ?)
        """, [
            ("turmeric", "Organic Turmeric Powder", 120, 15, "250g", 15),
            ("saree", "Handloom Cotton Saree", 1850, 200, "piece", 4),
            ("honey", "Raw Wild Honey", 350, 30, "500g", 8),
            ("rice", "Basmati Rice", 90, 10, "1kg", 25)
        ])
        
    conn.commit()
    conn.close()

init_db()

# Log Call Outcome (Day 6 & Day 8)
def record_call_outcome(call_type, status, sentiment="NEUTRAL", failure_reason="N/A", queries_count=1, active_agent="Asha Main Agent", language="English"):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO calls (timestamp, call_type, status, sentiment, failure_reason, queries_count, active_agent, language)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), call_type, status, sentiment, failure_reason, queries_count, active_agent, language))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

# Get Dynamic Dashboard Analytics (Day 6 Dashboard)
def get_analytics_data():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM calls")
        total_calls = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM calls WHERE status = 'SUCCESS'")
        successful_calls = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM calls WHERE status = 'FAILED'")
        failed_calls = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM calls WHERE status = 'ACTIVE'")
        active_calls = cursor.fetchone()[0]
        
        cursor.execute("SELECT id, timestamp, call_type, active_agent, status, sentiment, failure_reason FROM calls ORDER BY id DESC LIMIT 6")
        recent_calls = cursor.fetchall()

        cursor.execute("SELECT key, name, price, stock FROM inventory")
        inventory_items = cursor.fetchall()
        
        conn.close()
        
        success_rate = round((successful_calls / total_calls * 100), 1) if total_calls > 0 else 0.0
        
        return {
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "active_calls": active_calls,
            "success_rate": success_rate,
            "recent_calls": recent_calls,
            "inventory": inventory_items
        }
    except Exception as e:
        print(f"Analytics DB Error: {e}")
        return {"total_calls": 0, "successful_calls": 0, "failed_calls": 0, "active_calls": 0, "success_rate": 0, "recent_calls": [], "inventory": []}

# Global Session State
session_state = {
    "active_agent": "Asha Main Agent",
    "pending_escalation": False,
    "query_count": 0,
    "current_language": "English"
}

# Sentiment Analyzer (Day 8)
def analyze_sentiment(text):
    text = text.lower()
    positive_words = ["great", "thank", "good", "nice", "awesome", "perfect", "yes", "helpful"]
    negative_words = ["bad", "worst", "angry", "damaged", "defective", "scam", "useless", "fail", "slow"]
    
    if any(w in text for w in positive_words):
        return "POSITIVE"
    elif any(w in text for w in negative_words):
        return "NEGATIVE"
    return "NEUTRAL"

# Murf TTS Voice Generation (Day 5)
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
        with urllib.request.urlopen(req, timeout=4) as resp:
            res_data = json.loads(resp.read().decode())
            return res_data.get("audioFile", "")
    except Exception as e:
        print(f"TTS Bypass: {e}")
        return ""

# Core Engine Processing Logic (Days 1, 3, 4, 7, 8, 9)
def process_query(query_text, call_type="Inbound", lang="English"):
    global session_state
    session_state["current_language"] = lang
    query_clean = query_text.lower().strip()
    session_state["query_count"] += 1
    sentiment = analyze_sentiment(query_text)

    # 1. End Call Action
    if query_clean in ["hangup", "end call", "bye", "exit", "quit"]:
        agent = session_state["active_agent"]
        record_call_outcome(call_type, "SUCCESS", sentiment, "User Ended Call", session_state["query_count"], agent, lang)
        session_state = {"active_agent": "Asha Main Agent", "pending_escalation": False, "query_count": 0, "current_language": lang}
        return "Call session ended. Thank you for using Asha AI Platform!", "Asha Main Agent", sentiment

    # 2. Day 9 Sub-Agent: Returns & Refunds Specialist
    if session_state["active_agent"] == "Returns Specialist":
        if any(w in query_clean for w in ["yes", "yeah", "sure", "proceed", "agree", "raise"]):
            ref_id = f"RET-{random.randint(1000, 9999)}"
            record_call_outcome(call_type, "SUCCESS", "POSITIVE", "N/A", session_state["query_count"], "Returns Specialist", lang)
            session_state["active_agent"] = "Asha Main Agent"
            return f"Refund ticket #{ref_id} created successfully! Courier pickup scheduled within 24 hrs. Transferring you back to Asha Main Agent.", "Asha Main Agent", "POSITIVE"
        else:
            record_call_outcome(call_type, "SUCCESS", sentiment, "N/A", session_state["query_count"], "Returns Specialist", lang)
            return "Our 7-day return policy covers full replacement or refund. Shall I create a return ticket for you?", "Returns Specialist", sentiment

    # 3. Day 9 Specialist Trigger
    specialist_keywords = ["refund", "return", "damaged", "replacement", "defective", "wrong item", "exchange"]
    if any(k in query_clean for k in specialist_keywords):
        session_state["active_agent"] = "Returns Specialist"
        record_call_outcome(call_type, "SUCCESS", sentiment, "Handoff to Specialist", session_state["query_count"], "Main -> Specialist", lang)
        
        handoff_response = (
            "Connecting you to Returns Specialist... "
            "[Handoff Complete] Namaste! I am the Returns Specialist. "
            f"I understand your issue regarding '{query_text}'. Should I process a return request now?"
        )
        return handoff_response, "Returns Specialist", sentiment

    # 4. Day 7 Human Escalation Trigger
    if any(k in query_clean for k in ["manager", "human", "supervisor", "escalate", "store manager"]):
        session_state["pending_escalation"] = True
        record_call_outcome(call_type, "SUCCESS", sentiment, "Escalation Requested", session_state["query_count"], "Asha Main Agent", lang)
        return "I can escalate this directly to our Store Manager. Should I generate an escalation ticket for you?", "Asha Main Agent", sentiment

    if session_state["pending_escalation"]:
        if any(word in query_clean for word in ["yes", "yeah", "ok", "sure", "proceed"]):
            ref_id = f"HUM-{random.randint(1000, 9999)}"
            record_call_outcome(call_type, "SUCCESS", "POSITIVE", "Human Escalated", session_state["query_count"], "Human Agent", lang)
            session_state["pending_escalation"] = False
            return f"Human Escalation Ticket #{ref_id} generated. Store Manager will call you within 15 minutes.", "Asha Main Agent", "POSITIVE"
        else:
            session_state["pending_escalation"] = False

    # 5. Day 4 SQLite Inventory Search
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT name, price, discount, unit, stock FROM inventory")
        items = cursor.fetchall()
        conn.close()

        for name, price, discount, unit, stock in items:
            if name.lower() in query_clean or any(word in query_clean for word in name.lower().split()):
                final_price = price - discount
                record_call_outcome(call_type, "SUCCESS", sentiment, "N/A", session_state["query_count"], "Asha Main Agent", lang)
                
                # Day 3 Vernacular Multilingual Response
                if lang == "Hindi":
                    return f"नमस्ते! {name} का मूल्य ₹{price} है। छूट: ₹{discount}। अंतिम मूल्य: ₹{final_price}। स्टॉक: {stock} units.", "Asha Main Agent", sentiment
                elif lang == "Tamil":
                    return f"வணக்கம்! {name} விலை ₹{price}. தள்ளுபடி: ₹{discount}. இறுதி விலை: ₹{final_price}. கையிருப்பு: {stock} units.", "Asha Main Agent", sentiment
                else:
                    return f"Namaste! For {name}, the standard price is ₹{price}. Discount: ₹{discount}. Final Price: ₹{final_price}. Stock: {stock} ({unit}).", "Asha Main Agent", sentiment
    except Exception as e:
        print(f"Inventory lookup error: {e}")

    # 6. Day 8 Fallback / Unrecognized Handling
    record_call_outcome(call_type, "FAILED", sentiment, "Unrecognized Query", session_state["query_count"], "Asha Main Agent", lang)
    return "Namaste! I didn't recognize that product or action. Try asking for turmeric, saree, honey, rice, or request returns and refunds.", "Asha Main Agent", sentiment

# HTML + CSS (Glassmorphism UI Framework)
HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Asha AI - Master Glassmorphism Dashboard (Days 1-9)</title>
    <style>
        :root {
            --bg-dark: #080b14;
            --glass-bg: rgba(22, 28, 45, 0.65);
            --glass-border: rgba(168, 85, 247, 0.25);
            --primary-purple: #c084fc;
            --accent-pink: #f472b6;
            --accent-cyan: #38bdf8;
            --success-green: #4ade80;
            --warning-yellow: #facc15;
            --danger-red: #f87171;
            --user-blue: #0284c7;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', system-ui, -apple-system, sans-serif; }
        
        body {
            background: radial-gradient(circle at 20% 20%, #1e1b4b 0%, #080b14 60%, #030712 100%);
            color: #f1f5f9;
            padding: 20px;
            min-height: 100vh;
        }

        .dashboard-container {
            max-width: 1280px;
            margin: auto;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .glass-card {
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }

        /* Top Bar Header */
        .header-card {
            padding: 20px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }

        .brand-section {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .brand-logo {
            width: 48px;
            height: 48px;
            border-radius: 14px;
            background: linear-gradient(135deg, #a855f7, #ec4899);
            display: flex;
            justify-content: center;
            align-items: center;
            font-weight: 800;
            font-size: 22px;
            color: #fff;
            box-shadow: 0 0 15px rgba(168, 85, 247, 0.5);
        }

        .brand-info .title { font-size: 22px; font-weight: 800; color: #fff; letter-spacing: -0.5px; }
        .brand-info .subtitle { font-size: 13px; color: var(--accent-cyan); font-weight: 500; }

        .user-section {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .user-name {
            font-size: 14px;
            font-weight: 600;
            color: #e2e8f0;
            background: rgba(255,255,255,0.06);
            padding: 6px 14px;
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .badges-group { display: flex; gap: 10px; align-items: center; }

        .badge {
            padding: 8px 16px;
            border-radius: 30px;
            font-size: 13px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .badge-agent {
            background: linear-gradient(135deg, rgba(168, 85, 247, 0.3), rgba(236, 72, 153, 0.3));
            border: 1px solid var(--primary-purple);
            color: #f3e8ff;
        }

        .badge-lang {
            background: rgba(56, 189, 248, 0.15);
            border: 1px solid var(--accent-cyan);
            color: var(--accent-cyan);
        }

        /* Grid Layout */
        .dashboard-grid {
            display: grid;
            grid-template-columns: 380px 1fr;
            gap: 20px;
        }

        @media (max-width: 960px) {
            .dashboard-grid { grid-template-columns: 1fr; }
        }

        .console-panel {
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .orb-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            padding-bottom: 12px;
        }

        .orb-title { font-size: 15px; font-weight: 600; color: var(--primary-purple); }

        .voice-orb {
            width: 42px;
            height: 42px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--primary-purple), var(--accent-pink));
            box-shadow: 0 0 20px rgba(168, 85, 247, 0.8);
            animation: pulse 2s infinite ease-in-out;
            cursor: pointer;
        }

        .voice-orb.listening {
            background: linear-gradient(135deg, #ef4444, #f97316);
            box-shadow: 0 0 25px rgba(239, 68, 68, 0.9);
            animation: pulse-fast 0.8s infinite ease-in-out;
        }

        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(168, 85, 247, 0.7); }
            70% { transform: scale(1.05); box-shadow: 0 0 0 12px rgba(168, 85, 247, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(168, 85, 247, 0); }
        }

        @keyframes pulse-fast {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.8); }
            50% { transform: scale(1.15); box-shadow: 0 0 0 16px rgba(239, 68, 68, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
        }

        .chat-box {
            height: 320px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 12px;
            padding-right: 6px;
        }

        .chat-box::-webkit-scrollbar { width: 4px; }
        .chat-box::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 4px; }

        .msg {
            padding: 10px 14px;
            border-radius: 14px;
            font-size: 13px;
            line-height: 1.4;
            max-width: 90%;
            word-wrap: break-word;
        }

        .msg-user { background: var(--user-blue); align-self: flex-end; border-bottom-right-radius: 2px; }
        .msg-main { background: rgba(34, 197, 94, 0.25); border: 1px solid var(--success-green); align-self: flex-start; border-bottom-left-radius: 2px; }
        .msg-specialist { background: rgba(168, 85, 247, 0.25); border: 1px solid var(--primary-purple); align-self: flex-start; border-bottom-left-radius: 2px; }

        .controls-box { display: flex; flex-direction: column; gap: 10px; }

        .input-row { display: flex; gap: 8px; align-items: center; }

        input[type="text"], select {
            background: rgba(0,0,0,0.4);
            border: 1px solid var(--glass-border);
            border-radius: 10px;
            color: #fff;
            padding: 10px 12px;
            font-size: 13px;
            outline: none;
        }

        input[type="text"] { flex: 1; }
        input[type="text"]:focus { border-color: var(--primary-purple); }

        .mic-btn {
            background: rgba(255,255,255,0.1);
            border: 1px solid var(--glass-border);
            border-radius: 10px;
            color: #fff;
            padding: 10px 12px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .mic-btn.active {
            background: #ef4444;
            border-color: #f87171;
            box-shadow: 0 0 10px rgba(239, 68, 68, 0.6);
        }

        .btn {
            padding: 10px 14px;
            border-radius: 10px;
            font-size: 12px;
            font-weight: 600;
            border: none;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .btn:hover { opacity: 0.9; transform: translateY(-1px); }
        .btn-purple { background: linear-gradient(135deg, var(--primary-purple), var(--accent-pink)); color: #fff; }
        .btn-green { background: var(--success-green); color: #000; }
        .btn-yellow { background: var(--warning-yellow); color: #000; }
        .btn-cyan { background: var(--accent-cyan); color: #000; }

        .interactive-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }

        .analytics-panel {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .metrics-row {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
        }

        @media (max-width: 600px) {
            .metrics-row { grid-template-columns: repeat(2, 1fr); }
        }

        .metric-card {
            padding: 16px;
            text-align: center;
        }

        .metric-label { font-size: 12px; color: #94a3b8; font-weight: 500; }
        .metric-num { font-size: 24px; font-weight: 800; margin-top: 6px; }

        .data-section {
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .section-title {
            font-size: 15px;
            font-weight: 700;
            color: var(--primary-purple);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        table { width: 100%; border-collapse: collapse; font-size: 12px; }
        th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.06); }
        th { color: #94a3b8; font-weight: 600; text-transform: uppercase; font-size: 11px; }

        .sentiment-badge {
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 700;
        }

        .sent-POSITIVE { background: rgba(74, 222, 128, 0.2); color: var(--success-green); }
        .sent-NEUTRAL { background: rgba(250, 204, 21, 0.2); color: var(--warning-yellow); }
        .sent-NEGATIVE { background: rgba(248, 113, 113, 0.2); color: var(--danger-red); }
    </style>
</head>
<body>
    <div class="dashboard-container">
        
        <!-- Header with Asha AI Branding & Mrithika Profile -->
        <div class="glass-card header-card">
            <div class="brand-section">
                <div class="brand-logo">A</div>
                <div class="brand-info">
                    <div class="title">Asha AI</div>
                    <div class="subtitle">Day 9 Complete Framework Platform</div>
                </div>
            </div>

            <div class="user-section">
                <div class="user-name">👤 Mrittiga</div>
                <div class="badges-group">
                    <div class="badge badge-lang" id="langBadge">🌐 Lang: English</div>
                    <div class="badge badge-agent" id="agentBadge">🤖 Active: Asha Main Agent</div>
                </div>
            </div>
        </div>

        <!-- Main Workspace Grid -->
        <div class="dashboard-grid">
            
            <!-- Left Console Panel -->
            <div class="glass-card console-panel">
                <div class="orb-header">
                    <div class="orb-title">Live Voice & Chat Interface</div>
                    <div class="voice-orb" id="voiceOrb" onclick="toggleSpeechRecognition()" title="Click to Speak"></div>
                </div>

                <div class="chat-box" id="chatBox">
                    <div class="msg msg-main">
                        <b>Asha Main Agent:</b> Namaste! I am your Asha Kirana Platform AI. You can talk to me directly using the mic or type your query.
                    </div>
                </div>

                <div class="controls-box">
                    <div class="input-row">
                        <select id="langSelect" onchange="changeLanguage()">
                            <option value="English">English</option>
                            <option value="Hindi">Hindi (हिंदी)</option>
                            <option value="Tamil">Tamil (தமிழ்)</option>
                        </select>
                        <input type="text" id="userInput" placeholder="Ask 'price of honey' or speak..." onkeypress="if(event.key==='Enter') sendQuery('Inbound')">
                        <button class="mic-btn" id="micBtn" onclick="toggleSpeechRecognition()" title="Voice Input">🎙️</button>
                        <button class="btn btn-purple" onclick="sendQuery('Inbound')">Send</button>
                    </div>

                    <div class="interactive-grid">
                        <button class="btn btn-green" onclick="quickAction('What is the price of Raw Honey?', 'Inbound')">📞 Product Query</button>
                        <button class="btn btn-yellow" onclick="quickAction('I have a defective product and need a refund', 'Inbound')">🔄 Day 9 Handoff</button>
                        <button class="btn btn-cyan" onclick="quickAction('Connect me to the store manager please', 'Outbound')">👨‍💼 Day 7 Escalate</button>
                        <button class="btn btn-purple" onclick="triggerOutboundCall()">📱 Day 2 Outbound</button>
                    </div>
                </div>
            </div>

            <!-- Right Analytics Panel -->
            <div class="analytics-panel">
                
                <div class="metrics-row">
                    <div class="glass-card metric-card">
                        <div class="metric-label">Total Calls</div>
                        <div class="metric-num" style="color: #38bdf8;" id="mTotal">0</div>
                    </div>
                    <div class="glass-card metric-card">
                        <div class="metric-label">Successful</div>
                        <div class="metric-num" style="color: #4ade80;" id="mSuccess">0</div>
                    </div>
                    <div class="glass-card metric-card">
                        <div class="metric-label">Failed/Fallbacks</div>
                        <div class="metric-num" style="color: #f87171;" id="mFailed">0</div>
                    </div>
                    <div class="glass-card metric-card">
                        <div class="metric-label">Success Rate</div>
                        <div class="metric-num" style="color: #facc15;" id="mRate">0%</div>
                    </div>
                </div>

                <div class="glass-card data-section">
                    <div class="section-title">
                        <span>📦 Day 4 SQLite Inventory Database</span>
                        <span style="font-size:11px; color:#94a3b8;">Real-Time Stock Engine</span>
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>Item Code</th>
                                <th>Product Name</th>
                                <th>Price</th>
                                <th>Stock</th>
                            </tr>
                        </thead>
                        <tbody id="inventoryBody">
                            <tr><td colspan="4">Loading SQLite Data...</td></tr>
                        </tbody>
                    </table>
                </div>

                <div class="glass-card data-section">
                    <div class="section-title">
                        <span>📊 Real-Time Call Analytics & Sentiment Log</span>
                        <span style="font-size:11px; color:#94a3b8;">Days 6, 8 & 9 Tracking</span>
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Type</th>
                                <th>Agent</th>
                                <th>Status</th>
                                <th>Sentiment</th>
                                <th>Reason</th>
                            </tr>
                        </thead>
                        <tbody id="logsBody">
                            <tr><td colspan="6">Loading Call Logs...</td></tr>
                        </tbody>
                    </table>
                </div>

            </div>

        </div>
    </div>

    <script>
        let currentLang = "English";
        let recognition = null;
        let isListening = false;

        // Initialize Web Speech API for Mic Listening
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;

            recognition.onstart = function() {
                isListening = true;
                document.getElementById('micBtn').classList.add('active');
                document.getElementById('voiceOrb').classList.add('listening');
            };

            recognition.onresult = function(event) {
                const transcript = event.results[0][0].transcript;
                document.getElementById('userInput').value = transcript;
                sendQuery('Inbound', transcript);
            };

            recognition.onerror = function(event) {
                console.error("Speech Recognition Error:", event.error);
                stopListening();
            };

            recognition.onend = function() {
                stopListening();
            };
        }

        function toggleSpeechRecognition() {
            if (!recognition) {
                alert("Speech recognition is not supported in this browser. Try Google Chrome or Edge.");
                return;
            }
            if (isListening) {
                recognition.stop();
                stopListening();
            } else {
                if(currentLang === 'Hindi') recognition.lang = 'hi-IN';
                else if(currentLang === 'Tamil') recognition.lang = 'ta-IN';
                else recognition.lang = 'en-IN';
                
                recognition.start();
            }
        }

        function stopListening() {
            isListening = false;
            document.getElementById('micBtn').classList.remove('active');
            document.getElementById('voiceOrb').classList.remove('listening');
        }

        function speakText(text) {
            // Web Speech Synthesis Engine (Fallback & Real-time Auto Read)
            if ('speechSynthesis' in window) {
                window.speechSynthesis.cancel(); // Stop any previous speech
                let utterance = new SpeechSynthesisUtterance(text);
                if (currentLang === 'Hindi') utterance.lang = 'hi-IN';
                else if (currentLang === 'Tamil') utterance.lang = 'ta-IN';
                else utterance.lang = 'en-IN';
                
                utterance.rate = 1.0;
                utterance.pitch = 1.0;
                window.speechSynthesis.speak(utterance);
            }
        }

        function changeLanguage() {
            currentLang = document.getElementById('langSelect').value;
            document.getElementById('langBadge').innerText = "🌐 Lang: " + currentLang;
        }

        async function fetchDashboardData() {
            try {
                let res = await fetch('/api/analytics');
                let data = await res.json();

                document.getElementById('mTotal').innerText = data.total_calls || 0;
                document.getElementById('mSuccess').innerText = data.successful_calls || 0;
                document.getElementById('mFailed').innerText = data.failed_calls || 0;
                document.getElementById('mRate').innerText = (data.success_rate || 0) + '%';

                let invBody = document.getElementById('inventoryBody');
                if(data.inventory && data.inventory.length > 0) {
                    invBody.innerHTML = data.inventory.map(item => `
                        <tr>
                            <td><code>${item[0]}</code></td>
                            <td><b>${item[1]}</b></td>
                            <td>₹${item[2]}</td>
                            <td><span style="color:${item[3] > 5 ? '#4ade80' : '#f87171'}">${item[3]} units</span></td>
                        </tr>
                    `).join('');
                }

                let logsBody = document.getElementById('logsBody');
                if(!data.recent_calls || data.recent_calls.length === 0) {
                    logsBody.innerHTML = '<tr><td colspan="6" style="text-align:center;">No activity logged yet.</td></tr>';
                    return;
                }

                logsBody.innerHTML = data.recent_calls.map(c => `
                    <tr>
                        <td>#${c[0]}</td>
                        <td><span style="color:${c[2] === 'Outbound' ? '#38bdf8' : '#c084fc'}">${c[2] || 'Inbound'}</span></td>
                        <td style="font-weight:600;">${c[3]}</td>
                        <td style="color:${c[4] === 'SUCCESS' ? '#4ade80' : '#f87171'}; font-weight:700;">${c[4]}</td>
                        <td><span class="sentiment-badge sent-${c[5]}">${c[5]}</span></td>
                        <td style="color:#94a3b8;">${c[6]}</td>
                    </tr>
                `).join('');
            } catch(e) {
                console.error("Dashboard Sync Error:", e);
            }
        }

        async function sendQuery(callType = "Inbound", overrideQuery = null) {
            let input = document.getElementById('userInput');
            let query = overrideQuery || input.value.trim();
            if(!query) return;

            let chatBox = document.getElementById('chatBox');
            chatBox.innerHTML += `<div class="msg msg-user"><b>Caller (${callType}):</b> ${query}</div>`;
            if(!overrideQuery) input.value = '';
            chatBox.scrollTop = chatBox.scrollHeight;

            try {
                let res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        query: query,
                        call_type: callType,
                        language: currentLang
                    })
                });

                let data = await res.json();
                let agentName = data.agent || "Asha Main Agent";
                let speechText = data.speech || "System response error.";

                document.getElementById('agentBadge').innerText = '🤖 Active: ' + agentName;

                let msgClass = agentName === 'Returns Specialist' ? 'msg msg-specialist' : 'msg msg-main';
                chatBox.innerHTML += `<div class="${msgClass}"><b>${agentName}:</b> ${speechText}</div>`;
                chatBox.scrollTop = chatBox.scrollHeight;

                // 🔊 Automatic Live Speech Output
                if(data.audio) {
                    let audio = new Audio(data.audio);
                    audio.play().catch(() => speakText(speechText));
                } else {
                    speakText(speechText);
                }

                fetchDashboardData();
            } catch(e) {
                console.error("Chat Error:", e);
            }
        }

        function quickAction(text, callType) {
            sendQuery(callType, text);
        }

        function triggerOutboundCall() {
            let prompt = "Automated Call: Reminder regarding your pending order item Basmati Rice.";
            sendQuery("Outbound", prompt);
        }

        fetchDashboardData();
        setInterval(fetchDashboardData, 5000);
    </script>
</body>
</html>
"""

class AshaPlatformHandler(BaseHTTPRequestHandler):
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
        if self.path == '/api/chat':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                req_json = json.loads(post_data.decode('utf-8'))
                caller_query = req_json.get("query", "")
                call_type = req_json.get("call_type", "Inbound")
                lang = req_json.get("language", "English")
                
                response_text, current_agent, sentiment = process_query(caller_query, call_type, lang)
                
                audio_url = ""
                try:
                    audio_url = generate_murf_tts(response_text)
                except Exception as tts_err:
                    print(f"TTS Bypass: {tts_err}")

                reply_payload = {
                    "speech": response_text,
                    "agent": current_agent,
                    "sentiment": sentiment,
                    "audio": audio_url
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(reply_payload).encode('utf-8'))
                
            except Exception as e:
                print(f"POST Processing Error: {e}")
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "speech": "An error occurred while processing your request.",
                    "agent": "Asha Main Agent",
                    "sentiment": "NEUTRAL",
                    "audio": ""
                }).encode('utf-8'))

def run_server():
    server_address = ('127.0.0.1', 8000)
    httpd = HTTPServer(server_address, AshaPlatformHandler)
    print("=========================================================================")
    print("🚀 Asha AI Master Glassmorphism Dashboard Running on http://127.0.0.1:8000")
    print("=========================================================================")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()