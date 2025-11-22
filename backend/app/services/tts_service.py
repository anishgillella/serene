"""
ElevenLabs TTS service for generating natural voice responses
"""
import logging
from typing import Optional
from elevenlabs import ElevenLabs
from app.config import settings

logger = logging.getLogger(__name__)

class TTSService:
    """Service for text-to-speech using ElevenLabs"""
    
    def __init__(self):
        self.client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)
        self.voice_id = "21m00Tcm4TlvDq8ikWAM"  # Default voice (Rachel)
        logger.info("✅ Initialized ElevenLabs TTS service")
    
    def generate_audio(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model: str = "eleven_turbo_v2_5"
    ) -> bytes:
        """Generate audio from text"""
        try:
            audio_generator = self.client.text_to_speech.convert(
                voice_id=voice_id or self.voice_id,
                text=text,
                model_id=model
            )
            # Collect all audio chunks
            audio_bytes = b""
            for chunk in audio_generator:
                audio_bytes += chunk
            return audio_bytes
        except Exception as e:
            logger.error(f"❌ Error generating TTS audio: {e}")
            raise
    
    def stream_audio(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model: str = "eleven_turbo_v2_5"
    ):
        """Stream audio chunks (for real-time playback)"""
        try:
            audio_stream = self.client.text_to_speech.convert(
                voice_id=voice_id or self.voice_id,
                text=text,
                model_id=model
            )
            return audio_stream
        except Exception as e:
            logger.error(f"❌ Error streaming TTS audio: {e}")
            raise

# Singleton instance
tts_service = TTSService()

