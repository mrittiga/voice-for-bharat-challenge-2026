import http.server
import socketserver
import json
import os
import sqlite3
import requests
from dotenv import load_dotenv

load_dotenv()

MURF_API_KEY = os.getenv("MURF_API_KEY")
PORT = 8000
DB_FILE = "store_inventory.db"

# ==========================================
# DATABASE SETUP & INITIALIZATION
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS store_info (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT UNIQUE,
            quantity TEXT,
            price_per_unit TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            quantity TEXT,
            status TEXT
        )
    ''')

    cursor.execute("INSERT OR IGNORE INTO store_info VALUES ('timings', 'Subah 8 baje se raat 9 baje tak')")
    
    default_items = [
        ('aata', '25 kg', '₹45 per kg'),
        ('chawal', '50 kg', '₹60 per kg'),
        ('doodh', '10 packets', '₹30 per packet'),
        ('chini', '15 kg', '₹42 per kg'),
        ('tel', '20 liters', '₹140 per liter')
    ]
    cursor.executemany("INSERT OR IGNORE INTO inventory (item_name, quantity, price_per_unit) VALUES (?, ?, ?)", default_items)
    
    conn.commit()
    conn.close()

init_db()

# ==========================================
# VOICE AGENT BUSINESS LOGIC (SQL QUERIES)
# ==========================================
def process_user_query(user_text):
    text = user_text.lower()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Guardrail Check: Direct Payment / Confirmation Refusal
    payment_keywords = ["payment", "paisa", "pay", "confirm", "पेमेंट", "पैसा", "पे", "कन्फर्म"]
    if any(word in text for word in payment_keywords):
        conn.close()
        return "Main direct payment ya order confirm nahi kar sakti. Kripya dukaandaar se 9876543210 par baat karein."

    # Feature 1: Store Timings Query
    timing_keywords = ["timing", "time", "samay", "kab khulegi", "kab band", "समय", "टाइम", "कितने बजे", "कब खुलती", "कब बंद"]
    if any(word in text for word in timing_keywords):
        cursor.execute("SELECT value FROM store_info WHERE key='timings'")
        row = cursor.fetchone()
        conn.close()
        timings = row[0] if row else "Subah 8 baje se raat 9 baje tak"
        return f"Dukaan ka samay hai: {timings}."

    # Feature 2: Grocery Availability & Price Check via DB
    item_map = {
        "aata": ["aata", "آٹا", "आटा"],
        "chawal": ["chawal", "rice", "चावल"],
        "doodh": ["doodh", "milk", "दूध"],
        "chini": ["chini", "sugar", "चीनी"],
        "tel": ["tel", "oil", "तेल"]
    }

    for db_item, keywords in item_map.items():
        if any(kw in text for kw in keywords):
            cursor.execute("SELECT quantity, price_per_unit FROM inventory WHERE item_name=?", (db_item,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return f"Haan! {db_item.capitalize()} stock mein available hai. Quantity {row[0]} hai aur rate {row[1]} hai."
            else:
                return f"Maaf kijiye, {db_item} filhaal stock mein khatam hai."

    # General stock query fallback
    if any(kw in text for kw in ["stock", "samaan", "item", "available", "स्टॉक", "सामान", "आइटम"]):
        cursor.execute("SELECT item_name, quantity FROM inventory")
        rows = cursor.fetchall()
        conn.close()
        items_str = ", ".join([f"{r[0]} ({r[1]})" for r in rows])
        return f"Dukaan mein filhaal yeh items stock mein hain: {items_str}."

    # Feature 3: Order List Drafting via DB
    order_keywords = ["order", "list", "chahiye", "मँगवा", "ऑर्डर", "लिस्ट", "चाहिए"]
    if any(kw in text for kw in order_keywords):
        cursor.execute("INSERT INTO orders (item_name, quantity, status) VALUES (?, ?, ?)", ("Grocery Request", "1", "Drafted"))
        conn.commit()
        conn.close()
        return "Aapka request database order list mein add kar diya gaya hai. Aap ise dukaandaar se verify kar sakte hain."

    conn.close()
    return f"Aapne kaha: {user_text}. Main aapki dukaan ke stock, timing, aur order list mein madad kar sakti hoon."


# ==========================================
# FRONTEND HTML / UI (CHAT & DUAL PANEL)
# ==========================================
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aasha AI - Real-time Voice & Chat Agent</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
        body { background: #0b0f19; color: #ffffff; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 16px; position: relative; overflow-x: hidden; }
        
        .bubble { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.35; z-index: 0; }
        .bubble-1 { width: 300px; height: 300px; background: #f59e0b; top: -5%; left: -10%; }
        .bubble-2 { width: 320px; height: 320px; background: #8b5cf6; bottom: -10%; right: -10%; }

        .container { position: relative; z-index: 10; width: 100%; max-width: 900px; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        @media (max-width: 768px) { .container { grid-template-columns: 1fr; } }

        .card {
            background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
            border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 24px; padding: 24px; text-align: center;
            display: flex; flex-direction: column; justify-content: space-between;
        }

        h1 { font-size: 22px; font-weight: 800; background: linear-gradient(135deg, #fbbf24, #f59e0b, #38bdf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 4px; }
        .subtitle { font-size: 11px; color: #9ca3af; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 16px; text-transform: uppercase; }

        .avatar-container { position: relative; width: 100px; height: 100px; margin: 10px auto 16px auto; display: flex; align-items: center; justify-content: center; }
        .glow-ring { position: absolute; width: 100%; height: 100%; border-radius: 50%; transition: all 0.5s ease; }
        
        .glow-ready { background: radial-gradient(circle, rgba(107,114,128,0.3) 0%, rgba(0,0,0,0) 70%); }
        .glow-connecting { background: radial-gradient(circle, rgba(245,158,11,0.6) 0%, rgba(0,0,0,0) 70%); animation: pulse 1.5s infinite; }
        .glow-listening { background: radial-gradient(circle, rgba(34,197,94,0.6) 0%, rgba(0,0,0,0) 70%); animation: pulse 1s infinite; }
        .glow-speaking { background: radial-gradient(circle, rgba(56,189,248,0.7) 0%, rgba(0,0,0,0) 70%); animation: pulse 0.8s infinite; }
        .glow-ended { background: radial-gradient(circle, rgba(239,68,68,0.4) 0%, rgba(0,0,0,0) 70%); }

        @keyframes pulse { 0% { transform: scale(0.95); opacity: 0.6; } 50% { transform: scale(1.15); opacity: 1; } 100% { transform: scale(0.95); opacity: 0.6; } }

        .avatar { width: 75px; height: 75px; border-radius: 50%; background: rgba(255, 255, 255, 0.08); border: 2px solid rgba(255, 255, 255, 0.2); display: flex; align-items: center; justify-content: center; font-size: 32px; z-index: 2; }

        .status-badge { display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 700; margin-bottom: 12px; }
        .badge-dot { width: 8px; height: 8px; border-radius: 50%; }

        .badge-ready { background: rgba(107, 114, 128, 0.2); color: #e5e7eb; border: 1px solid rgba(107, 114, 128, 0.4); } .badge-ready .badge-dot { background: #9ca3af; }
        .badge-connecting { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); } .badge-connecting .badge-dot { background: #fbbf24; }
        .badge-listening { background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4); } .badge-listening .badge-dot { background: #4ade80; }
        .badge-speaking { background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); } .badge-speaking .badge-dot { background: #38bdf8; }
        .badge-ended { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); } .badge-ended .badge-dot { background: #f87171; }

        .status-desc { font-size: 13px; color: #d1d5db; margin-bottom: 12px; min-height: 20px; }
        .db-tag { font-size: 10px; color: #38bdf8; background: rgba(56, 189, 248, 0.1); padding: 4px 8px; border-radius: 6px; margin-bottom: 16px; border: 1px solid rgba(56, 189, 248, 0.2); display: inline-block; }

        .btn { width: 100%; padding: 14px; border: none; border-radius: 16px; font-size: 15px; font-weight: 700; color: #ffffff; cursor: pointer; background: linear-gradient(135deg, #f59e0b, #d97706); box-shadow: 0 6px 20px rgba(245, 158, 11, 0.3); }
        .btn-danger { background: linear-gradient(135deg, #ef4444, #dc2626); box-shadow: 0 6px 20px rgba(239, 68, 68, 0.3); }

        /* CHAT SECTION STYLES */
        .chat-card { text-align: left; height: 420px; display: flex; flex-direction: column; justify-content: space-between; }
        .chat-title { font-size: 14px; font-weight: 700; color: #9ca3af; text-transform: uppercase; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; }
        
        .chat-box { flex-grow: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; padding-right: 6px; margin-bottom: 12px; }
        .chat-box::-webkit-scrollbar { width: 4px; }
        .chat-box::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 4px; }

        .msg { max-width: 85%; padding: 10px 14px; border-radius: 16px; font-size: 13px; line-height: 1.4; word-wrap: break-word; }
        .msg-user { align-self: flex-end; background: rgba(245, 158, 11, 0.2); border: 1px solid rgba(245, 158, 11, 0.4); color: #fef3c7; border-bottom-right-radius: 4px; }
        .msg-agent { align-self: flex-start; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.3); color: #e0f2fe; border-bottom-left-radius: 4px; }
        .msg-sender { font-size: 10px; opacity: 0.7; margin-bottom: 3px; font-weight: 700; }

        .chat-input-container { display: flex; gap: 8px; }
        .chat-input { flex-grow: 1; background: rgba(0, 0, 0, 0.3); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 12px; padding: 10px 12px; color: #fff; font-size: 13px; outline: none; }
        .chat-send-btn { background: #38bdf8; border: none; border-radius: 12px; padding: 0 16px; color: #000; font-weight: 700; cursor: pointer; font-size: 13px; }
    </style>
</head>
<body>

<div class="bubble bubble-1"></div>
<div class="bubble bubble-2"></div>

<div class="container">
    <!-- LEFT PANEL: VOICE STATUS -->
    <div class="card">
        <div>
            <h1>Aasha AI</h1>
            <div class="subtitle">Day 4 • Interactive Voice Agent</div>

            <div class="avatar-container">
                <div class="glow-ring glow-ready" id="glowRing"></div>
                <div class="avatar" id="avatarEmoji">🏪</div>
            </div>

            <div>
                <div class="status-badge badge-ready" id="badge">
                    <span class="badge-dot"></span>
                    <span id="badgeText">READY</span>
                </div>
            </div>
            
            <div class="status-desc" id="statusText">Tap start to begin conversation</div>
            <div class="db-tag">🗄️ SQLite Active: store_inventory.db</div>
        </div>

        <button class="btn" id="mainBtn" onclick="handleButtonClick()">Start Call</button>
    </div>

    <!-- RIGHT PANEL: REAL-TIME CHAT -->
    <div class="card chat-card">
        <div class="chat-title">
            <span>💬 Live Chat Feed</span>
            <span style="font-size: 10px; color: #38bdf8;">Real-Time</span>
        </div>

        <div class="chat-box" id="chatBox">
            <div class="msg msg-agent">
                <div class="msg-sender">Aasha</div>
                Namaste! Main Aasha hoon. Aap mujhse stock, timing, ya order ke baare mein baat kar sakte hain.
            </div>
        </div>

        <div class="chat-input-container">
            <input type="text" class="chat-input" id="chatInput" placeholder="Type a message or speak..." onkeydown="if(event.key==='Enter') sendTextMessage()">
            <button class="chat-send-btn" onclick="sendTextMessage()">Send</button>
        </div>
    </div>
</div>

<audio id="audioPlayer" style="display:none;"></audio>

<script>
    let activeState = 'READY';
    let recognition = null;
    let keepListening = false;

    function addChatMessage(sender, text) {
        const chatBox = document.getElementById('chatBox');
        const msgDiv = document.createElement('div');
        msgDiv.className = sender === 'You' ? 'msg msg-user' : 'msg msg-agent';
        msgDiv.innerHTML = `<div class="msg-sender">${sender}</div>${text}`;
        chatBox.appendChild(msgDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function updateUI(newState, text) {
        activeState = newState;
        const badge = document.getElementById('badge');
        const badgeText = document.getElementById('badgeText');
        const statusText = document.getElementById('statusText');
        const btn = document.getElementById('mainBtn');
        const glow = document.getElementById('glowRing');
        const emoji = document.getElementById('avatarEmoji');

        const stateKey = newState.toLowerCase().replace(' ', '');

        badge.className = 'status-badge badge-' + stateKey;
        badgeText.innerText = newState;
        statusText.innerText = text;

        glow.className = 'glow-ring glow-' + stateKey;

        if (newState === 'READY') emoji.innerText = '🏪';
        else if (newState === 'CONNECTING') emoji.innerText = '⚡';
        else if (newState === 'LISTENING') emoji.innerText = '🎙️';
        else if (newState === 'SPEAKING') emoji.innerText = '🗣️';
        else if (newState === 'CALL ENDED') emoji.innerText = '👋';

        if (newState === 'READY' || newState === 'CALL ENDED') {
            btn.innerText = newState === 'CALL ENDED' ? 'Start Again' : 'Start Call';
            btn.className = 'btn';
        } else {
            btn.innerText = 'End Call';
            btn.className = 'btn btn-danger';
        }
    }

    function handleButtonClick() {
        if (activeState === 'READY' || activeState === 'CALL ENDED') {
            startConversation();
        } else {
            endConversation();
        }
    }

    async function startConversation() {
        keepListening = true;
        updateUI('CONNECTING', 'Connecting to Aasha...');

        try {
            await navigator.mediaDevices.getUserMedia({ audio: true });
        } catch (err) {
            updateUI('CALL ENDED', 'Microphone blocked.');
            keepListening = false;
            return;
        }

        const introText = "Namaste! Main Aasha hoon, aapki store assistant. Main stock aur timing bata sakti hoon.";
        speakText(introText);
    }

    function sendTextMessage() {
        const input = document.getElementById('chatInput');
        const text = input.value.trim();
        if (!text) return;
        
        input.value = '';
        addChatMessage('You', text);
        handleQuery(text);
    }

    async function handleQuery(queryText) {
        updateUI('CONNECTING', 'Processing query...');
        try {
            const res = await fetch('/process-query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: queryText })
            });
            const data = await res.json();
            addChatMessage('Aasha', data.response);
            speakText(data.response);
        } catch(e) {
            const fallback = "Aapne kaha: " + queryText;
            addChatMessage('Aasha', fallback);
            speakText(fallback);
        }
    }

    async function speakText(text) {
        updateUI('SPEAKING', text);

        // Immediate Native Speech for Instant Feedback
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'hi-IN';
            utterance.rate = 1.0;
            
            utterance.onend = () => {
                if (keepListening) startListening();
            };
            
            window.speechSynthesis.speak(utterance);
        } else {
            if (keepListening) setTimeout(startListening, 2000);
        }
    }

    function startListening() {
        if (!keepListening) return;

        updateUI('LISTENING', 'Listening...');

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) return;

        if (recognition) {
            try { recognition.abort(); } catch(e) {}
        }

        recognition = new SpeechRecognition();
        recognition.lang = 'hi-IN';
        recognition.interimResults = false;

        recognition.onresult = async (event) => {
            const userSpeech = event.results[0][0].transcript;
            addChatMessage('You', userSpeech);
            handleQuery(userSpeech);
        };

        recognition.onerror = () => {
            if (keepListening) setTimeout(startListening, 1000);
        };

        recognition.onend = () => {
            if (keepListening && activeState === 'LISTENING') {
                setTimeout(startListening, 500);
            }
        };

        try { recognition.start(); } catch(e) {}
    }

    function endConversation() {
        keepListening = false;
        if (recognition) {
            try { recognition.abort(); } catch(e) {}
        }
        if ('speechSynthesis' in window) window.speechSynthesis.cancel();
        updateUI('CALL ENDED', 'Conversation ended.');
    }
</script>
</body>
</html>
"""

# ==========================================
# SERVER ROUTING & API ENDPOINTS
# ==========================================
class AgentHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_CONTENT.encode())

    def do_POST(self):
        if self.path == "/process-query":
            content_length = int(self.headers['Content-Length'])
            post_data = json.loads(self.rfile.read(content_length))
            user_query = post_data.get("query", "")

            ai_reply = process_user_query(user_query)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"response": ai_reply}).encode())

        elif self.path == "/generate-speech":
            content_length = int(self.headers['Content-Length'])
            post_data = json.loads(self.rfile.read(content_length))
            user_text = post_data.get("text", "")

            headers = {
                "api-key": MURF_API_KEY,
                "Content-Type": "application/json"
            }
            payload = {
                "voiceId": "hi-IN-kabir",
                "style": "Conversational",
                "text": user_text,
                "rate": 0,
                "pitch": 0,
                "sampleRate": 44100,
                "format": "MP3",
                "encodeAsBase64": False
            }

            try:
                resp = requests.post("https://api.murf.ai/v1/speech/generate", json=payload, headers=headers, timeout=3)
                if resp.status_code in [200, 201]:
                    audio_url = resp.json().get("audioFile")
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"audioUrl": audio_url}).encode())
                else:
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"audioUrl": None}).encode())
            except Exception:
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"audioUrl": None}).encode())

socketserver.TCPServer.allow_reuse_address = True
print(f"🚀 Day 4 Chat & Voice Server running at http://localhost:{PORT}")
with socketserver.TCPServer(("", PORT), AgentHandler) as httpd:
    httpd.serve_forever()

