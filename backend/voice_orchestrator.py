"""Unified voice orchestrator: STT + LLM + RAG + TTS."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from .stt_client import AssemblyAIClient
from .serene_agent import get_serene_response
from .tts_handler import text_to_speech
from .rag_handler import amara_kb

logger = logging.getLogger(__name__)


class VoiceOrchestrator:
    """Orchestrates the complete voice call flow."""
    
    def __init__(self):
        self.stt_client = AssemblyAIClient()
        self.call_history: list[dict] = []
    
    async def process_voice_call(
        self, 
        audio_bytes: bytes,
        call_sid: Optional[str] = None,
    ) -> dict:
        """Process a complete voice call.
        
        Flow:
        1. Speech-to-Text (AssemblyAI)
        2. LLM Response (Serene + RAG)
        3. Text-to-Speech (ElevenLabs)
        
        Args:
            audio_bytes: Raw audio from phone
            call_sid: Twilio call ID for tracking
            
        Returns:
            Dict with transcript, response, and audio
        """
        logger.info(f"Starting voice call orchestration (call_sid: {call_sid})")
        
        try:
            # Step 1: Transcribe speech
            logger.info("Step 1: Transcribing speech...")
            transcript = await self.transcribe_audio(audio_bytes)
            
            if not transcript:
                return {
                    "success": False,
                    "error": "Failed to transcribe audio",
                    "call_sid": call_sid,
                }
            
            logger.info(f"Transcript: {transcript}")
            
            # Step 2: Generate response with RAG
            logger.info("Step 2: Generating response with Amara context...")
            serene_response = await get_serene_response(transcript)
            
            logger.info(f"Response: {serene_response[:100]}...")
            
            # Step 3: Convert to speech
            logger.info("Step 3: Converting response to speech...")
            audio_bytes_response = await text_to_speech(serene_response)
            
            if not audio_bytes_response:
                logger.warning("Failed to generate audio, returning text response")
                audio_bytes_response = b""
            
            # Log to call history
            self.call_history.append({
                "call_sid": call_sid,
                "transcript": transcript,
                "response": serene_response,
                "audio_length": len(audio_bytes_response),
            })
            
            return {
                "success": True,
                "transcript": transcript,
                "response": serene_response,
                "audio": audio_bytes_response,
                "audio_length": len(audio_bytes_response),
                "call_sid": call_sid,
            }
            
        except Exception as e:
            logger.error(f"Error in voice orchestration: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "call_sid": call_sid,
            }
    
    async def transcribe_audio(self, audio_bytes: bytes) -> str:
        """Transcribe audio using AssemblyAI.
        
        Args:
            audio_bytes: Raw audio data
            
        Returns:
            Transcribed text
        """
        try:
            # For now, return a placeholder
            # In production, this would stream to AssemblyAI
            logger.warning("STT not fully integrated yet - placeholder response")
            return "I'm calling to ask about Amara..."
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return ""
    
    async def get_call_summary(self, call_sid: str) -> Optional[dict]:
        """Get summary of a call."""
        for call in self.call_history:
            if call["call_sid"] == call_sid:
                return call
        return None


# Global instance
voice_orchestrator = VoiceOrchestrator()
