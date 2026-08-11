import os
import json
import urllib.request

# Load variables directly from environment or set them here
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "YOUR_GEMINI_API_KEY")
MURF_API_KEY = os.getenv("MURF_API_KEY", "YOUR_MURF_API_KEY")

INVENTORY = {
    "organic turmeric powder": {"price": "₹120 / 250g", "stock": 15},
    "handloom cotton saree": {"price": "₹1,850", "stock": 4},
    "raw honey": {"price": "₹350 / 500g", "stock": 8},
}

def check_inventory(product_name):
    key = product_name.lower().strip()
    for item, details in INVENTORY.items():
        if item in key or key in item:
            return f"Item: {item.title()} | Price: {details['price']} | In Stock: {details['stock']} units."
    return f"Product '{product_name}' was not found in catalog."

def generate_murf_tts(text, filename="day6_response.mp3"):
    url = "https://api.murf.ai/v1/speech/generate"
    headers = {"api-key": MURF_API_KEY, "Content-Type": "application/json"}
    payload = json.dumps({"voiceId": "en-IN-aarav", "text": text, "format": "MP3"}).encode('utf-8')

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        res_data = json.loads(resp.read().decode())
        audio_url = res_data.get("audioFile")

    if audio_url:
        with urllib.request.urlopen(audio_url) as audio_resp, open(filename, "wb") as f:
            f.write(audio_resp.read())
        print(f"\n[Success] Audio saved to: {filename}")

def run():
    query = "organic turmeric powder"
    print(f"Querying catalog for: {query}...")
    result = check_inventory(query)
    agent_text = f"Namaste! {result}"
    print(f"Agent Answer: {agent_text}")
    generate_murf_tts(agent_text)

if __name__ == "__main__":
    run()

