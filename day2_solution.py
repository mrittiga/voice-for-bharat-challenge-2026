import os
import requests
from dotenv import load_dotenv

# Load key automatically from .env file
load_dotenv()

MURF_API_KEY = os.getenv("MURF_API_KEY")

if not MURF_API_KEY:
    print("Error: MURF_API_KEY not found in .env file.")
    exit(1)

URL = "https://api.murf.ai/v1/speech/generate"

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "api-key": MURF_API_KEY
}

# Day 2 Task: Multilingual / Voice Customization
payload = {
    "voiceId": "hi-IN-kabir",      # Indic voice ID
    "style": "Conversational",
    "text": "नमस्ते! 'Voice for Bharat Challenge' के दूसरे दिन में आपका स्वागत है। यह मुर्फ़ एआई द्वारा निर्मित एक बहुभाषी ध्वनि संदेश है।",
    "rate": 0,
    "pitch": 0,
    "sampleRate": 44100,
    "format": "MP3",
    "encodeAsBase64": False
}

def run_day_2_task():
    print("Executing Day 2 Task using .env configuration...")
    
    try:
        response = requests.post(URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            audio_url = data.get("audioFile") or data.get("audioUrl")
            
            print("\n================ SUCCESS (DAY 2) ================")
            print(f"Generated Audio URL: {audio_url}")
            print("=================================================")
            
            if audio_url:
                print("Downloading output audio file...")
                audio_data = requests.get(audio_url).content
                with open("day2_output.mp3", "wb") as f:
                    f.write(audio_data)
                print("Audio saved successfully to day2_output.mp3!")
                
            return audio_url
        else:
            print(f"\nAPI Call Failed (Status {response.status_code}):")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

if __name__ == "__main__":
    run_day_2_task()

