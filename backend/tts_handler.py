"""ElevenLabs Text-to-Speech integration for Serene."""

from __future__ import annotations

import io
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
import httpx

# Load environment
load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)

# ElevenLabs configuration
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"
VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "56AoDkrOh6qfVPDXZ7Pt")


async def text_to_speech(text: str) -> bytes:
    """Convert text to speech using ElevenLabs.
    
    Args:
        text: Text to convert to speech
        
    Returns:
        Audio bytes (MP3 format)
    """
    if not ELEVENLABS_API_KEY:
        logger.error("ELEVENLABS_API_KEY not set")
        return b""
    
    try:
        logger.info(f"Converting to speech: {text[:50]}...")
        
        url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{VOICE_ID}"
        
        response = httpx.post(
            url,
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                },
            },
            timeout=30.0,
        )
        
        if response.status_code == 200:
            audio_bytes = response.content
            logger.info(f"✅ Audio generated: {len(audio_bytes)} bytes")
            return audio_bytes
        else:
            logger.error(f"ElevenLabs error: {response.status_code} - {response.text}")
            return b""
            
    except Exception as e:
        logger.error(f"Error generating speech: {e}")
        return b""


async def speak(text: str) -> dict:
    """Generate speech and return as base64 for Twilio.
    
    Args:
        text: Text to speak
        
    Returns:
        Dict with audio data and metadata
    """
    audio_bytes = await text_to_speech(text)
    
    if not audio_bytes:
        return {
            "success": False,
            "error": "Failed to generate audio",
        }
    
    # For Twilio, we need to return the audio in a format it can use
    import base64
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    
    return {
        "success": True,
        "audio": audio_base64,
        "format": "mp3",
        "text": text,
        "bytes": len(audio_bytes),
    }


async def stream_audio(text: str) -> bytes:
    """Stream audio for real-time playback (for future enhancement).
    
    Args:
        text: Text to speak
        
    Returns:
        Audio bytes
    """
    return await text_to_speech(text)
