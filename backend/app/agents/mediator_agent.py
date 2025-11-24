"""
Luna - Simple Mediator Agent
A friendly AI mediator for relationship conflicts
"""

import os
import json
import logging
import asyncio
import time
from datetime import datetime
from dotenv import load_dotenv
from livekit import agents, rtc
from livekit.agents import AgentServer, AgentSession, Agent, room_io, RunContext, llm, voice, JobContext
from livekit.plugins import deepgram, elevenlabs, openai, silero
from livekit.plugins import noise_cancellation

# Load environment variables
load_dotenv(".env.local")
load_dotenv(".env")

# Set ElevenLabs API key in environment early (plugin checks ELEVEN_API_KEY)
# This matches Voice Agent RAG pattern
if os.getenv("ELEVENLABS_API_KEY"):
    os.environ["ELEVEN_API_KEY"] = os.getenv("ELEVENLABS_API_KEY")

# Import settings
try:
    from app.config import settings
except ImportError:
    class Settings:
        LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
        LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
        LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
        ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
        OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    settings = Settings()

logger = logging.getLogger("mediator-agent")


class SimpleMediator(Agent):
    """Luna - A simple, friendly relationship mediator"""
    
    def __init__(self):
        instructions = """
You are Luna, a friendly and helpful AI mediator for couples.

Your personality:
- Warm, empathetic, and non-judgmental
- Curious and interested in understanding both perspectives
- Keep responses brief and natural (2-3 sentences max for voice)
- Use conversational, human language
- Supportive but honest

Your role:
- Listen to what each person has to say
- Help them understand each other better
- Suggest practical ways to resolve conflicts
- Be supportive and encouraging

Remember: You're here to help, not to judge. Everyone deserves to be heard.
"""
        super().__init__(instructions=instructions)


class RAGMediator(voice.Agent):
    """Luna - Mediator agent with RAG capabilities for answering questions about conversations"""
    
    def __init__(
        self,
        rag_system,
        conflict_id: str = None,
        relationship_id: str = None,
        instructions: str = "",
    ):
        """
        Initialize RAG mediator agent.
        
        Args:
            rag_system: TranscriptRAGSystem instance for retrieving context
            conflict_id: Current conflict ID
            relationship_id: Relationship ID
            instructions: Instructions for the agent (optional)
        """
        self.rag_system = rag_system
        self.conflict_id = conflict_id
        self.relationship_id = relationship_id
        
        # Default instructions if not provided
        if not instructions:
            instructions = """
You are Luna, a friendly and helpful AI mediator for couples.

Your personality:
- Warm, empathetic, and non-judgmental
- Curious and interested in understanding both perspectives
- Keep responses brief and natural (2-3 sentences max for voice)
- Use conversational, human language
- Supportive but honest

Your role:
- Listen to what each person has to say
- Help them understand each other better
- Suggest practical ways to resolve conflicts
- Be supportive and encouraging
- Answer questions about what was said in the conversation using the transcript context provided

You have access to the conversation transcript and can reference specific things that were said.
When answering questions about the conversation, use the provided transcript context to give accurate answers.
Reference specific speakers and their statements when relevant.

Remember: You're here to help, not to judge. Everyone deserves to be heard.
"""
        
        super().__init__(instructions=instructions)
    
    async def on_user_turn_completed(
        self,
        turn_ctx: llm.ChatContext,
        new_message: llm.ChatMessage,
    ) -> None:
        """
        Hook called when user completes a turn.
        Performs RAG lookup and injects context into chat context.
        
        Args:
            turn_ctx: Chat context for the turn
            new_message: The user's completed message
        """
        try:
            # Extract user's query - try both property and method access
            if hasattr(new_message, 'text_content'):
                # Try as method first
                try:
                    user_query = new_message.text_content()
                except TypeError:
                    # If it's a property, access directly
                    user_query = new_message.text_content
            elif hasattr(new_message, 'content'):
                user_query = str(new_message.content)
            else:
                logger.warning("Could not extract text from message")
                return
            
            if not user_query or not user_query.strip():
                logger.warning("Empty user query, skipping RAG lookup")
                return
            
            logger.info(f"User query: {user_query}")
            
            # Perform RAG lookup
            rag_context = self.rag_system.rag_lookup(
                query=user_query,
                conflict_id=self.conflict_id,
                relationship_id=self.relationship_id,
            )
            
            # Format context for LLM
            formatted_context = self.rag_system.format_context_for_llm(rag_context)
            
            # Inject context into chat context before LLM generates response
            turn_ctx.add_message(
                role="assistant",
                content=formatted_context,
            )
            
            logger.info("RAG context injected into chat context")
            
        except Exception as e:
            logger.error(f"Error in on_user_turn_completed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Don't fail the turn, just log the error


# Initialize agent server (similar to Voice Agent RAG)
server = AgentServer()

@server.rtc_session()
async def mediator_entrypoint(ctx: JobContext):
    """Main mediator agent entry point - automatically called for RTC sessions"""
    
    # CRITICAL: Log immediately to verify entrypoint is called (BEFORE filtering)
    logger.error("=" * 100)
    logger.error("🔴 ========== MEDIATOR ENTRYPOINT CALLED ==========")
    logger.error("=" * 100)
    logger.error(f"🎯 Room Name: {ctx.room.name}")
    logger.error(f"🆔 Job ID: {ctx.job.id}")
    # Room SID is a property, access it directly
    try:
        room_sid = str(ctx.room.sid) if ctx.room.sid else "N/A"
    except:
        room_sid = "N/A"
    logger.error(f"📋 Room SID: {room_sid}")
    
    # Filter: Only process mediator-* rooms
    # NOTE: Filter AFTER logging so we can see if entrypoint is called at all
    room_name = ctx.room.name
    if not room_name.startswith("mediator-"):
        logger.warning(f"⚠️  Room '{room_name}' doesn't match mediator-* pattern, skipping")
        logger.warning(f"   Expected: mediator-{{conflict_id}}")
        return
    
    # Show current participants in the room
    participant_count = len(ctx.room.remote_participants)
    participant_names = [p.identity for p in ctx.room.remote_participants.values()]
    logger.error(f"👥 Participants in room: {participant_count}")
    if participant_names:
        logger.error(f"   Names: {', '.join(participant_names)}")
    logger.error("=" * 100)
    
    # Extract conflict_id from room name
    conflict_id = room_name.replace("mediator-", "").split("?")[0]
    logger.info(f"   ✅ Extracted Conflict ID: {conflict_id}")
    
    stage_times = {}
    overall_start = time.time()
    
    try:
        # Stage 1: Initialization
        stage_start = time.time()
        logger.info(f"📍 Starting mediator session for SPECIFIC room")
        logger.info(f"   🏠 Room: {ctx.room.name}")
        logger.info(f"   🆔 Job ID: {ctx.job.id}")
        try:
            room_sid = str(ctx.room.sid) if ctx.room.sid else "N/A"
        except:
            room_sid = "N/A"
        logger.info(f"   📋 Room SID: {room_sid}")
        logger.info(f"   👥 Current participants: {participant_count}")
        logger.info(f"   🔗 This agent instance is joining THIS specific room session")
        
        stage_times['init'] = time.time() - stage_start
        logger.info(f"   ⏱️  Init: {stage_times['init']:.2f}s")
        
        # Stage 2: Configure API keys
        stage_start = time.time()
        logger.info(f"🔑 Configuring API keys...")
        
        elevenlabs_key = getattr(settings, 'ELEVENLABS_API_KEY', None) or os.getenv("ELEVENLABS_API_KEY")
        openrouter_key = getattr(settings, 'OPENROUTER_API_KEY', None) or os.getenv("OPENROUTER_API_KEY")
        
        if not elevenlabs_key or not openrouter_key:
            raise ValueError("ELEVENLABS_API_KEY and OPENROUTER_API_KEY required")
        
        stage_times['api_keys'] = time.time() - stage_start
        logger.info(f"   ⏱️  API Keys: {stage_times['api_keys']:.2f}s")
        
        # Stage 3: Setup OpenRouter
        stage_start = time.time()
        logger.info(f"🤖 Setting up LLM (gpt-4o-mini via OpenRouter)...")
        
        os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
        
        llm_instance = openai.LLM(
            api_key=openrouter_key,
            model="openai/gpt-4o-mini",
        )
        
        stage_times['llm_setup'] = time.time() - stage_start
        logger.info(f"   ✅ LLM ready")
        logger.info(f"   ⏱️  LLM Setup: {stage_times['llm_setup']:.2f}s")
        
        # Stage 4: Setup TTS
        stage_start = time.time()
        logger.info(f"🎙️  Setting up TTS (ElevenLabs)...")
        
        # ELEVEN_API_KEY should already be set at module level (like Voice Agent RAG)
        if not os.getenv("ELEVEN_API_KEY"):
            raise ValueError("ELEVEN_API_KEY not set - ElevenLabs TTS requires API key")
        
        # Use EXACT same TTS config as Voice Agent RAG - don't pass api_key, use environment
        # Voice Agent RAG pattern: Let plugin read from ELEVEN_API_KEY environment variable
        tts_instance = elevenlabs.TTS(
            model="eleven_flash_v2_5",  # Use default model (more stable)
            voice_id="ODq5zmih8GrVes37Dizd",  # Friendly female voice
            # Don't pass api_key - let it use ELEVEN_API_KEY from environment
            streaming_latency=3,  # Default latency for better stability
        )
        
        logger.info(f"   ✅ TTS configured with model=eleven_flash_v2_5, voice_id=ODq5zmih8GrVes37Dizd, ELEVEN_API_KEY={'SET' if os.getenv('ELEVEN_API_KEY') else 'MISSING'}")
        
        stage_times['tts_setup'] = time.time() - stage_start
        logger.info(f"   ✅ TTS ready")
        logger.info(f"   ⏱️  TTS Setup: {stage_times['tts_setup']:.2f}s")
        
        # Stage 5: Create agent session
        stage_start = time.time()
        logger.info(f"⚙️  Creating agent session...")
        
        session = AgentSession(
            stt=deepgram.STT(model="nova-3"),
            llm=llm_instance,
            tts=tts_instance,
            vad=silero.VAD.load(),
        )
        
        stage_times['session_create'] = time.time() - stage_start
        logger.info(f"   ✅ Session created")
        logger.info(f"   ⏱️  Session Create: {stage_times['session_create']:.2f}s")
        
        # Stage 6: Initialize RAG system and create agent
        stage_start = time.time()
        logger.info(f"🧠 Creating mediator agent (Luna) with RAG...")
        
        # Extract relationship_id if available (could be in room metadata or from conflict lookup)
        relationship_id = None
        if conflict_id:
            # Try to get relationship_id from Pinecone transcript metadata
            try:
                from app.services.pinecone_service import pinecone_service
                transcript_result = pinecone_service.get_by_conflict_id(
                    conflict_id=conflict_id,
                    namespace="transcripts"
                )
                if transcript_result and hasattr(transcript_result, 'metadata'):
                    relationship_id = transcript_result.metadata.get("relationship_id")
                    logger.info(f"   ✅ Found relationship_id: {relationship_id}")
            except Exception as e:
                logger.warning(f"   ⚠️ Could not fetch relationship_id: {e}")
        
        # Initialize RAG system
        try:
            from app.services.transcript_rag import TranscriptRAGSystem
            rag_system = TranscriptRAGSystem(k=5)
            logger.info(f"   ✅ RAG system initialized")
        except Exception as e:
            logger.error(f"   ❌ Failed to initialize RAG system: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Fallback to SimpleMediator if RAG fails
            rag_system = None
        
        # Create agent (RAGMediator if RAG available, otherwise SimpleMediator)
        if rag_system:
            agent = RAGMediator(
                rag_system=rag_system,
                conflict_id=conflict_id,
                relationship_id=relationship_id,
            )
            logger.info(f"   ✅ RAGMediator created with conflict_id={conflict_id}")
        else:
            agent = SimpleMediator()
            logger.info(f"   ✅ SimpleMediator created (RAG unavailable)")
        
        stage_times['agent_create'] = time.time() - stage_start
        logger.info(f"   ⏱️  Agent Create: {stage_times['agent_create']:.2f}s")
        
        # Stage 7: Connect to room
        stage_start = time.time()
        logger.info(f"🚀 Connecting to room...")
        
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
        
        stage_times['connect'] = time.time() - stage_start
        logger.info(f"   ✅ Connected to room")
        logger.info(f"   ⏱️  Connect: {stage_times['connect']:.2f}s")
        
        # Wait a moment for connection to stabilize
        await asyncio.sleep(1.0)
        
        # Generate initial greeting (like Voice Agent RAG)
        logger.info("🎤 Generating initial greeting...")
        try:
            await session.generate_reply(
                instructions=(
                    "Greet the user warmly and introduce yourself as Luna, their friendly relationship mediator. "
                    "Let them know you're here to help them reflect on their conversation and answer any questions they might have. "
                    "Be warm, empathetic, and encouraging."
                ),
            )
            logger.info("✅ Greeting generated successfully")
        except Exception as e:
            logger.error(f"❌ Error generating greeting: {e}", exc_info=True)
            # Don't fail the session if greeting fails
        
        # Session running - wait for user input
        logger.info(f"💬 Session active - Luna is listening...")
        logger.info("Voice agent session started successfully")
        
        # Session stays open automatically - don't call aclose() here
        # The session will close when user disconnects or room closes
        # Voice Agent RAG pattern: function ends here, session stays alive
        
    except Exception as e:
        logger.error(f"❌ Error in mediator session: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    
    finally:
        # Print timing summary
        total_time = time.time() - overall_start
        logger.info(f"\n⏱️  === TIMING SUMMARY ===")
        for stage, duration in sorted(stage_times.items()):
            logger.info(f"   {stage:20s}: {duration:6.2f}s")
        logger.info(f"   {'Total Setup':20s}: {sum(stage_times.values()):6.2f}s")
        logger.info(f"   {'Overall':20s}: {total_time:6.2f}s")
        logger.info(f"✅ Session closed")


# Agent is started via start_agent.py which uses agents.cli.run_app(server)
