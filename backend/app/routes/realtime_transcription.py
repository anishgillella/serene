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
                # Map first speaker to Boyfriend, second to Girlfriend
                if speaker_counter == 1:
                    speaker_map[speaker_id] = "Boyfriend"
                else:
                    speaker_map[speaker_id] = "Girlfriend"
            return speaker_map[speaker_id]
        
        # Start receiving transcripts in background
        async def receive_from_deepgram():
            logger.info("🟢 Started receiving transcripts from Deepgram...")
            response_count = 0
            debug_file = None
            try:
                # Open debug file to dump responses
                debug_file = open('/tmp/deepgram_responses.json', 'w')
                debug_file.write("[\n")
                
                while True:
                    try:
                        result = await transcriber.receive_transcript()
                        response_count += 1
                        
                        # ALWAYS log that we received something
                        print(f"🔵 RECEIVED RESPONSE #{response_count} from Deepgram")
                        logger.info(f"🔵 RECEIVED RESPONSE #{response_count} from Deepgram")
                        
                        if not result:
                            logger.warning("⚠️ Received None from Deepgram")
                            continue
                    except Exception as e:
                        logger.error(f"❌ Exception in receive loop: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        raise
                    
                    # Dump first 10 responses to file for inspection
                    if response_count <= 10:
                        if response_count > 1:
                            debug_file.write(",\n")
                        debug_file.write(json.dumps(result, indent=2))
                        logger.info(f"📥 Response #{response_count} - Keys: {list(result.keys())}")
                        logger.info(f"📥 Full response: {json.dumps(result, indent=2)[:500]}...")
                    
                    if result and 'channel' in result:
                        channel = result['channel']
                        if 'alternatives' in channel and channel['alternatives']:
                            alternative = channel['alternatives'][0]
                            transcript = alternative.get('transcript', '').strip()
                            is_final = result.get('is_final', False)
                            
                            if not transcript:
                                continue
                            
                            # For WebSocket real-time API, speaker info is in words array
                            # Focus on final results for accurate speaker attribution
                            speaker_id = None
                            
                            # Log words array structure for first few responses
                            if response_count <= 5 and 'words' in alternative:
                                words_sample = alternative['words'][:3] if len(alternative['words']) > 3 else alternative['words']
                                logger.info(f"🔍 Words sample: {json.dumps(words_sample, indent=2)}")
                            
                            # Extract speaker from words array (most reliable for WebSocket)
                            if 'words' in alternative and len(alternative['words']) > 0:
                                speaker_counts = {}
                                words_with_speaker = 0
                                
                                for word in alternative['words']:
                                    word_speaker = word.get('speaker')
                                    if word_speaker is not None:
                                        words_with_speaker += 1
                                        speaker_counts[word_speaker] = speaker_counts.get(word_speaker, 0) + 1
                                
                                if speaker_counts:
                                    speaker_id = max(speaker_counts, key=speaker_counts.get)
                                    logger.info(f"🔍 Speaker from words: {speaker_id} (appears {speaker_counts[speaker_id]}/{words_with_speaker} words)")
                                elif response_count <= 10:
                                    logger.warning(f"⚠️ No speaker info in words array. Words count: {len(alternative['words'])}")
                                    # Log first word structure
                                    if alternative['words']:
                                        logger.info(f"🔍 First word structure: {json.dumps(alternative['words'][0], indent=2)}")
                            
                            # Fallback: try other locations
                            if speaker_id is None:
                                if 'speaker' in result:
                                    speaker_id = result['speaker']
                                    logger.info(f"🔍 Speaker from result level: {speaker_id}")
                                elif 'speaker' in alternative:
                                    speaker_id = alternative.get('speaker')
                                    logger.info(f"🔍 Speaker from alternative level: {speaker_id}")
                            
                            # Default to 0 if still no speaker found
                            if speaker_id is None:
                                speaker_id = 0
                                if is_final and response_count <= 10:
                                    logger.warning(f"⚠️ Final result but no speaker ID found!")
                                    logger.warning(f"   Result keys: {list(result.keys())}")
                                    logger.warning(f"   Alternative keys: {list(alternative.keys())}")
                            
                            speaker_name = get_speaker_name(speaker_id)
                            
                            # Only send final results to frontend (more accurate speaker attribution)
                            # Or send interim if we have speaker info
                            if is_final or (not is_final and speaker_id != 0):
                                await websocket.send_json({
                                    "type": "transcript",
                                    "text": transcript,
                                    "speaker": speaker_name,
                                    "is_final": is_final
                                })
                                logger.info(f"📤 Sent: {speaker_name} (ID: {speaker_id}): {transcript[:50]}... (final: {is_final})")
            except websockets.exceptions.ConnectionClosed:
                logger.info("Deepgram connection closed")
            except Exception as e:
                logger.error(f"❌ Error receiving from Deepgram: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
            finally:
                if debug_file:
                    debug_file.write("\n]")
                    debug_file.close()
                    logger.info("💾 Saved Deepgram responses to /tmp/deepgram_responses.json")
        
        # Start receiving task
        logger.info("🚀 Creating receive_from_deepgram task...")
        receive_task = asyncio.create_task(receive_from_deepgram())
        logger.info("✅ Receive task created")
        
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

