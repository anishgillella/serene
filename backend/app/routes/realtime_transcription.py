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
logger.setLevel(logging.INFO)  # Ensure INFO level logging

router = APIRouter(prefix="/api/realtime", tags=["realtime"])

class RealtimeTranscriber:
    """Manages real-time transcription via Deepgram WebSocket"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.deepgram_ws = None
        
    async def connect_deepgram(self):
        """Connect to Deepgram WebSocket"""
        # Use linear16 (PCM) format for raw audio from browser
        # diarize=true enables speaker diarization
        # Note: utterances=true is for REST API only, not WebSocket streaming
        # For WebSocket, speaker info comes in words array
        # smart_format=true improves punctuation and formatting
        # model=nova-3 provides best diarization accuracy
        url = "wss://api.deepgram.com/v1/listen?model=nova-3&punctuate=true&interim_results=true&diarize=true&smart_format=true&encoding=linear16&sample_rate=16000"
        headers = {
            "Authorization": f"Token {self.api_key}"
        }
        logger.info("Connecting to Deepgram WebSocket with Nova-3 model and diarization enabled...")
        # Use additional_headers for websockets library v10+
        self.deepgram_ws = await websockets.connect(url, additional_headers=headers)
        logger.info("✅ Connected to Deepgram Nova-3 with speaker diarization and utterances")
        
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
                # Map first speaker to Adrian Malhotra, second to Elara Voss
                if speaker_counter == 1:
                    speaker_map[speaker_id] = "Adrian Malhotra"
                else:
                    speaker_map[speaker_id] = "Elara Voss"
            return speaker_map[speaker_id]
        
        # Start receiving transcripts in background
        async def receive_from_deepgram():
            logger.info("🟢 Started receiving transcripts from Deepgram...")
            try:
                while True:
                    try:
                        result = await transcriber.receive_transcript()
                        
                        if not result:
                            logger.warning("⚠️ Received None from Deepgram")
                            continue
                    except Exception as e:
                        logger.error(f"❌ Exception in receive loop: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        raise
                    
                    if result and 'channel' in result:
                        channel = result['channel']
                        if 'alternatives' in channel and channel['alternatives']:
                            alternative = channel['alternatives'][0]
                            transcript = alternative.get('transcript', '').strip()
                            is_final = result.get('is_final', False)
                            
                            if not transcript:
                                continue
                            
                            # Extract speaker from words array (most reliable for WebSocket)
                            speaker_id = None
                            if 'words' in alternative and len(alternative['words']) > 0:
                                speaker_counts = {}
                                
                                for word in alternative['words']:
                                    word_speaker = word.get('speaker')
                                    if word_speaker is not None:
                                        speaker_counts[word_speaker] = speaker_counts.get(word_speaker, 0) + 1
                                
                                if speaker_counts:
                                    speaker_id = max(speaker_counts, key=speaker_counts.get)
                            
                            # Fallback: try other locations
                            if speaker_id is None:
                                if 'speaker' in result:
                                    speaker_id = result['speaker']
                                elif 'speaker' in alternative:
                                    speaker_id = alternative.get('speaker')
                            
                            # Default to 0 if still no speaker found
                            if speaker_id is None:
                                speaker_id = 0
                            
                            speaker_name = get_speaker_name(speaker_id)
                            
                            # Only send final results to frontend (more accurate speaker attribution)
                            if is_final:
                                await websocket.send_json({
                                    "type": "transcript",
                                    "text": transcript,
                                    "speaker": speaker_name,
                                    "is_final": is_final
                                })
                                logger.info(f"📤 Sent: {speaker_name}: {transcript[:50]}...")
            except websockets.exceptions.ConnectionClosed:
                logger.info("Deepgram connection closed")
            except Exception as e:
                logger.error(f"❌ Error receiving from Deepgram: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
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
        logger.error(f"❌ WebSocket error: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        if transcriber:
            await transcriber.close()
        logger.info("WebSocket connection closed")

