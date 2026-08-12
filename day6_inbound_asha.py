import os
import json
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

INVENTORY = {
    "turmeric": {"name": "Organic Turmeric Powder", "price": 120, "discount": 15, "unit": "250g", "stock": 15},
    "saree": {"name": "Handloom Cotton Saree", "price": 1850, "discount": 200, "unit": "piece", "stock": 4},
    "honey": {"name": "Raw Honey", "price": 350, "discount": 30, "unit": "500g", "stock": 8},
    "rice": {"name": "Basmati Rice", "price": 90, "discount": 10, "unit": "1kg", "stock": 25}
}

def query_catalog(query_text):
    query_clean = query_text.lower()
    for key, details in INVENTORY.items():
        if key in query_clean or details["name"].lower() in query_clean:
            final_price = details["price"] - details["discount"]
            return (
                f"Namaste! For {details['name']}, the rate is ₹{details['price']} per {details['unit']}. "
                f"Discount: ₹{details['discount']}. Final Price: ₹{final_price}. "
                f"Stock: {details['stock']} units."
            )
    return "Namaste! That product is currently not available in Asha AI's catalog."

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

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Asha AI Kirana Voice Agent</title>
    <style>
        body { font-family: Arial, sans-serif; background: #121212; color: #fff; margin: 0; padding: 20px; text-align: center; }
        .card { max-width: 450px; margin: auto; background: #1e1e1e; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
        h2 { color: #ff9800; margin-bottom: 5px; }
        .chat-box { height: 250px; overflow-y: auto; background: #2a2a2a; border-radius: 8px; padding: 10px; text-align: left; margin: 15px 0; }
        .msg { margin: 8px 0; padding: 8px 12px; border-radius: 6px; font-size: 14px; }
        .user { background: #0288d1; text-align: right; margin-left: 20%; }
        .asha { background: #388e3c; margin-right: 20%; }
        input { width: 70%; padding: 10px; border: none; border-radius: 5px; font-size: 14px; }
        button { padding: 10px 15px; border: none; background: #ff9800; color: #000; font-weight: bold; border-radius: 5px; cursor: pointer; }
        audio { width: 100%; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>📞 Asha AI Voice Agent</h2>
        <p style="font-size: 12px; color: #aaa;">Inbound Commerce Simulation</p>
        <div class="chat-box" id="chat">
            <div class="msg asha"><b>Asha AI:</b> Namaste! Welcome to Kirana Store. Ask me about rates, discounts, or stock!</div>
        </div>
        <input type="text" id="query" placeholder="Ask e.g. price of turmeric..." onkeypress="if(event.key==='Enter') sendQuery()">
        <button onclick="sendQuery()">Call</button>
        <audio id="player" controls style="display:none;"></audio>
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
        }
    </script>
</body>
</html>
"""

class AshaAIRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
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
            
            response_text = query_catalog(caller_query)
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
    print("🚀 Asha AI Web App Running on http://127.0.0.1:8000")
    print("=======================================================")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()

