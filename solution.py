import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables if present
load_dotenv()

# 1. ADD YOUR MURF API KEY HERE (or set it in your environment as MURF_API_KEY)
MURF_API_KEY = os.getenv("MURF_API_KEY", "ap2_690cba90-7f1a-43b8-989d-118296721582")

# Murf V1 Speech Generation Endpoint
URL = "https://api.murf.ai/v1/speech/generate"

# Request Headers
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "api-key": MURF_API_KEY
}

# 2. DAY 1 PAYLOAD CONFIGURATION
payload = {
    "voiceId": "en-IN-eashwar",  # Options: en-IN-eashwar, en-IN-ananya, hi-IN-kabir, hi-IN-swara
    "style": "Conversational",
    "text": "Namaste! Welcome to Day 1 of the Voice for Bharat Challenge 2026. This voice generation was created using Murf AI.",
    "rate": 0,                   # Speech speed (-50 to 50)
    "pitch": 0,                  # Voice pitch (-50 to 50)
    "sampleRate": 44100,         # High quality sample rate
    "format": "MP3",             # MP3, WAV, or FLAC
    "encodeAsBase64": False
}

def run_day_1_task():
    print("Sending request to Murf AI API for Day 1...")
    
    try:
        response = requests.post(URL, headers=headers, json=payload)
        
        # Parse Response
        if response.status_code == 200:
            data = response.json()
            audio_url = data.get("audioFile") or data.get("audioUrl")
            
            print("\n================ SUCCESS ================")
            print(f"Generated Audio URL: {audio_url}")
            print("=========================================")
            
            # Optionally download the audio file directly inside Termux
            if audio_url:
                print("Downloading audio file locally as output.mp3...")
                audio_data = requests.get(audio_url).content
                with open("output.mp3", "wb") as f:
                    f.write(audio_data)
                print("Audio saved successfully to output.mp3!")
                
            return audio_url
        else:
            print(f"\nAPI Call Failed with status code: {response.status_code}")
            print("Error Details:", response.text)
            return None
            
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

if __name__ == "__main__":
    run_day_1_task()
