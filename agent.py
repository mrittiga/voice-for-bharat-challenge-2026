import asyncio
from dotenv import load_dotenv
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import murf, openai

# Load credentials from .env
load_dotenv()

async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Day 1: Configure Murf Falcon TTS with an Indian Voice Model
    tts_plugin = murf.TTS(
        voice="en-IN-ananya",  # Indian English (or hi-IN-kabir)
        model="Falcon 2"
    )

    # Setup the voice assistant pipeline
    assistant = VoiceAssistant(
        vad=openai.VAD.load(),
        stt=openai.STT(),
        llm=openai.LLM(),
        tts=tts_plugin,
        chat_ctx=llm.ChatContext().append(
            role="system",
            text="You are an AI Voice Agent for the Local Commerce track in India. Keep responses concise and natural."
        )
    )

    assistant.start(ctx.room)
    
    # Day 1 Initial Greeting
    await assistant.say("Hello! Welcome to Day 1 of Voice for Bharat Challenge. I am your Local Commerce voice agent. How can I assist you today?", allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

