import http.server
import socketserver
import json
import os
import sqlite3
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

MURF_API_KEY = os.getenv("MURF_API_KEY")
PORT = 8000
DB_FILE = "store_inventory.db"

EXTERNAL_API_LIVE = True 

# ==========================================
# DATABASE INITIALIZATION
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT UNIQUE,
            quantity TEXT,
            price_per_unit TEXT,
            updated_at TEXT
        )
    ''')
    
    today = datetime.now().strftime("%B %Y")
    items = [
        ('aata', '25 kg', '₹45 per kg', today),
        ('chawal', '50 kg', '₹60 per kg', today),
        ('doodh', '10 packets', '₹30 per packet', today),
        ('chini', '15 kg', '₹42 per kg', today),
        ('tel', '20 liters', '₹140 per liter', today)
    ]
    cursor.executemany("INSERT OR IGNORE INTO inventory (item_name, quantity, price_per_unit, updated_at) VALUES (?, ?, ?, ?)", items)
    conn.commit()
    conn.close()

init_db()

# ==========================================
# DAY 5 TOOL CALLING LOGIC (EXPANDED MATCHING)
# ==========================================
def tool_get_market_prices(item_query):
    if not EXTERNAL_API_LIVE:
        return {
            "status": "error",
            "message": "Main maafi chahti hoon, filhaal server ya live rate lookup service offline hai. Kripya dukaandaar se seedhe sampark karein."
        }
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    text = item_query.lower()
    
    # Expanded keywords supporting Devanagari Script & Roman Transliteration
    item_map = {
        "aata": ["aata", "flour", "आटा"],
        "chawal": ["chawal", "rice", "चावल"],
        "doodh": ["doodh", "milk", "दूध", "मिल्क"],
        "chini": ["chini", "sugar", "चीनी"],
        "tel": ["tel", "oil", "तेल"]
    }

    found_items = []
    for db_item, keywords in item_map.items():
        if any(kw in text for kw in keywords):
            cursor.execute("SELECT quantity, price_per_unit, updated_at FROM inventory WHERE item_name=?", (db_item,))
            row = cursor.fetchone()
            if row:
                found_items.append(f"{db_item.capitalize()}: {row[1]} (Stock: {row[0]})")

    conn.close()

    if found_items:
        details = ", ".join(found_items)
        return {
            "status": "success",
            "item": "Requested Items",
            "price": details,
            "stock": "In Stock",
            "as_of": datetime.now().strftime("%B %Y"),
            "message": f"Aapke poocha gaye items ke rate hain: {details}. Yeh jankari live update hui hai."
        }
    
    # Generic inventory overview if no specific item match
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, price_per_unit FROM inventory")
    rows = cursor.fetchall()
    conn.close()
    items_str = ", ".join([f"{r[0].capitalize()}: {r[1]}" for r in rows])
    
    return {
        "status": "success",
        "item": "All Inventory Items",
        "price": items_str,
        "stock": "Available",
        "as_of": datetime.now().strftime("%B %Y"),
        "message": f"Aaj ke sabhi items ke rates hain: {items_str}."
    }

def process_agent_query(user_text):
    text = user_text.lower()
    
    # Payment Guardrails
    if any(w in text for w in ["payment", "pay", "paisa", "confirm", "पेमेंट", "पैसा"]):
        return {
            "text": "Main direct payment ya order confirm nahi kar sakti. Kripya dukaandaar se 9876543210 par baat karein.",
            "ui_data": None
        }

    # Discounts / Offers Query
    if any(w in text for w in ["discount", "offer", "डिस्काउंट", "ऑफर", "छूट"]):
        return {
            "text": "Aaj ke liye 500 se upar ki khareedi par 5% discount mil raha hai!",
            "ui_data": None
        }

    # Market Price / Stock Query
    if any(w in text for w in ["rate", "price", "daam", "kitne ka", "stock", "chawal", "aata", "doodh", "chini", "tel", "चावल", "आटा", "दूध", "मिल्क", "चीनी", "तेल", "पैसे", "रेट", "दाम", "स्टॉक"]):
        tool_result = tool_get_market_prices(user_text)
        return {
            "text": tool_result["message"],
            "ui_data": tool_result if tool_result["status"] == "success" else None
        }

    # Timings Query
    if any(w in text for w in ["timing", "time", "samay", "khulegi", "band", "समय", "कब"]):
        return {
            "text": "Dukaan subah 8 baje se raat 9 baje tak khuli rahti hai.",
            "ui_data": None
        }

    # Dynamic Fallback Response
    return {
        "text": f"Aapne '{user_text}' ke baare mein poocha. Main aapko dukaan ke sabhi items ke rate aur stock ki jankari de sakti hoon.",
        "ui_data": None
    }

# ==========================================
# FRONTEND HTML / UI
# ==========================================
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Voice for Bharat - Day 5 Tool Agent</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
        body { background: #090d16; color: #ffffff; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }

        .app-window {
            width: 100%; max-width: 1100px; height: 600px;
            background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(30px);
            border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 28px;
            display: grid; grid-template-columns: 1fr 1fr; gap: 0; overflow: hidden;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
        }

        @media (max-width: 768px) {
            body { padding: 10px; }
            .app-window { grid-template-columns: 1fr; height: auto; }
        }

        .left-panel {
            padding: 32px; border-right: 1px solid rgba(255, 255, 255, 0.08);
            display: flex; flex-direction: column; justify-content: space-between; text-align: center; background: rgba(0,0,0,0.2);
        }

        .panel-header h1 { font-size: 24px; font-weight: 800; background: linear-gradient(135deg, #fbbf24, #f59e0b, #38bdf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .panel-header p { font-size: 11px; color: #9ca3af; text-transform: uppercase; font-weight: 700; letter-spacing: 1px; margin-top: 4px; }

        .avatar-box { position: relative; width: 140px; height: 140px; margin: 20px auto; display: flex; align-items: center; justify-content: center; }
        .glow-ring { position: absolute; width: 100%; height: 100%; border-radius: 50%; transition: all 0.5s ease; }
        .glow-ready { background: radial-gradient(circle, rgba(107,114,128,0.2) 0%, rgba(0,0,0,0) 70%); }
        .glow-listening { background: radial-gradient(circle, rgba(34,197,94,0.5) 0%, rgba(0,0,0,0) 70%); animation: pulse 1s infinite; }
        .glow-speaking { background: radial-gradient(circle, rgba(56,189,248,0.6) 0%, rgba(0,0,0,0) 70%); animation: pulse 0.8s infinite; }

        @keyframes pulse { 0% { transform: scale(0.95); opacity: 0.5; } 50% { transform: scale(1.15); opacity: 1; } 100% { transform: scale(0.95); opacity: 0.5; } }

        .avatar-circle { width: 100px; height: 100px; border-radius: 50%; background: rgba(255, 255, 255, 0.06); border: 2px solid rgba(255, 255, 255, 0.15); display: flex; align-items: center; justify-content: center; font-size: 42px; z-index: 2; }

        .status-badge { display: inline-flex; align-items: center; gap: 8px; padding: 8px 18px; border-radius: 20px; font-size: 12px; font-weight: 800; margin: 0 auto 12px auto; width: fit-content; }
        .badge-ready { background: rgba(107, 114, 128, 0.2); color: #e5e7eb; border: 1px solid rgba(107, 114, 128, 0.4); }

        .btn-action { width: 100%; padding: 16px; border: none; border-radius: 16px; font-size: 15px; font-weight: 700; color: #ffffff; cursor: pointer; background: linear-gradient(135deg, #f59e0b, #d97706); }
        .btn-danger { background: linear-gradient(135deg, #ef4444, #dc2626); }

        .right-panel { padding: 24px; display: flex; flex-direction: column; justify-content: space-between; background: rgba(0,0,0,0.1); }
        .chat-title { font-size: 12px; font-weight: 800; color: #9ca3af; text-transform: uppercase; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; }

        .chat-box { flex-grow: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; padding-right: 8px; margin-bottom: 16px; max-height: 440px; }
        .chat-box::-webkit-scrollbar { width: 4px; }
        .chat-box::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 4px; }

        .msg { max-width: 85%; padding: 12px 16px; border-radius: 18px; font-size: 13px; line-height: 1.5; word-wrap: break-word; }
        .msg-user { align-self: flex-end; background: rgba(245, 158, 11, 0.2); border: 1px solid rgba(245, 158, 11, 0.4); color: #fef3c7; border-bottom-right-radius: 4px; }
        .msg-agent { align-self: flex-start; background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.3); color: #e0f2fe; border-bottom-left-radius: 4px; }

        .tool-card { background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.4); border-radius: 12px; padding: 10px 12px; margin-top: 8px; font-size: 12px; }
        .tool-title { font-weight: 800; color: #4ade80; margin-bottom: 4px; }

        .chat-input-row { display: flex; gap: 10px; }
        .chat-input { flex-grow: 1; background: rgba(0, 0, 0, 0.4); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 14px; padding: 12px 16px; color: #fff; font-size: 13px; outline: none; }
        .send-btn { background: #38bdf8; border: none; border-radius: 14px; padding: 0 20px; color: #000; font-weight: 800; cursor: pointer; }
    </style>
</head>
<body>

<div class="app-window">
    <div class="left-panel">
        <div class="panel-header">
            <h1>Aasha AI</h1>
            <p>Day 5 • Tool Integrated Agent</p>
        </div>

        <div>
            <div class="avatar-box">
                <div class="glow-ring glow-ready" id="glowRing"></div>
                <div class="avatar-circle" id="avatarEmoji">🏪</div>
            </div>

            <div class="status-badge badge-ready" id="badge">
                <span id="badgeText">READY</span>
            </div>

            <p style="font-size: 12px; color: #9ca3af;" id="statusText">Click start to initiate conversation</p>
        </div>

        <button class="btn-action" id="mainBtn" onclick="handleButtonClick()">Start Call</button>
    </div>

    <div class="right-panel">
        <div class="chat-title">
            <span>💬 Real-Time Chat Screen</span>
            <span style="color: #38bdf8;">Murf Falcon TTS Active</span>
        </div>

        <div class="chat-box" id="chatBox">
            <div class="msg msg-agent">
                <b>Aasha:</b> Namaste! Main Aasha hoon. Aaj ka rate, stock, ya discount poocho!
            </div>
        </div>

        <div class="chat-input-row">
            <input type="text" class="chat-input" id="chatInput" placeholder="Type or speak a message..." onkeydown="if(event.key==='Enter') sendTextMessage()">
            <button class="send-btn" onclick="sendTextMessage()">Send</button>
        </div>
    </div>
</div>

<audio id="audioPlayer" crossorigin="anonymous" style="display:none;"></audio>

<script>
    let activeState = 'READY';
    let recognition = null;
    let keepListening = false;
    let audioCtx = null;
    let gainNode = null;

    function initAudioBoost() {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const player = document.getElementById('audioPlayer');
            const source = audioCtx.createMediaElementSource(player);
            gainNode = audioCtx.createGain();
            gainNode.gain.value = 2.0;
            source.connect(gainNode);
            gainNode.connect(audioCtx.destination);
        }
    }

    function addChatMessage(sender, text, uiData=null) {
        const chatBox = document.getElementById('chatBox');
        const msgDiv = document.createElement('div');
        msgDiv.className = sender === 'You' ? 'msg msg-user' : 'msg msg-agent';
        
        let html = `<b>${sender}:</b> ${text}`;
        
        if (uiData && uiData.item) {
            html += `
                <div class="tool-card">
                    <div class="tool-title">🛠️ Tool Executed: Market Price Lookup</div>
                    <div><b>Query:</b> ${uiData.item}</div>
                    <div><b>Details:</b> ${uiData.price}</div>
                    <div><b>Status:</b> ${uiData.stock}</div>
                </div>
            `;
        }
        
        msgDiv.innerHTML = html;
        chatBox.appendChild(msgDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function updateUI(newState, text) {
        activeState = newState;
        document.getElementById('badgeText').innerText = newState;
        document.getElementById('statusText').innerText = text;

        const glow = document.getElementById('glowRing');
        glow.className = 'glow-ring glow-' + newState.toLowerCase().replace(' ', '');

        const btn = document.getElementById('mainBtn');
        if (newState === 'READY' || newState === 'CALL ENDED') {
            btn.innerText = 'Start Call';
            btn.className = 'btn-action';
        } else {
            btn.innerText = 'End Call';
            btn.className = 'btn-action btn-danger';
        }
    }

    function handleButtonClick() {
        initAudioBoost();
        if (activeState === 'READY' || activeState === 'CALL ENDED') {
            keepListening = true;
            speakText("Namaste! Main Aasha hoon. Aaj ka rate ya stock janne ke liye poocho.");
        } else {
            keepListening = false;
            updateUI('CALL ENDED', 'Call ended.');
        }
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
        updateUI('SPEAKING', 'Fetching data...');
        try {
            const res = await fetch('/process-agent-query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: queryText })
            });
            const data = await res.json();
            addChatMessage('Aasha', data.text, data.ui_data);
            speakText(data.text);
        } catch(e) {
            const fallback = "System offline. Main abhi query execute nahi kar pa rahi hoon.";
            addChatMessage('Aasha', fallback);
            speakText(fallback);
        }
    }

    async function speakText(text) {
        updateUI('SPEAKING', text);

        try {
            const res = await fetch('/generate-speech', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text })
            });
            const data = await res.json();

            if (data.audioUrl) {
                const player = document.getElementById('audioPlayer');
                player.src = data.audioUrl;
                player.volume = 1.0;
                await player.play();
                player.onended = () => { if (keepListening) startListening(); };
            } else {
                fallbackSpeech(text);
            }
        } catch (e) {
            fallbackSpeech(text);
        }
    }

    function fallbackSpeech(text) {
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'hi-IN';
            utterance.volume = 1.0;
            utterance.onend = () => { if (keepListening) startListening(); };
            window.speechSynthesis.speak(utterance);
        }
    }

    function startListening() {
        if (!keepListening) return;
        updateUI('LISTENING', 'Listening...');
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) return;

        if (recognition) { try { recognition.abort(); } catch(e) {} }

        recognition = new SpeechRecognition();
        recognition.lang = 'hi-IN';
        recognition.onresult = (e) => {
            const userSpeech = e.results[0][0].transcript;
            addChatMessage('You', userSpeech);
            handleQuery(userSpeech);
        };
        try { recognition.start(); } catch(e) {}
    }
</script>
</body>
</html>
"""

# ==========================================
# SERVER ROUTING
# ==========================================
class AgentHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_CONTENT.encode())

    def do_POST(self):
        if self.path == "/process-agent-query":
            content_length = int(self.headers['Content-Length'])
            post_data = json.loads(self.rfile.read(content_length))
            user_query = post_data.get("query", "")

            response_data = process_agent_query(user_query)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())

        elif self.path == "/generate-speech":
            content_length = int(self.headers['Content-Length'])
            post_data = json.loads(self.rfile.read(content_length))
            user_text = post_data.get("text", "")

            headers = {
                "api-key": MURF_API_KEY,
                "Content-Type": "application/json"
            }
            payload = {
                "voiceId": "hi-IN-aarti",
                "style": "Conversational",
                "text": user_text,
                "rate": 0,
                "pitch": 0,
                "sampleRate": 44100,
                "format": "MP3",
                "encodeAsBase64": False
            }

            try:
                resp = requests.post("https://api.murf.ai/v1/speech/generate", json=payload, headers=headers, timeout=5)
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
print(f"🚀 Day 5 Server running at http://localhost:{PORT}")
with socketserver.TCPServer(("", PORT), AgentHandler) as httpd:
    httpd.serve_forever()

