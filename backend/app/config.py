from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    LIVEKIT_URL: str
    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str
    OPENROUTER_API_KEY: str
    DEEPGRAM_API_KEY: str
    ELEVENLABS_API_KEY: str
    VOYAGE_API_KEY: str
    PINECONE_API_KEY: str
    MISTRAL_API_KEY: str
    DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # Local Auth
    SECRET_KEY: str = "serene-dev-secret-change-in-production"

    # AWS S3 Configuration
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "serene-relationship-mediator"  # S3 bucket name

    # Auth0 Configuration
    AUTH0_DOMAIN: str = ""
    AUTH0_AUDIENCE: str = ""
    AUTH0_ALGORITHMS: list = ["RS256"]
    AUTH_OPTIONAL: bool = True  # Set to False in production


    class Config:
        env_file = "../.env"  # Load from root directory
        extra = "ignore"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
