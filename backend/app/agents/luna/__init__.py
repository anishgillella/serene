import json
import logging
import time
import asyncio
import os
from livekit import agents, rtc
from livekit.agents import AgentSession, room_io, JobContext, JobProcess
from livekit.plugins import deepgram, elevenlabs, openai, silero
from livekit.plugins import noise_cancellation

from .config import settings
from .agent import SimpleMediator, RAGMediator
from .tools import get_tools
from .moss_tools import get_moss_tools
from app.services.db_service import db_service
from app.services.moss_service import moss_service
from app.services.calendar_service import calendar_service

try:
    from langfuse import Langfuse
except ImportError:
    Langfuse = None

logger = logging.getLogger("luna-entrypoint")

# Global VAD model for prewarming
_vad_model = None

def prewarm(proc: JobProcess):
    """Pre-load heavy models (VAD) when worker process starts"""
    global _vad_model
    logger.info("🔥 Pre-warming VAD model...")
    try:
        _vad_model = silero.VAD.load(min_speech_duration=0.1, min_silence_duration=0.3)
        logger.info("✅ VAD model loaded successfully")
    except Exception as e:
        logger.error(f"❌ Failed to pre-warm VAD model: {e}")

def _parse_dispatch_metadata(ctx: JobContext) -> dict:
    if not ctx.job.metadata:
        return {}
    try:
        return json.loads(ctx.job.metadata)
    except json.JSONDecodeError:
        logger.warning("ctx.job.metadata was not valid JSON")
        return {}


async def mediator_entrypoint(ctx: JobContext):
    """Main mediator agent entry point"""
    
    logger.info(f"📍 Starting mediator session for room: {ctx.room.name}")
    
    dispatch_meta = _parse_dispatch_metadata(ctx)

    # Filter: Only process mediator-* rooms
    room_name = ctx.room.name
    if not room_name.startswith("mediator-"):
        logger.warning(f"⚠️  Room '{room_name}' doesn't match mediator-* pattern, skipping")
        return
    
    # Extract conflict_id — prefer dispatch metadata, fall back to room name
    conflict_id = dispatch_meta.get("conflict_id") or room_name.replace("mediator-", "").split("?")[0]
    relationship_id_from_meta = dispatch_meta.get("relationship_id")
    user_id = dispatch_meta.get("user_id", "anonymous")
    logger.info(f"   ✅ Conflict ID: {conflict_id}, user: {user_id}")
    
    # Parallel Initialization Tasks
    async def init_db_session():
        if db_service:
            try:
                sid = await asyncio.to_thread(
                    db_service.create_mediator_session,
                    conflict_id=conflict_id
                )
                logger.info(f"   ✅ Created DB session: {sid}")
                return sid
            except Exception as e:
                logger.error(f"   ❌ Failed to create DB session: {e}")
        return None

    async def init_rag_system():
        try:
            # Check if we need RAG (if conflict_id exists)
            if not conflict_id:
                return None, None
                
            # Get relationship_id
            rel_id = None
            if db_service:
                try:
                    conflict_data = await asyncio.to_thread(db_service.get_conflict_by_id, conflict_id=conflict_id)
                    if conflict_data:
                        rel_id = str(conflict_data.get("relationship_id"))
                except Exception:
                    pass
            
            # Initialize RAG system
            from app.services.transcript_rag import TranscriptRAGSystem
            # This might involve network calls to Pinecone/OpenAI, so run in thread if blocking
            # But TranscriptRAGSystem init is mostly setting config, actual connections are lazy or fast
            rag = TranscriptRAGSystem(k=5, include_profiles=True, include_calendar=False)
            return rag, rel_id
        except ImportError:
            logger.warning("RAG system not available")
            return None, None
        except Exception as e:
            logger.error(f"Error initializing RAG: {e}")
            return None, None

    # Start parallel tasks
    # 1. DB Session
    # 2. RAG System (includes DB lookup for relationship_id)
    # 3. AI Services (LLM, TTS) - these are fast but good to group
    
    # Setup AI Services (Synchronous but fast)
    elevenlabs_key = settings.ELEVENLABS_API_KEY
    openrouter_key = settings.OPENROUTER_API_KEY
    
    if not elevenlabs_key or not openrouter_key:
        raise ValueError("ELEVENLABS_API_KEY and OPENROUTER_API_KEY required")
        
    os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
    
    llm_instance = openai.LLM(
        api_key=openrouter_key,
        model="google/gemini-2.5-flash",
    )
    
    tts_instance = elevenlabs.TTS(
        model="eleven_flash_v2_5",
        voice_id="21m00Tcm4TlvDq8ikWAM", # Rachel
        api_key=elevenlabs_key,
        streaming_latency=3,
    )

    # Run async tasks
    session_task = asyncio.create_task(init_db_session())
    rag_task = asyncio.create_task(init_rag_system())
    
    # Wait for results
    session_id = await session_task
    rag_system, relationship_id = await rag_task

    if relationship_id_from_meta:
        relationship_id = relationship_id_from_meta

    # Preload Moss indexes for sub-10ms retrieval during voice session
    if moss_service.enabled:
        await moss_service.preload_session_indexes()

    # Fetch partner names for dynamic greeting and instructions
    partner_a_name = "Partner A"
    partner_b_name = "Partner B"
    if relationship_id and db_service:
        try:
            partner_names = await asyncio.to_thread(
                db_service.get_partner_names,
                relationship_id
            )
            partner_a_name = partner_names.get("partner_a", "Partner A")
            partner_b_name = partner_names.get("partner_b", "Partner B")
            logger.info(f"   ✅ Loaded partner names: {partner_a_name} & {partner_b_name}")
        except Exception as e:
            logger.warning(f"   ⚠️ Could not load partner names: {e}")

    try:
        # Use pre-warmed VAD or load new one
        global _vad_model
        if _vad_model is None:
            logger.info("⚠️ VAD model not pre-warmed, loading now (this will be slow)")
            _vad_model = silero.VAD.load(min_speech_duration=0.1, min_silence_duration=0.3)
            
        # Agent Session
        session = AgentSession(
            stt=deepgram.STT(model="nova-3", smart_format=True),
            llm=llm_instance,
            tts=tts_instance,
            vad=_vad_model,
        )
        
        tools = get_tools(conflict_id, relationship_id, partner_b_name=partner_b_name)
        tools += get_moss_tools(
            relationship_id=relationship_id,
            conflict_id=conflict_id,
            room=ctx.room,
        )
        
        # Create Agent with dynamic partner names
        if rag_system:
            agent = RAGMediator(
                rag_system,
                conflict_id,
                relationship_id,
                session_id,
                tools=tools,
                partner_a_name=partner_a_name,
                partner_b_name=partner_b_name
            )
        else:
            agent = SimpleMediator(
                session_id,
                tools=tools,
                partner_a_name=partner_a_name,
                partner_b_name=partner_b_name
            )
            
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
        
        # Initial Greeting Logic with dynamic partner name
        greeting = f"Hey {partner_a_name}, I'm here. What's on your mind?"
        await session.say(greeting, allow_interruptions=True)
        
    except Exception as e:
        logger.error(f"❌ Error in mediator session: {e}", exc_info=True)
        raise
    finally:
        if session_id and db_service:
            await asyncio.to_thread(db_service.end_mediator_session, session_id=session_id)
        
        # Explicit cleanup to save memory
        import gc
        gc.collect()
