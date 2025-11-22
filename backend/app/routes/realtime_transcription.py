"""
Real-time transcription WebSocket endpoint
Accepts audio chunks and returns transcripts in real-time
"""
import json
import logging
import asyncio
import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/realtime", tags=["realtime"])

class RealtimeTranscriber:
    """Manages real-time transcription via Deepgram WebSocket"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.deepgram_ws = None
        
    async def connect_deepgram(self):
        """Connect to Deepgram WebSocket"""
        # Use linear16 (PCM) format for raw audio from browser
        url = "wss://api.deepgram.com/v1/listen?punctuate=true&interim_results=true&diarize=true&encoding=linear16&sample_rate=16000"
        headers = {
            "Authorization": f"Token {self.api_key}"
        }
        logger.info("Connecting to Deepgram WebSocket...")
        # Use additional_headers for websockets library v10+
        self.deepgram_ws = await websockets.connect(url, additional_headers=headers)
        logger.info("✅ Connected to Deepgram")
        
    async def send_audio(self, audio_data: bytes):
        """Send audio to Deepgram"""
        if self.deepgram_ws:
            await self.deepgram_ws.send(audio_data)
            
    async def receive_transcript(self):
        """Receive transcript from Deepgram"""
        if self.deepgram_ws:
            message = await self.deepgram_ws.recv()
            return json.loads(message)
        return None
        
    async def close(self):
        """Close Deepgram connection"""
        if self.deepgram_ws:
            await self.deepgram_ws.close()

@router.websocket("/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """
    WebSocket endpoint for real-time transcription
    
    Client sends: Audio chunks (binary)
    Server sends: Transcript JSON messages
    """
    try:
        await websocket.accept()
        logger.info("✅ WebSocket client connected from: %s", websocket.client)
    except Exception as e:
        logger.error(f"❌ Failed to accept WebSocket connection: {e}")
        return
    
    transcriber = None
    
    try:
        # Check API key
        if not settings.DEEPGRAM_API_KEY:
            logger.error("❌ DEEPGRAM_API_KEY not configured")
            await websocket.send_json({
                "type": "error",
                "message": "Deepgram API key not configured"
            })
            await websocket.close()
            return
            
        # Connect to Deepgram
        transcriber = RealtimeTranscriber(settings.DEEPGRAM_API_KEY)
        try:
            await transcriber.connect_deepgram()
        except Exception as e:
            logger.error(f"❌ Failed to connect to Deepgram: {e}")
            await websocket.send_json({
                "type": "error",
                "message": f"Failed to connect to Deepgram: {str(e)}"
            })
            await websocket.close()
            return
        
        # Speaker mapping for diarization
        speaker_counter = 0
        speaker_map = {}
        
        def get_speaker_name(speaker_id: int) -> str:
            """Map Deepgram speaker ID to readable name"""
            nonlocal speaker_counter
            if speaker_id not in speaker_map:
                speaker_counter += 1
                speaker_map[speaker_id] = f"Speaker {speaker_counter}"
            return speaker_map[speaker_id]
        
        # Start receiving transcripts in background
        async def receive_from_deepgram():
            try:
                while True:
                    result = await transcriber.receive_transcript()
                    if result and 'channel' in result:
                        channel = result['channel']
                        if 'alternatives' in channel and channel['alternatives']:
                            alternative = channel['alternatives'][0]
                            transcript = alternative.get('transcript', '')
                            if transcript:
                                # Get speaker ID (if diarization is enabled)
                                speaker_id = alternative.get('speaker', 0)
                                speaker_name = get_speaker_name(speaker_id)
                                
                                # Check if this is a final result
                                # Deepgram sends 'is_final' at the top level of the result
                                is_final = result.get('is_final', False)  # Default to False (interim) if not specified
                                
                                # Send transcript to client
                                await websocket.send_json({
                                    "type": "transcript",
                                    "text": transcript,
                                    "speaker": speaker_name,
                                    "is_final": is_final
                                })
                                logger.debug(f"📤 Sent transcript: {speaker_name}: {transcript[:50]}... (final: {is_final})")
            except websockets.exceptions.ConnectionClosed:
                logger.info("Deepgram connection closed")
            except Exception as e:
                logger.error(f"Error receiving from Deepgram: {e}")
        
        # Start receiving task
        receive_task = asyncio.create_task(receive_from_deepgram())
        
        # Receive audio from client
        try:
            while True:
                # Receive audio chunk
                audio_data = await websocket.receive_bytes()
                
                # Send to Deepgram
                if transcriber:
                    await transcriber.send_audio(audio_data)
                    
        except WebSocketDisconnect:
            logger.info("Client disconnected")
        finally:
            receive_task.cancel()
            try:
                await receive_task
            except asyncio.CancelledError:
                pass
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        if transcriber:
            await transcriber.close()
        logger.info("WebSocket connection closed")

