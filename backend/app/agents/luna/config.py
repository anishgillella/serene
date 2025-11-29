import os
from pathlib import Path
from dotenv import load_dotenv

# Find project root (3 levels up from this file: luna/ -> agents/ -> app/ -> backend/ -> root)
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent.parent.parent
env_path = project_root / ".env"

# Load environment variables from root directory
if env_path.exists():
    load_dotenv(env_path)
else:
    print(f"⚠️  Warning: .env file not found at {env_path}")

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
