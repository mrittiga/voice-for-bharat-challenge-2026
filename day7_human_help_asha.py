import os
import json
import random
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

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
ESCALATIONS_FILE = "escalations.json"

INVENTORY = {
    "turmeric": {"name": "Organic Turmeric Powder", "price": 120, "discount": 15, "unit": "250g", "stock": 15},
    "saree": {"name": "Handloom Cotton Saree", "price": 1850, "discount": 200, "unit": "piece", "stock": 4},
    "honey": {"name": "Raw Honey", "price": 350, "discount": 30, "unit": "500g", "stock": 8},
    "rice": {"name": "Basmati Rice", "price": 90, "discount": 10, "unit": "1kg", "stock": 25}
}

# In-memory session state
session_state = {
    "pending_escalation": False,
    "issue_type": None,
    "user_query": None
}

def load_escalations():
    if os.path.exists(ESCALATIONS_FILE):
        try:
            with open(ESCALATIONS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_escalation(summary):
    data = load_escalations()
    data.append(summary)
    with open(ESCALATIONS_FILE, "w") as f:
        json.dump(data, f, indent=2)

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

    # Step 1: Check if caller is replying to consent ask
    if session_state["pending_escalation"]:
        if any(word in query_clean for word in ["yes", "yeah", "ok", "sure", "proceed", "agree"]):
            ref_id = f"REF-{random.randint(1000, 9999)}"
            ticket_summary = {
                "reference_id": ref_id,
                "caller": "Customer (+91-987XXXXXXX)",
                "issue_type": session_state["issue_type"],
                "summary": f"User reported: {session_state['user_query']}. Automatic catalog resolution failed.",
                "urgency": "HIGH",
                "language": "English/Hindi",
                "preferred_followup": "Call back within 24 hours",
                "status": "OPEN"
            }
            save_escalation(ticket_summary)
            session_state["pending_escalation"] = False
            session_state["issue_type"] = None
            session_state["user_query"] = None
            
            return (
                f"Thank you. I have created a human support ticket for you. Your Reference ID is {ref_id}. "
                f"Our Kirana store manager will review this and follow up with you within 24 hours."
            )
        else:
            session_state["pending_escalation"] = False
            session_state["issue_type"] = None
            session_state["user_query"] = None
            return "Understood. I have not shared your information or created a support request. How else may I help you today?"

    # Step 2: Escalation Triggers (Payment Disputes or Product Damage)
    if any(k in query_clean for k in ["refund", "dispute", "double charged", "wrong payment", "fraud"]):
        session_state["pending_escalation"] = True
        session_state["issue_type"] = "Payment & Refund Dispute"
        session_state["user_query"] = query_text
        return (
            "I see that you have a payment or refund dispute. I cannot resolve payment discrepancies on my own. "
            "May I have your permission to share your call details with our store manager to resolve this?"
        )

    if any(k in query_clean for k in ["damaged", "broken", "quality issue", "spoiled", "rotten"]):
        session_state["pending_escalation"] = True
        session_state["issue_type"] = "Damaged Goods & Quality Complaint"
        session_state["user_query"] = query_text
        return (
            "I apologize that your item had quality or damage issues. "
            "May I have your permission to escalate this problem to our store owner along with your preferred contact method?"
        )

    # Step 3: Standard Catalog Query
    for key, details in INVENTORY.items():
        if key in query_clean or details["name"].lower() in query_clean:
            final_price = details["price"] - details["discount"]
            return (
                f"Namaste! For {details['name']}, the rate is ₹{details['price']} per {details['unit']}. "
                f"Discount: ₹{details['discount']}. Final Price: ₹{final_price}. Stock: {details['stock']} units."
            )

    return "Namaste! Welcome to Asha AI Kirana Store. I can help you check prices, discounts, or report order issues."

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Day 7 - Asha AI Human Support Agent</title>
    <style>
        body { font-family: Arial, sans-serif; background: #121212; color: #fff; margin: 0; padding: 15px; }
        .container { max-width: 900px; margin: auto; display: flex; flex-wrap: wrap; gap: 20px; }
        .card { flex: 1; min-width: 300px; background: #1e1e1e; padding: 20px; border-radius: 12px; }
        h2, h3 { color: #ff9800; margin-top: 0; }
        .chat-box { height: 260px; overflow-y: auto; background: #2a2a2a; border-radius: 8px; padding: 10px; margin: 15px 0; }
        .msg { margin: 8px 0; padding: 8px 12px; border-radius: 6px; font-size: 14px; }
        .user { background: #0288d1; text-align: right; margin-left: 15%; }
        .asha { background: #388e3c; margin-right: 15%; }
        input { width: 70%; padding: 10px; border: none; border-radius: 5px; }
        button { padding: 10px 15px; border: none; background: #ff9800; color: #000; font-weight: bold; border-radius: 5px; cursor: pointer; }
        .ticket { background: #2a2a2a; border-left: 4px solid #ff9800; padding: 10px; margin-bottom: 10px; border-radius: 4px; font-size: 13px; }
        audio { width: 100%; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h2>📞 Asha AI Interactive Voice</h2>
            <p style="font-size:12px; color:#aaa;">Day 7: Human Escalation & Permission Flow</p>
            <div class="chat-box" id="chat">
                <div class="msg asha"><b>Asha AI:</b> Namaste! How can I help you with orders, rates, or disputes today?</div>
            </div>
            <input type="text" id="query" placeholder="Ask or report issue..." onkeypress="if(event.key==='Enter') sendQuery()">
            <button onclick="sendQuery()">Send</button>
            <audio id="player" controls style="display:none;"></audio>
        </div>

        <div class="card">
            <h3>📋 Store Manager Dashboard</h3>
            <p style="font-size:12px; color:#aaa;">Open Escalation Requests</p>
            <div id="tickets"><i>No escalations yet.</i></div>
        </div>
    </div>

    <script>
        async function sendQuery() {
            let input = document.getElementById('query');
            let text = input.value.trim();
            if(!text) return;

            let chat = document.getElementById('chat');
            chat.innerHTML += `<div class="msg user"><b>Caller:</b> ${text}</div>`;
            input.value = '';
            chat.scrollTop = chat.scrollHeight;

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
            loadTickets();
        }

        async function loadTickets() {
            let res = await fetch('/api/tickets');
            let tickets = await res.json();
            let box = document.getElementById('tickets');
            if(tickets.length === 0) {
                box.innerHTML = '<i>No open escalations.</i>';
                return;
            }
            box.innerHTML = tickets.map(t => `
                <div class="ticket">
                    <b>[${t.reference_id}] ${t.issue_type}</b> <span style="color:#ff5252">(${t.urgency})</span><br>
                    <b>Summary:</b> ${t.summary}<br>
                    <b>Caller:</b> ${t.caller} | <b>Follow-up:</b> ${t.preferred_followup}<br>
                    <b>Status:</b> ${t.status}
                </div>
            `).join('');
        }
        loadTickets();
    </script>
</body>
</html>
"""

class AshaAIRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/tickets':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(load_escalations()).encode('utf-8'))
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
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
    print("🚀 Day 7 Asha AI Human Support Server on http://127.0.0.1:8000")
    print("=======================================================")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()

