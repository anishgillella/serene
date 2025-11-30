import logging
import time
import asyncio
import os
from livekit import agents, rtc
from livekit.agents import AgentSession, room_io, JobContext
from livekit.plugins import deepgram, elevenlabs, openai, silero
import livekit.plugins.cartesia as cartesia
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

# Pre-load VAD model to reduce latency per connection
logger.info("⏳ Pre-loading VAD model...")
try:
    _vad_model = silero.VAD.load(min_speech_duration=0.1, min_silence_duration=0.3)
    logger.info("✅ VAD model pre-loaded")
except Exception as e:
    logger.error(f"❌ Failed to pre-load VAD model: {e}")
    _vad_model = None

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
    
    # Initialize variables
    session_id = None
    rag_system = None
    relationship_id = None
    
    # Define async tasks for parallel execution
    async def init_db_session():
        if not db_service:
            return None, None
        try:
            # Create session
            sid = await asyncio.to_thread(
                db_service.create_mediator_session,
                conflict_id=conflict_id
            )
            logger.info(f"   ✅ Created DB session: {sid}")
            
            # Get relationship ID for RAG
            rid = None
            try:
                conflict_data = await asyncio.to_thread(db_service.get_conflict_by_id, conflict_id=conflict_id)
                if conflict_data:
                    rid = str(conflict_data.get("relationship_id"))
            except Exception:
                pass
                
            return sid, rid
        except Exception as e:
            logger.error(f"   ❌ Failed to create DB session: {e}")
            return None, None

    async def init_rag():
        try:
            from app.services.transcript_rag import TranscriptRAGSystem
            # Initialize RAG (lightweight, but good to parallelize if it grows)
            return TranscriptRAGSystem(k=5, include_profiles=True, include_calendar=False)
        except ImportError:
            logger.warning("RAG system not available")
            return None

    # Start parallel tasks
    t_start = time.perf_counter()
    db_task = asyncio.create_task(init_db_session())
    rag_task = asyncio.create_task(init_rag())
    
    # Initialize AI Services (Lightweight client creation)
    try:
        cartesia_key = settings.CARTESIA_API_KEY
        openrouter_key = settings.OPENROUTER_API_KEY
        
        if not cartesia_key or not openrouter_key:
            raise ValueError("CARTESIA_API_KEY and OPENROUTER_API_KEY required")
            
        # LLM
        os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
        llm_instance = openai.LLM(
            api_key=openrouter_key,
            model="openai/gpt-4o-mini",
        )
        
        # TTS - Cartesia Sonic
        logger.info("   🎤 Initializing Cartesia TTS...")
        tts_instance = cartesia.TTS(
            model="sonic-english",
            voice="a01c369f-6d2d-4185-bc20-b32c225eab70", # British Lady
            api_key=cartesia_key,
        )
        
        # Await parallel tasks
        session_id, relationship_id = await db_task
        rag_system = await rag_task
        
        logger.info(f"⚡ Initialization completed in {time.perf_counter() - t_start:.3f}s")
        
        # Agent Session
        session = AgentSession(
            stt=deepgram.STT(model="nova-3", smart_format=True),
            llm=llm_instance,
            tts=tts_instance,
            vad=_vad_model or silero.VAD.load(min_speech_duration=0.1, min_silence_duration=0.3),
        )
        
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
        
        # Initial Greeting Logic
        greeting = "Hey Adrian, I'm here. What's on your mind?"
        await session.say(greeting, allow_interruptions=True)
        
    except Exception as e:
        logger.error(f"❌ Error in mediator session: {e}", exc_info=True)
        raise
    finally:
        if session_id and db_service:
            await asyncio.to_thread(db_service.end_mediator_session, session_id=session_id)
