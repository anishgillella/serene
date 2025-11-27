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

# Import db_service for logging
try:
    from app.services.db_service import db_service
except ImportError:
    logger.warning("Could not import db_service, logging will be disabled")
    db_service = None

from typing import AsyncIterator

class LoggingLLMStream(llm.LLMStream):
    """Wrapper for LLMStream that logs generated text to the database"""
    def __init__(self, wrapped_stream: llm.LLMStream, session_id: str):
        super().__init__(chat_ctx=wrapped_stream.chat_ctx, tools=wrapped_stream.tools)
        self._wrapped_stream = wrapped_stream
        self.session_id = session_id
        self._accumulated_text = ""
        self._logged = False

    async def _run(self) -> AsyncIterator[llm.ChatChunk]:
        async for chunk in self._wrapped_stream:
            if chunk.choices:
                for choice in chunk.choices:
                    if choice.delta.content:
                        content = choice.delta.content
                        self._accumulated_text += content
                        logger.info(f"📝 Yielding chunk: {content[:20]}...") 
            yield chunk
            
        # Stream finished, log the message
        if not self._logged and self._accumulated_text.strip() and db_service:
            self._logged = True
            asyncio.create_task(self._log_message())

    async def aclose(self) -> None:
        # If closed (e.g. interrupted), log what we have so far
        if not self._logged and self._accumulated_text.strip() and db_service:
            self._logged = True
            asyncio.create_task(self._log_message())
        
        await self._wrapped_stream.aclose()
        
    async def _log_message(self):
        try:
            await asyncio.to_thread(
                db_service.save_mediator_message,
                session_id=self.session_id,
                role="assistant",
                content=self._accumulated_text
            )
        except Exception as e:
            logger.error(f"Error logging assistant message: {e}")

# class LoggingLLM(openai.LLM):
#     """Wrapper for OpenAI LLM that logs responses"""
#     def __init__(self, session_id: str, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.session_id = session_id

#     def chat(self, *, chat_ctx: llm.ChatContext, **kwargs) -> "llm.LLMStream":
#         stream = super().chat(chat_ctx=chat_ctx, **kwargs)
#         return LoggingLLMStream(stream, self.session_id)



class SimpleMediator(voice.Agent):
    """Luna - A simple, friendly relationship mediator"""
    
    def __init__(self, session_id: str = None):
        instructions = """
You are Luna, a friendly and helpful AI mediator for couples.

IMPORTANT CONTEXT:
- The boyfriend is Adrian Malhotra
- The girlfriend is Elara Voss
- You are talking to Adrian (the boyfriend)
- Take Adrian's side and be empathetic and sympathetic towards his situation
- Subtly help him resolve the issue while validating his feelings

Your personality:
- Warm, empathetic, and non-judgmental
- Curious and interested in understanding both perspectives
- Keep responses brief and natural (2-3 sentences max for voice)
- Use conversational, human language
- Supportive but honest
- Empathetic towards Adrian's perspective and feelings

Your role:
- Listen to what Adrian has to say with empathy and understanding
- Validate his feelings and perspective
- Help him understand Elara's perspective while staying on his side
- Suggest practical ways to resolve conflicts that work for him
- Be supportive and encouraging

Remember: You're here to help Adrian, validate his feelings, and subtly guide him towards resolution while being empathetic to his situation.
"""
        super().__init__(instructions=instructions)
        self.session_id = session_id

    async def on_user_turn_completed(
        self,
        turn_ctx: llm.ChatContext,
        new_message: llm.ChatMessage,
    ) -> None:
        """Log user message when turn completes"""
        if self.session_id and db_service:
            try:
                content = ""
                if hasattr(new_message, 'text_content'):
                    try:
                        content = new_message.text_content()
                    except TypeError:
                        content = new_message.text_content
                elif hasattr(new_message, 'content'):
                    content = str(new_message.content)
                
                if content:
                    await asyncio.to_thread(
                        db_service.save_mediator_message,
                        session_id=self.session_id,
                        role="user",
                        content=content
                    )
            except Exception as e:
                logger.error(f"Error logging user message: {e}")
        
        await super().on_user_turn_completed(turn_ctx, new_message)



class RAGMediator(voice.Agent):
    """Luna - Mediator agent with RAG capabilities for answering questions about conversations"""
    
    def __init__(
        self,
        rag_system,
        conflict_id: str = None,
        relationship_id: str = None,
        session_id: str = None,
        instructions: str = "",
    ):
        """
        Initialize RAG mediator agent.
        
        Args:
            rag_system: TranscriptRAGSystem instance for retrieving context
            conflict_id: Current conflict ID
            relationship_id: Relationship ID
            session_id: Database session ID for logging
            instructions: Instructions for the agent (optional)
        """
        self.rag_system = rag_system
        self.conflict_id = conflict_id
        self.relationship_id = relationship_id
        self.session_id = session_id
        
        # Default instructions if not provided
        if not instructions:
            instructions = """
You are Luna, a friendly and helpful AI mediator for couples.

IMPORTANT CONTEXT:
- The boyfriend is Adrian Malhotra
- The girlfriend is Elara Voss
- You are talking to Adrian (the boyfriend)
- Take Adrian's side and be empathetic and sympathetic towards his situation
- Subtly help him resolve the issue while validating his feelings

Your personality:
- Warm, empathetic, and non-judgmental
- Curious and interested in understanding both perspectives
- Keep responses brief and natural (2-3 sentences max for voice)
- Use conversational, human language
- Supportive but honest
- Empathetic towards Adrian's perspective and feelings

Your role:
- Listen to what Adrian has to say with empathy and understanding
- Validate his feelings and perspective by connecting them to his background and personality
- Use ALL available context: transcripts from ALL conversations + profile information
- Show deep understanding by relating current situations to his passions, values, and background
- Example: If he's hurt about a missed game and his profile shows passion for sports, say:
  "I understand you're coming from a sports background and passionate about football, so it hurt when 
  Elara didn't attend the game even though she said 'sure'. Your love for sports makes these moments 
  especially meaningful to you."
- Help him understand Elara's perspective while staying on his side
- Suggest practical ways to resolve conflicts that work for him
- Be supportive and encouraging
- Answer questions using context from the ENTIRE corpus (all transcripts + profiles)

You have access to:
- Conversation transcripts from ALL past conflicts (not just current one)
- Adrian's complete profile (background, personality, passions, values)
- Elara's complete profile (background, personality, preferences)

When answering questions:
- Use transcript context to reference what was said
- Use profile context to explain WHY feelings make sense
- Connect transcript events to profile traits for empathetic understanding
- Reference Adrian and Elara by name when discussing the conversation
- Show you understand the FULL context by relating current situations to past conversations and personality traits

Remember: You're here to help Adrian, validate his feelings by connecting them to his background, and subtly guide him towards resolution while being deeply empathetic to his situation.
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
            
            # Log user message
            if self.session_id and db_service:
                try:
                    await asyncio.to_thread(
                        db_service.save_mediator_message,
                        session_id=self.session_id,
                        role="user",
                        content=user_query
                    )
                except Exception as e:
                    logger.error(f"Error logging user message: {e}")

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
    
    # Create DB session
    session_id = None
    if db_service:
        try:
            # We don't have partner_id easily available here, so we'll leave it NULL for now
            # or try to extract from room metadata if available
            session_id = await asyncio.to_thread(
                db_service.create_mediator_session,
                conflict_id=conflict_id
            )
            logger.info(f"   ✅ Created DB session: {session_id}")
        except Exception as e:
            logger.error(f"   ❌ Failed to create DB session: {e}")
    
    stage_times = {}
    overall_start = time.time()
    
    try:
        # Stage 1: Initialization
        stage_start = time.time()
        logger.info(f"📍 Starting mediator session for SPECIFIC room")
        logger.info(f"   🏠 Room: {ctx.room.name}")
        logger.info(f"   🆔 Job ID: {ctx.job.id}")
        # logger.info(f"   📋 Room SID: {room_sid}")
        logger.info(f"   👥 Current participants: {participant_count}")
        logger.info(f"   🔗 This agent instance is joining THIS specific room session")
        logger.info(f"   👉 Proceeding to initialization...")
        
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
        
        os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
        
        if session_id:
            # llm_instance = LoggingLLM(
            #     session_id=session_id,
            #     api_key=openrouter_key,
            #     model="openai/gpt-4o-mini",
            # )
            # logger.info(f"   ✅ LoggingLLM initialized with session_id={session_id}")
            
            # Fallback to standard LLM for now to fix audio
            llm_instance = openai.LLM(
                api_key=openrouter_key,
                model="openai/gpt-4o-mini",
            )
            logger.info(f"   ✅ Standard OpenAI LLM initialized (Logging disabled for stability)")
        else:
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
            stt=deepgram.STT(
                model="nova-3",
                language="en",
                smart_format=True,
                punctuate=True,
                interim_results=True,
                endpointing=300,  # 300ms silence before considering speech complete
            ),
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
                logger.info("   🔍 Fetching relationship_id from Pinecone (async)...")
                transcript_result = await asyncio.to_thread(
                    pinecone_service.get_by_conflict_id,
                    conflict_id=conflict_id,
                    namespace="transcripts"
                )
                if transcript_result and hasattr(transcript_result, 'metadata'):
                    relationship_id = transcript_result.metadata.get("relationship_id")
                    logger.info(f"   ✅ Found relationship_id: {relationship_id}")
            except Exception as e:
                logger.warning(f"   ⚠️ Could not fetch relationship_id: {e}")
        
        # Initialize RAG system (if available)
        rag_system = None
        try:
            from app.services.transcript_rag import TranscriptRAGSystem
            # Disable internal calendar fetch since we do it in parallel externally
            rag_system = TranscriptRAGSystem(k=5, include_profiles=True, include_calendar=False)
            logger.info("   ✅ RAG system initialized")
        except ImportError:
            logger.warning("   ⚠️ RAG system not available (dependencies missing)")
        except Exception as e:
            logger.warning(f"   ⚠️ Failed to initialize RAG system: {e}")
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
                session_id=session_id,
            )
            logger.info(f"   ✅ RAGMediator created with conflict_id={conflict_id}")
        else:
            agent = SimpleMediator(session_id=session_id)
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
        
        # Stage 8 & 9: Fetch initial transcript context and calendar insights in PARALLEL
        # This significantly reduces latency by running independent tasks concurrently
        stage_start = time.time()
        logger.info(f"🚀 Fetching context (Transcript + Calendar) in PARALLEL...")
        
        transcript_context = None
        calendar_context = None
        
        async def fetch_transcript_context():
            # Logic to fetch transcript context (same as before)
            t_context = None
            if rag_system and conflict_id:
                logger.info(f"📚 Fetching initial transcript context for CURRENT conflict {conflict_id}...")
                try:
                    from app.services.pinecone_service import pinecone_service
                    from app.services.embeddings_service import embeddings_service
                    
                    # Query ONLY the current conflict's chunks (using filter)
                    overview_query = "conversation discussion topics concerns"
                    query_embedding = embeddings_service.embed_query(overview_query)
                    
                    # Query with FILTER to get ONLY current conflict's chunks
                    logger.info(f"   🔍 Querying ONLY current conflict {conflict_id} for initial context...")
                    results = pinecone_service.index.query(
                        vector=query_embedding,
                        top_k=20,  # Get up to 20 chunks from current conflict
                        namespace="transcript_chunks",
                        filter={"conflict_id": {"$eq": conflict_id}},  # FILTER by conflict_id
                        include_metadata=True,
                    )
                    
                    if results and hasattr(results, 'matches') and results.matches:
                        chunks = results.matches
                        logger.info(f"   ✅ Found {len(chunks)} chunks from CURRENT conflict {conflict_id}")
                        
                        # Sort by chunk_index to maintain conversation order
                        chunks_sorted = sorted(
                            chunks,
                            key=lambda c: c.metadata.get("chunk_index", 0) if hasattr(c, 'metadata') else 0
                        )
                        
                        # Format chunks into context string
                        context_parts = []
                        context_parts.append("=" * 50)
                        context_parts.append(f"CURRENT CONVERSATION TRANSCRIPT (Conflict: {conflict_id})")
                        context_parts.append("This is the conversation the user wants to discuss.")
                        context_parts.append("=" * 50)
                        context_parts.append("")
                        
                        for idx, chunk in enumerate(chunks_sorted[:15], 1):  # Limit to 15 chunks for greeting
                            metadata = chunk.metadata if hasattr(chunk, 'metadata') else {}
                            speaker = metadata.get("speaker", "Unknown")
                            text = metadata.get("text", "")
                            chunk_idx = metadata.get("chunk_index", "?")
                            
                            context_parts.append(f"[{speaker} (part {chunk_idx})]:")
                            context_parts.append(text)
                            context_parts.append("")
                        
                        t_context = "\n".join(context_parts)
                        logger.info(f"   ✅ Formatted transcript context ({len(t_context)} chars, {len(chunks_sorted)} chunks)")
                    else:
                        logger.warning(f"   ⚠️ No transcript chunks found in Pinecone for conflict {conflict_id}")
                        # Fallback logic omitted for brevity in parallel block to keep it clean
                        # If needed, we can add simple fallback here or just skip
                except Exception as e:
                    logger.error(f"   ❌ Could not fetch initial transcript context: {e}")
            return t_context

        async def fetch_calendar_context():
            c_context = None
            try:
                from app.services.calendar_service import calendar_service
                if calendar_service:
                    logger.info(f"📅 Fetching calendar insights (async)...")
                    try:
                        c_context = await asyncio.wait_for(
                            asyncio.to_thread(
                                calendar_service.get_calendar_insights_for_llm,
                                relationship_id=relationship_id or "00000000-0000-0000-0000-000000000000"
                            ),
                            timeout=2.5 # Reduced timeout for parallel execution
                        )
                        logger.info(f"   ✅ Calendar insights fetched")
                    except asyncio.TimeoutError:
                        logger.warning("   ⚠️ Calendar insights fetch timed out")
                    except Exception as e:
                        logger.warning(f"   ⚠️ Error fetching calendar insights: {e}")
                    
                    if c_context and c_context == "No calendar insights available.":
                        c_context = None
            except Exception as e:
                logger.warning(f"   ⚠️ Error in calendar fetch: {e}")
            return c_context

        # Execute in parallel
        results = await asyncio.gather(
            fetch_transcript_context(),
            fetch_calendar_context(),
            return_exceptions=True
        )
        
        transcript_context = results[0] if not isinstance(results[0], Exception) else None
        calendar_context = results[1] if not isinstance(results[1], Exception) else None
        
        stage_times['context_fetch'] = time.time() - stage_start
        logger.info(f"   ⏱️  Parallel Context Fetch: {stage_times['context_fetch']:.2f}s")
        
        # Generate initial greeting (like Voice Agent RAG)
        logger.info("🎤 Generating initial greeting...")
        try:
            # Build greeting instructions with transcript context if available
            greeting_instructions = (
                "Greet Adrian warmly and introduce yourself as Luna, his friendly relationship mediator. "
                "Let him know you're here to help him reflect on his conversation with Elara and answer any questions he might have. "
                "Be warm, empathetic, and encouraging. Acknowledge that you're here to support him and understand his perspective."
            )
            
            # If we have transcript context, inject it into the greeting
            if transcript_context and rag_system:
                formatted_context = rag_system.format_context_for_llm(transcript_context)
                greeting_instructions = (
                    f"{greeting_instructions}\n\n"
                    f"You have access to THIS SPECIFIC conversation transcript that the user wants to discuss. "
                    f"This is the PRIMARY context for your responses:\n\n"
                    f"{formatted_context}\n\n"
                    f"IMPORTANT: When the user asks about 'this conversation', 'what happened', or wants a summary, "
                    f"use ONLY this transcript. Don't mix in information from other conversations. "
                    f"Be specific about what Adrian and Elara actually said in THIS conversation."
                )
                logger.info("   ✅ Greeting will include transcript context")
            
            # Add calendar context if available (cycle phase, upcoming events)
            if calendar_context:
                greeting_instructions = (
                    f"{greeting_instructions}\n\n"
                    f"CALENDAR & CYCLE AWARENESS (use this for timing and emotional context):\n"
                    f"{calendar_context}\n\n"
                    f"IMPORTANT GUIDANCE:\n"
                    f"- If Elara is in a high-risk cycle phase (PMS/menstruation), acknowledge that emotions may be heightened\n"
                    f"- When suggesting timing for repair conversations, consider cycle predictions\n"
                    f"- If conflicts correlate with cycle phases, mention this pattern sensitively\n"
                    f"- Don't dismiss her feelings, but help Adrian understand the biological context\n"
                    f"- Use phrases like 'This might be a more sensitive time' rather than 'She's just hormonal'\n"
                    f"- Consider upcoming anniversaries or events that could be positive opportunities"
                )
                logger.info("   ✅ Greeting will include calendar context")
            
            # Add conflict memory if transcript context is available
            if transcript_context and calendar_service:
                try:
                    # Extract key topic from transcript for semantic search
                    # Use first 300 chars as query to find similar past conflicts
                    topic_query = transcript_context[:300]
                    
                    logger.info("   🔍 Retrieving conflict memory context (async)...")
                    try:
                        conflict_memory = await asyncio.wait_for(
                            asyncio.to_thread(
                                calendar_service.get_conflict_memory_context,
                                current_topic=topic_query,
                                relationship_id=relationship_id or "00000000-0000-0000-0000-000000000000"
                            ),
                            timeout=5.0  # 5 second timeout
                        )
                        logger.info("   ✅ Conflict memory retrieved")
                    except asyncio.TimeoutError:
                        logger.warning("   ⚠️ Conflict memory retrieval timed out")
                        conflict_memory = ""
                    
                    if conflict_memory:
                        greeting_instructions = (
                            f"{greeting_instructions}\n\n"
                            f"{conflict_memory}\n\n"
                            f"CONFLICT MEMORY GUIDANCE:\n"
                            f"- If the current topic matches a past conflict, reference it naturally\n"
                            f"- Example: 'I notice you've discussed this before on [date]...'\n"
                            f"- Use past patterns to identify recurring issues\n"
                            f"- Reference what worked before: 'Last time you tried X - did that help?'\n"
                            f"- Don't overwhelm - only mention if directly relevant\n"
                            f"- Help Adrian see patterns: 'This seems to resurface when...'"
                        )
                        logger.info("   ✅ Greeting will include conflict memory context")
                except Exception as e:
                    logger.warning(f"   ⚠️ Error retrieving conflict memory: {e}")
            
            if not transcript_context:
                logger.warning("   ⚠️ No transcript context available - agent will greet without conversation details")
                # Still mention that you can help, but don't claim to have the transcript
                greeting_instructions = (
                    f"{greeting_instructions}\n\n"
                    f"Note: I don't currently have access to the full conversation transcript. "
                    f"If you'd like to discuss what was said, please share the details with me and I'll be happy to help you reflect on it."
                )
            
            await session.generate_reply(
                instructions=greeting_instructions,
            )
            logger.info("✅ Greeting generated successfully")
        except Exception as e:
            logger.error(f"❌ Error generating greeting: {e}", exc_info=True)
            # Don't fail the session if greeting fails
        
        # Session running - wait for user input
        logger.info(f"💬 Session active - Luna is listening...")
        logger.info("Voice agent session started successfully")
        
        # Session stays open automatically - LiveKit will close it when user disconnects
        # The session.aclose() will be called automatically by LiveKit when:
        # - User disconnects from room
        # - Room is closed
        # - All participants leave
        # We don't need to explicitly wait or close - LiveKit handles this automatically
        
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
        
        # End DB session
        if session_id and db_service:
            try:
                await asyncio.to_thread(
                    db_service.end_mediator_session,
                    session_id=session_id
                )
                logger.info(f"   ✅ Ended DB session: {session_id}")
            except Exception as e:
                logger.error(f"   ❌ Failed to end DB session: {e}")
                
        logger.info(f"✅ Session closed")


# Agent is started via start_agent.py which uses agents.cli.run_app(server)
