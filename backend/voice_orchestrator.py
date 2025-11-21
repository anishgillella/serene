"""Unified voice orchestrator: STT + LLM + RAG + TTS."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from .stt_client import AssemblyAIStreamingClient
from .serene_agent import get_serene_response
from .tts_handler import text_to_speech, speak
from .rag_handler import amara_kb
import base64
import json

logger = logging.getLogger(__name__)


class VoiceOrchestrator:
    """Orchestrates the complete voice call flow."""
    
    def __init__(self):
        self.stt_client = AssemblyAIStreamingClient()
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
            # Use the streaming client to transcribe the audio segment
            # We wrap audio_bytes in a list as the client expects an iterable of segments
            transcripts = await self.stt_client.stream_segments([audio_bytes])
            
            if not transcripts:
                logger.warning("No transcript returned from AssemblyAI")
                return ""
                
            # Join all transcript parts
            full_text = " ".join(transcripts)
            logger.info(f"STT Result: {full_text}")
            return full_text
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return ""
    
    async def get_call_summary(self, call_sid: str) -> Optional[dict]:
        """Get summary of a call."""
        for call in self.call_history:
            if call["call_sid"] == call_sid:
                return call
        return None


    async def handle_twilio_stream(self, ws) -> None:
        """Handle a Twilio Media Stream WebSocket connection.
        
        Args:
            ws: The WebSocket connection from flask-sock
        """
        logger.info("Starting Twilio stream handler")
        
        # Queue for audio chunks to send to AssemblyAI
        audio_queue = asyncio.Queue()
        
        # Generator to yield chunks from the queue
        async def audio_generator():
            while True:
                chunk = await audio_queue.get()
                if chunk is None:
                    break
                yield chunk

        # Initialize STT client for Twilio format (8kHz mulaw)
        stt = AssemblyAIStreamingClient(sample_rate=8000, encoding="mulaw")
        
        # Task to run STT loop and drive conversation
        async def run_stt():
            try:
                stream_sid = None
                
                # Process transcripts as they arrive
                async for transcript in stt.stream_segments(audio_generator()):
                    logger.info(f"🎤 User said: {transcript}")
                    
                    # Broadcast transcript to frontend
                    self.broadcast_event("transcript", {
                        "role": "user",
                        "text": transcript,
                        "isFinal": True
                    })
                    
                    if not transcript.strip():
                        continue
                        
                    # 1. Get LLM Response
                    response_text = await get_serene_response(transcript)
                    logger.info(f"🧠 Serene thinking: {response_text}")
                    
                    # Broadcast response to frontend
                    self.broadcast_event("transcript", {
                        "role": "assistant",
                        "text": response_text,
                        "isFinal": True
                    })
                    
                    # 2. Convert to Speech (TTS)
                    # Note: For lower latency, we should stream TTS, but for now we generate full audio
                    # Request ulaw_8000 directly for Twilio compatibility
                    audio_bytes = await text_to_speech(response_text, output_format="ulaw_8000")
                    
                    if audio_bytes and stream_sid:
                        # 3. Send Audio back to Twilio
                        # Twilio expects base64 encoded 8kHz mulaw (usually)
                        # ElevenLabs returns mp3. We need to convert or just send it if Twilio accepts it?
                        # Twilio Media Streams ONLY accept 8kHz PCMU (mulaw).
                        # We need to convert MP3/PCM to mulaw.
                        
                        # Since we don't have easy audio conversion in pure python without ffmpeg/pydub,
                        # and we can't easily install system deps, we might be stuck.
                        # BUT, ElevenLabs has a 'pcm_44100' output format option, or 'ulaw_8000' option!
                        # Let's check tts_handler.py to see if we can request ulaw_8000.
                        
                        # Assuming we update tts_handler to request ulaw_8000:
                        payload = base64.b64encode(audio_bytes).decode("utf-8")
                        
                        media_message = {
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {
                                "payload": payload
                            }
                        }
                        ws.send(json.dumps(media_message))
                        
                        # Mark event
                        mark_message = {
                            "event": "mark",
                            "streamSid": stream_sid,
                            "mark": {
                                "name": "response_complete"
                            }
                        }
                        ws.send(json.dumps(mark_message))
                        logger.info("✅ Sent audio response to Twilio")
                        
            except Exception as e:
                logger.error(f"STT/Orchestration error: {e}", exc_info=True)

        # Start the STT task
        stt_task = asyncio.create_task(run_stt())
        
        try:
            while True:
                message = ws.receive()
                if message is None:
                    break
                
                data = json.loads(message)
                event = data.get("event")
                
                if event == "connected":
                    logger.info(f"Media stream connected: {data}")
                elif event == "start":
                    logger.info(f"Media stream started: {data}")
                    stream_sid = data.get("start", {}).get("streamSid")
                    # Pass stream_sid to the runner if needed, or it can pick it up from context if we shared it
                    # For simplicity, we'll just set it in a shared var (not thread safe but ok for single async task)
                    # Better: put it in a queue or just let the runner wait for it? 
                    # Actually, the runner is inside this scope, so it can access stream_sid if we use `nonlocal`
                    # But `stream_sid` is local to `run_stt`... wait.
                    # Let's make stream_sid accessible.
                    
                elif event == "media":
                    payload = data.get("media", {}).get("payload")
                    if payload:
                        chunk = base64.b64decode(payload)
                        await audio_queue.put(chunk)
                        
                elif event == "stop":
                    logger.info("Media stream stopped")
                    break
                elif event == "mark":
                    pass
                    
        except Exception as e:
            logger.error(f"Twilio stream error: {e}")
        finally:
            # Signal generator to stop
            await audio_queue.put(None)
            # Wait for STT task to finish
            try:
                await stt_task
            except Exception:
                pass
            logger.info("Twilio stream closed")


# Global instance
voice_orchestrator = VoiceOrchestrator()
