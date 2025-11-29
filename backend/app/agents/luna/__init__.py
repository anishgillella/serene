import logging
import time
import asyncio
import os
from livekit import agents, rtc
from livekit.agents import AgentSession, room_io, JobContext
from livekit.plugins import deepgram, elevenlabs, openai, silero
from livekit.plugins import noise_cancellation

from .config import settings
from .agent import SimpleMediator, RAGMediator
from .tools import get_tools
from app.services.db_service import db_service
from app.services.calendar_service import calendar_service

try:
    from langfuse import Langfuse
except ImportError:
    Langfuse = None

logger = logging.getLogger("luna-entrypoint")

async def mediator_entrypoint(ctx: JobContext):
    """Main mediator agent entry point"""
    
    logger.info(f"📍 Starting mediator session for room: {ctx.room.name}")
    
    # Filter: Only process mediator-* rooms
    room_name = ctx.room.name
    if not room_name.startswith("mediator-"):
        logger.warning(f"⚠️  Room '{room_name}' doesn't match mediator-* pattern, skipping")
        return
    
    # Extract conflict_id
    conflict_id = room_name.replace("mediator-", "").split("?")[0]
    logger.info(f"   ✅ Extracted Conflict ID: {conflict_id}")
    
    # Create DB session
    session_id = None
    if db_service:
        try:
            session_id = await asyncio.to_thread(
                db_service.create_mediator_session,
                conflict_id=conflict_id
            )
            logger.info(f"   ✅ Created DB session: {session_id}")
        except Exception as e:
            logger.error(f"   ❌ Failed to create DB session: {e}")
            
    try:
        # Setup AI Services
        elevenlabs_key = settings.ELEVENLABS_API_KEY
        openrouter_key = settings.OPENROUTER_API_KEY
        
        if not elevenlabs_key or not openrouter_key:
            raise ValueError("ELEVENLABS_API_KEY and OPENROUTER_API_KEY required")
            
        # LLM
        os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
        llm_instance = openai.LLM(
            api_key=openrouter_key,
            model="openai/gpt-4o-mini",
        )
        
        # TTS
        tts_instance = elevenlabs.TTS(
            model="eleven_flash_v2_5",
            voice_id="21m00Tcm4TlvDq8ikWAM", # Rachel
            api_key=elevenlabs_key,
            streaming_latency=3,
        )
        
        # Agent Session
        session = AgentSession(
            stt=deepgram.STT(model="nova-3", smart_format=True),
            llm=llm_instance,
            tts=tts_instance,
            vad=silero.VAD.load(min_speech_duration=0.1, min_silence_duration=0.3),
        )
        
        # Initialize RAG & Tools
        relationship_id = None
        if conflict_id and db_service:
            try:
                conflict_data = await asyncio.to_thread(db_service.get_conflict_by_id, conflict_id=conflict_id)
                if conflict_data:
                    relationship_id = str(conflict_data.get("relationship_id"))
            except Exception:
                pass

        rag_system = None
        try:
            from app.services.transcript_rag import TranscriptRAGSystem
            rag_system = TranscriptRAGSystem(k=5, include_profiles=True, include_calendar=False)
        except ImportError:
            logger.warning("RAG system not available")

        tools = get_tools(conflict_id, relationship_id)
        
        # Create Agent
        if rag_system:
            agent = RAGMediator(rag_system, conflict_id, relationship_id, session_id, tools=tools)
        else:
            agent = SimpleMediator(session_id, tools=tools)
            
        # Connect
        await session.start(
            room=ctx.room,
            agent=agent,
            room_options=room_io.RoomOptions(
                audio_input=room_io.AudioInputOptions(
                    noise_cancellation=lambda params: (
                        noise_cancellation.BVCTelephony()
                        if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                        else noise_cancellation.BVC()
                    ),
                ),
            ),
        )
        
        # Initial Greeting Logic (Simplified for brevity, but crucial for UX)
        # ... (We can port the greeting logic here or keep it simple)
        greeting = "Hey Adrian, I'm here. What's on your mind?"
        await session.say(greeting, allow_interruptions=True)
        
    except Exception as e:
        logger.error(f"❌ Error in mediator session: {e}", exc_info=True)
        raise
    finally:
        if session_id and db_service:
            await asyncio.to_thread(db_service.end_mediator_session, session_id=session_id)
