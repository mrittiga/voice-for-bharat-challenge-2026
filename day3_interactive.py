import http.server
import socketserver
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

MURF_API_KEY = os.getenv("MURF_API_KEY")
PORT = 8000

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aasha - AI Voice Assistant</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }

        body {
            background: #0d0f18;
            color: #ffffff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            position: relative;
        }

        /* Bubbly Ambient Background Elements */
        .bubble {
            position: absolute;
            border-radius: 50%;
            filter: blur(80px);
            opacity: 0.45;
            animation: float 8s ease-in-out infinite alternate;
            z-index: 0;
        }

        .bubble-1 {
            width: 320px;
            height: 320px;
            background: #f59e0b;
            top: -5%;
            left: -10%;
        }

        .bubble-2 {
            width: 360px;
            height: 360px;
            background: #8b5cf6;
            bottom: -10%;
            right: -10%;
            animation-delay: -4s;
        }

        .bubble-3 {
            width: 220px;
            height: 220px;
            background: #06b6d4;
            top: 45%;
            left: 50%;
            transform: translate(-50%, -50%);
            animation-delay: -2s;
        }

        @keyframes float {
            0% { transform: translateY(0px) scale(1); }
            100% { transform: translateY(-30px) scale(1.1); }
        }

        /* Glassmorphism Card Container */
        .card {
            position: relative;
            z-index: 10;
            width: 90%;
            max-width: 420px;
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 28px;
            padding: 32px 24px;
            text-align: center;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
        }

        h1 {
            font-size: 24px;
            font-weight: 800;
            background: linear-gradient(135deg, #fbbf24, #f59e0b, #38bdf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 6px;
        }

        .subtitle {
            font-size: 13px;
            color: #9ca3af;
            font-weight: 600;
            letter-spacing: 0.5px;
            margin-bottom: 24px;
            text-transform: uppercase;
        }

        /* Glowing Avatar & Halo Effect */
        .avatar-container {
            position: relative;
            width: 120px;
            height: 120px;
            margin: 0 auto 24px auto;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .glow-ring {
            position: absolute;
            width: 100%;
            height: 100%;
            border-radius: 50%;
            transition: all 0.5s ease;
        }

        .glow-ready { background: radial-gradient(circle, rgba(107,114,128,0.3) 0%, rgba(0,0,0,0) 70%); }
        .glow-connecting { background: radial-gradient(circle, rgba(245,158,11,0.6) 0%, rgba(0,0,0,0) 70%); animation: pulse 1.5s infinite; }
        .glow-listening { background: radial-gradient(circle, rgba(34,197,94,0.6) 0%, rgba(0,0,0,0) 70%); animation: pulse 1s infinite; }
        .glow-speaking { background: radial-gradient(circle, rgba(56,189,248,0.7) 0%, rgba(0,0,0,0) 70%); animation: pulse 0.8s infinite; }
        .glow-ended { background: radial-gradient(circle, rgba(239,68,68,0.4) 0%, rgba(0,0,0,0) 70%); }

        @keyframes pulse {
            0% { transform: scale(0.95); opacity: 0.6; }
            50% { transform: scale(1.2); opacity: 1; }
            100% { transform: scale(0.95); opacity: 0.6; }
        }

        .avatar {
            width: 85px;
            height: 85px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.08);
            border: 2px solid rgba(255, 255, 255, 0.2);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 36px;
            z-index: 2;
            box-shadow: inset 0 0 15px rgba(255,255,255,0.1);
        }

        /* 5 Dynamic Badges */
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 18px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.8px;
            margin-bottom: 12px;
            transition: all 0.3s ease;
        }

        .badge-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }

        .badge-ready { background: rgba(107, 114, 128, 0.2); color: #e5e7eb; border: 1px solid rgba(107, 114, 128, 0.4); }
        .badge-ready .badge-dot { background: #9ca3af; }

        .badge-connecting { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
        .badge-connecting .badge-dot { background: #fbbf24; }

        .badge-listening { background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4); }
        .badge-listening .badge-dot { background: #4ade80; }

        .badge-speaking { background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); }
        .badge-speaking .badge-dot { background: #38bdf8; }

        .badge-ended { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
        .badge-ended .badge-dot { background: #f87171; }

        .status-desc {
            font-size: 14px;
            color: #d1d5db;
            margin-bottom: 24px;
            min-height: 24px;
        }

        /* Buttons */
        .btn {
            width: 100%;
            padding: 16px;
            border: none;
            border-radius: 20px;
            font-size: 16px;
            font-weight: 700;
            color: #ffffff;
            cursor: pointer;
            background: linear-gradient(135deg, #f59e0b, #d97706);
            box-shadow: 0 8px 25px rgba(245, 158, 11, 0.35);
            transition: all 0.3s ease;
        }

        .btn:active {
            transform: scale(0.98);
        }

        .btn-danger {
            background: linear-gradient(135deg, #ef4444, #dc2626);
            box-shadow: 0 8px 25px rgba(239, 68, 68, 0.35);
        }

        .error-box {
            display: none;
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #fca5a5;
            padding: 12px;
            border-radius: 14px;
            font-size: 13px;
            margin-bottom: 20px;
            text-align: left;
        }
    </style>
</head>
<body>

<div class="bubble bubble-1"></div>
<div class="bubble bubble-2"></div>
<div class="bubble bubble-3"></div>

<div class="card">
    <h1>Aasha AI</h1>
    <div class="subtitle">Local Commerce Track • Voice for Bharat</div>

    <div class="avatar-container">
        <div class="glow-ring glow-ready" id="glowRing"></div>
        <div class="avatar" id="avatarEmoji">🛍️</div>
    </div>

    <div>
        <div class="status-badge badge-ready" id="badge">
            <span class="badge-dot"></span>
            <span id="badgeText">READY</span>
        </div>
    </div>
    
    <div class="status-desc" id="statusText">Tap below to connect with Aasha</div>

    <div class="error-box" id="errorBox"></div>

    <button class="btn" id="mainBtn" onclick="handleButtonClick()">Start Call</button>
    <audio id="audioPlayer" style="display:none;"></audio>
</div>

<script>
    let activeState = 'READY';
    let recognition = null;
    let keepListening = false;

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

        if (newState === 'READY') emoji.innerText = '🛍️';
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

    function showError(msg) {
        const box = document.getElementById('errorBox');
        box.style.display = 'block';
        box.innerHTML = msg;
    }

    function handleButtonClick() {
        if (activeState === 'READY' || activeState === 'CALL ENDED') {
            startConversation();
        } else {
            endConversation();
        }
    }

    async function startConversation() {
        document.getElementById('errorBox').style.display = 'none';
        keepListening = true;
        updateUI('CONNECTING', 'Connecting to agent...');

        try {
            await navigator.mediaDevices.getUserMedia({ audio: true });
        } catch (err) {
            showError('⚠️ <strong>Microphone Permission Denied!</strong><br>Please enable mic permissions in your browser settings.');
            updateUI('CALL ENDED', 'Microphone blocked.');
            keepListening = false;
            return;
        }

        // Full persona prompt integrating Day 1, Day 2 (3 Store Features + Guardrails)
        const introText = "Namaste! Main Aasha hoon, aapki local store assistant. Main teen kaam kar sakti hoon: pehla, dukaan ki timing batana; doosra, grocery items availability check karna; aur teesra, order list tayyar karna. Kripya dhyan dein, main payment nahi le sakti.";
        speakText(introText);
    }

    async function speakText(text) {
        updateUI('SPEAKING', 'Aasha is speaking...');
        
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
                player.play();
                
                player.onended = () => {
                    if (keepListening) {
                        startListening();
                    }
                };
            } else {
                if (keepListening) startListening();
            }
        } catch (e) {
            if (keepListening) startListening();
        }
    }

    function startListening() {
        if (!keepListening) return;

        updateUI('LISTENING', 'Listening... Speak into your mic');

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            showError('Speech recognition is not supported on this device/browser.');
            return;
        }

        if (recognition) {
            try { recognition.abort(); } catch(e) {}
        }

        recognition = new SpeechRecognition();
        recognition.lang = 'hi-IN';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onresult = (event) => {
            const userSpeech = event.results[0][0].transcript.toLowerCase();
            
            // Guardrail Escalation & Feature logic
            if (userSpeech.includes("payment") || userSpeech.includes("paisa") || userSpeech.includes("pay") || userSpeech.includes("confirm")) {
                speakText("Main direct payment ya order confirm nahi kar sakti. Kripya dukaandaar se 9876543210 par baat karein.");
            } else if (userSpeech.includes("time") || userSpeech.includes("timing") || userSpeech.includes("samay") || userSpeech.includes("kab")) {
                speakText("Dukaan subah aath baje se raat nau baje tak khuli rehti hai.");
            } else if (userSpeech.includes("samaan") || userSpeech.includes("item") || userSpeech.includes("grocery") || userSpeech.includes("aata")) {
                speakText("Aapki zaroorat ka grocery item stock mein available hai.");
            } else {
                speakText("Aapne kaha: " + userSpeech + ". Main aapki local dukaan jaankari mein madad kar sakti hoon.");
            }
        };

        recognition.onerror = (e) => {
            if (keepListening && e.error !== 'aborted') {
                setTimeout(() => { startListening(); }, 1000);
            }
        };

        recognition.onend = () => {
            if (keepListening && activeState === 'LISTENING') {
                setTimeout(() => { startListening(); }, 500);
            }
        };

        try {
            recognition.start();
        } catch(e) {}
    }

    function endConversation() {
        keepListening = false;
        if (recognition) {
            try { recognition.abort(); } catch(e) {}
        }
        const player = document.getElementById('audioPlayer');
        player.pause();
        updateUI('CALL ENDED', 'Conversation ended.');
    }
</script>
</body>
</html>
"""

class AgentHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_CONTENT.encode())

    def do_POST(self):
        if self.path == "/generate-speech":
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

            resp = requests.post("https://api.murf.ai/v1/speech/generate", json=payload, headers=headers)
            
            if resp.status_code in [200, 201]:
                audio_url = resp.json().get("audioFile")
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"audioUrl": audio_url}).encode())
            else:
                self.send_response(500)
                self.end_headers()

print(f"🚀 Combined Day 1+2+3 Interactive Server running at http://localhost:{PORT}")
with socketserver.TCPServer(("", PORT), AgentHandler) as httpd:
    httpd.serve_forever()

