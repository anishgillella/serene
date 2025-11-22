import json
import time
import logging
import asyncio
import websockets
from dotenv import load_dotenv
load_dotenv()

from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli
from livekit import rtc
from app.config import settings
from app.services.conflict_manager import ConflictManager

logger = logging.getLogger("heartsync-agent")

class DeepgramTranscriber:
    """Handles real-time transcription via Deepgram WebSocket"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.ws = None
        self.session = None
        
    async def connect(self):
        """Connect to Deepgram WebSocket"""
        # Use API key in URL for proper authentication
        url = f"wss://api.deepgram.com/v1/listen?punctuate=true&interim_results=false&diarize=true&encoding=linear16&sample_rate=16000&api_key={self.api_key}"
        logger.info("🔗 Connecting to Deepgram WebSocket...")
        self.ws = await websockets.connect(url)
        logger.info("✅ Connected to Deepgram")
        
    async def send_audio(self, audio_chunk: bytes):
        """Send audio to Deepgram"""
        if self.ws:
            await self.ws.send(audio_chunk)
            
    async def receive_transcripts(self, callback):
        """Receive and process transcripts from Deepgram"""
        try:
            async for message in self.ws:
                result = json.loads(message)
                
                # Check if this is a transcription result
                if 'channel' in result and 'alternatives' in result['channel']:
                    alternatives = result['channel']['alternatives']
                    if alternatives:
                        transcript = alternatives[0].get('transcript', '')
                        if transcript:
                            logger.info(f"📝 Transcript received: {transcript[:100]}")
                            await callback(transcript)
                            
        except websockets.exceptions.ConnectionClosed:
            logger.info("Deepgram connection closed")
        except Exception as e:
            logger.error(f"Error receiving transcripts: {e}")

async def audio_sink(transcriber: DeepgramTranscriber, track: rtc.AudioTrack):
    """Read audio from LiveKit track and send to Deepgram"""
    logger.info("🎤 Starting audio sink...")
    async for audio_frame in track.aframes:
        # Convert audio frame to bytes
        audio_data = audio_frame.data
        await transcriber.send_audio(audio_data)

async def entrypoint(ctx: JobContext):
    logger.info(f"🟢 ENTRYPOINT: connecting to room {ctx.room.name}")
    
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info("🟢 Connected to LiveKit room")

    participant = await ctx.wait_for_participant()
    logger.info(f"🟢 Participant joined: {participant.identity}")

    # Initialize Conflict Manager
    conflict_manager = ConflictManager()
    await conflict_manager.start_conflict()
    logger.info(f"🟢 Conflict started: {conflict_manager.current_conflict_id}")

    # Initialize Deepgram
    transcriber = DeepgramTranscriber(settings.DEEPGRAM_API_KEY)
    await transcriber.connect()

    # Callback to handle transcripts
    async def on_transcript(text: str):
        """Called when a transcript is received from Deepgram"""
        speaker_id = participant.identity if participant else "user"
        current_time = time.time()
        
        logger.info(f"💾 Saving transcript: {speaker_id}: {text}")
        conflict_manager.add_transcript(speaker_id, text, current_time)
        
        # Broadcast to frontend
        try:
            await ctx.room.local_participant.publish_data(
                json.dumps({
                    "type": "transcript",
                    "text": text,
                    "speaker": speaker_id,
                    "timestamp": current_time
                }),
                reliable=True
            )
            logger.info(f"📤 Sent to frontend")
        except Exception as e:
            logger.error(f"Failed to publish: {e}")

    # Start receiving transcripts
    transcript_task = asyncio.create_task(transcriber.receive_transcripts(on_transcript))

    # Subscribe to existing audio tracks
    logger.info("🟢 Setting up audio tracks...")
    for track in ctx.room.local_participant.audio_tracks:
        if track.kind == rtc.TrackKind.AUDIO:
            logger.info(f"🟢 Found audio track: {track.name}")
            asyncio.create_task(audio_sink(transcriber, track))

    # Listen for new audio tracks
    async def handle_track_events():
        async for event in ctx.room.events():
            if event.track and event.track.kind == rtc.TrackKind.AUDIO:
                logger.info(f"🟢 New audio track: {event.track.name}")
                asyncio.create_task(audio_sink(transcriber, event.track))

    track_task = asyncio.create_task(handle_track_events())

    # Shutdown control
    shutdown_event = asyncio.Event()
    
    # Data Channel listener for frontend end_session signals
    @ctx.room.on("data_received")
    def on_data_received(data_packet: rtc.DataPacket):
        try:
            payload = json.loads(data_packet.data.decode('utf-8'))
            if payload.get("type") == "end_session":
                logger.info("Received end_session signal from frontend")
                shutdown_event.set()
        except Exception as e:
            logger.error(f"Error processing data message: {e}")
    
    # Periodic room monitor
    async def monitor_room():
        """Monitor room for participant activity and auto-end when empty"""
        empty_since = None
        timeout_seconds = 10
        
        while not shutdown_event.is_set():
            await asyncio.sleep(5)
            
            participant_count = len(ctx.room.remote_participants)
            
            if participant_count == 0:
                if empty_since is None:
                    empty_since = asyncio.get_event_loop().time()
                    logger.info("Room is empty, starting timeout timer")
                else:
                    elapsed = asyncio.get_event_loop().time() - empty_since
                    if elapsed >= timeout_seconds:
                        logger.info(f"Room empty for {elapsed:.1f}s, ending session")
                        shutdown_event.set()
                        break
            else:
                if empty_since is not None:
                    logger.info(f"Participants rejoined ({participant_count}), resetting timer")
                empty_since = None
    
    monitor_task = asyncio.create_task(monitor_room())

    # Handle shutdown
    try:
        await shutdown_event.wait()
        logger.info("Shutdown signal received, ending conflict session...")
    except asyncio.CancelledError:
        logger.info("Agent cancelled, shutting down...")
    finally:
        # Cancel all tasks
        transcript_task.cancel()
        track_task.cancel()
        monitor_task.cancel()
        
        try:
            await transcript_task
        except asyncio.CancelledError:
            pass
        try:
            await track_task
        except asyncio.CancelledError:
            pass
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        
        # Close Deepgram connection
        if transcriber.ws:
            await transcriber.ws.close()
        
        # End conflict and save data
        await conflict_manager.end_conflict()
        logger.info("Conflict session ended and data saved")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
