import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env.local")
load_dotenv(".env")

# Set ElevenLabs API key in environment early (plugin checks ELEVEN_API_KEY)
if os.getenv("ELEVENLABS_API_KEY"):
    os.environ["ELEVEN_API_KEY"] = os.getenv("ELEVENLABS_API_KEY")

class Settings:
    LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
    LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
    LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

settings = Settings()
