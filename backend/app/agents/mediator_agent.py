"""
LiveKit Mediator Agent - Luna
A friendly AI mediator that can help with relationship conflicts and conversations.
Based on the Livekit Voice Agent implementation.
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from livekit import agents, rtc
from livekit.agents import AgentServer, AgentSession, Agent, room_io, function_tool, RunContext, inference
from livekit.plugins import elevenlabs, openai, silero
from livekit.plugins import noise_cancellation

# Load environment variables from .env.local or .env (for console mode)
load_dotenv(".env.local")
load_dotenv(".env")

# Import settings after loading env (for production use)
try:
    from app.config import settings
    from app.services.pinecone_service import pinecone_service
    from app.services.db_service import db_service
except ImportError:
    # If running standalone, create minimal settings
    class Settings:
        LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
        LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
        LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
        ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
        OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    settings = Settings()
    pinecone_service = None
    db_service = None

logger = logging.getLogger("mediator-agent")


async def retrieve_conflict_context(conflict_id: str) -> str:
    """
    Helper function to retrieve conflict information including transcript, analysis, and repair plans.
    Used by both the tool and the agent initialization.
    """
    try:
        if not conflict_id:
            return "I'm sorry, but I don't have a conflict ID to retrieve information for."
        
        logger.info(f"🔍 Retrieving conflict context for {conflict_id}")
        
        # Check if pinecone_service is available (might be None in console mode)
        if not pinecone_service:
            return "I'm running in console mode and don't have access to conflict data. Please run me through the web interface to access conflict information."
        
        # Retrieve transcript - try Pinecone first, then Supabase storage as fallback
        transcript_result = pinecone_service.get_by_conflict_id(
            conflict_id=conflict_id,
            namespace="transcripts"
        )
        
        transcript_text = ""
        if transcript_result and hasattr(transcript_result, 'metadata') and transcript_result.metadata:
            transcript_text = transcript_result.metadata.get("transcript_text", "")
            if transcript_text:
                logger.info(f"✅ Retrieved transcript from Pinecone ({len(transcript_text)} chars)")
                # Truncate if too long (keep last 2000 chars for context)
                if len(transcript_text) > 2000:
                    transcript_text = "..." + transcript_text[-2000:]
            else:
                logger.warning(f"⚠️ Transcript found but transcript_text is empty in metadata")
        
        # Fallback: Try fetching from S3 if Pinecone doesn't have it
        if not transcript_text:
            logger.info(f"🔄 Transcript not in Pinecone, trying S3 storage...")
            try:
                from supabase import create_client, Client
                
                # Get Supabase credentials from settings (might not be available in console mode)
                supabase_url = getattr(settings, 'SUPABASE_URL', None) or os.getenv("SUPABASE_URL")
                supabase_key = getattr(settings, 'SUPABASE_KEY', None) or os.getenv("SUPABASE_KEY")
                
                if not supabase_url or not supabase_key:
                    logger.warning(f"⚠️ Supabase credentials not available, skipping S3 fallback")
                else:
                    supabase: Client = create_client(supabase_url, supabase_key)
                    
                    # Get conflict record to find transcript_path (which is now S3 URL/path)
                    conflict_response = supabase.table("conflicts").select("*").eq("id", conflict_id).execute()
                    
                    if conflict_response.data and len(conflict_response.data) > 0:
                        conflict = conflict_response.data[0]
                        transcript_path = conflict.get("transcript_path")
                        
                        if transcript_path:
                            logger.info(f"📁 Found transcript_path: {transcript_path}")
                            # Extract S3 key from S3 URL if it's a full URL, otherwise use as-is
                            if transcript_path.startswith("s3://"):
                                # Extract key from s3://bucket/key format
                                s3_key = transcript_path.replace(f"s3://{settings.S3_BUCKET_NAME}/", "")
                            elif transcript_path.startswith("transcripts/"):
                                s3_key = transcript_path
                            elif "/" in transcript_path:
                                # Assume it's already a valid path
                                s3_key = transcript_path
                            else:
                                # Old format without folder prefix
                                s3_key = f"transcripts/{transcript_path}"
                            
                            # Download from S3
                            from app.services.s3_service import s3_service
                            file_response = s3_service.download_file(s3_key)
                            
                            if file_response:
                                # Parse JSON transcript (file_response is already bytes from S3)
                                transcript_data = json.loads(file_response.decode('utf-8'))
                                
                                # Extract transcript text from segments
                                if isinstance(transcript_data, list):
                                    # Array of segments
                                    transcript_lines = []
                                    for segment in transcript_data:
                                        if isinstance(segment, dict):
                                            speaker = segment.get("speaker", segment.get("speaker_name", "Speaker"))
                                            text = segment.get("text", segment.get("transcript", segment.get("message", "")))
                                            if text:
                                                transcript_lines.append(f"{speaker}: {text}")
                                    transcript_text = "\\n".join(transcript_lines)
                                elif isinstance(transcript_data, dict):
                                    # Object with transcript_text or segments
                                    if "transcript_text" in transcript_data:
                                        transcript_text = transcript_data["transcript_text"]
                                    elif "segments" in transcript_data:
                                        transcript_lines = []
                                        for segment in transcript_data["segments"]:
                                            speaker = segment.get("speaker", "Speaker")
                                            text = segment.get("text", "")
                                            if text:
                                                transcript_lines.append(f"{speaker}: {text}")
                                        transcript_text = "\\n".join(transcript_lines)
                                
                                if transcript_text:
                                    logger.info(f"✅ Retrieved transcript from Supabase storage ({len(transcript_text)} chars)")
                                    # Truncate if too long
                                    if len(transcript_text) > 2000:
                                        transcript_text = "..." + transcript_text[-2000:]
                        else:
                            logger.warning(f"⚠️ No transcript_path in conflict record")
                    else:
                        logger.warning(f"⚠️ Conflict {conflict_id} not found in database")
            except Exception as e:
                logger.error(f"❌ Error fetching transcript from Supabase: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        if not transcript_text:
            logger.warning(f"⚠️ No transcript found for conflict {conflict_id} in Pinecone or Supabase")
        
        # Retrieve analysis
        analysis_result = pinecone_service.get_by_conflict_id(
            conflict_id=conflict_id,
            namespace="analysis"
        )
        
        analysis_summary = ""
        if analysis_result and analysis_result.metadata:
            analysis_json_str = analysis_result.metadata.get("full_analysis_json", "")
            if analysis_json_str:
                try:
                    analysis_data = json.loads(analysis_json_str)
                    fight_summary = analysis_data.get("fight_summary", "")
                    root_causes = analysis_data.get("root_causes", [])
                    
                    analysis_summary = f"Fight Summary: {fight_summary}\\n"
                    if root_causes:
                        analysis_summary += f"Root Causes: {', '.join(root_causes[:3])}"  # Limit to 3 causes
                except Exception as e:
                    logger.warning(f"Failed to parse analysis JSON: {e}")
                    analysis_summary = analysis_result.metadata.get("fight_summary", "")
        
        # Retrieve repair plans
        repair_plan_bf = None
        repair_plan_gf = None
        
        bf_result = pinecone_service.get_by_conflict_id(
            conflict_id=f"{conflict_id}_boyfriend",
            namespace="repair_plans"
        )
        if bf_result and bf_result.metadata:
            repair_plan_json = bf_result.metadata.get("full_repair_plan_json", "")
            if repair_plan_json:
                try:
                    repair_plan_bf = json.loads(repair_plan_json)
                except Exception:
                    pass
        
        gf_result = pinecone_service.get_by_conflict_id(
            conflict_id=f"{conflict_id}_girlfriend",
            namespace="repair_plans"
        )
        if gf_result and gf_result.metadata:
            repair_plan_json = gf_result.metadata.get("full_repair_plan_json", "")
            if repair_plan_json:
                try:
                    repair_plan_gf = json.loads(repair_plan_json)
                except Exception:
                    pass
        
        # Build context string
        context_parts = []
        
        if transcript_text:
            context_parts.append(f"CONFLICT TRANSCRIPT:\\n{transcript_text}")
        
        if analysis_summary:
            context_parts.append(f"ANALYSIS:\\n{analysis_summary}")
        
        if repair_plan_bf or repair_plan_gf:
            context_parts.append("REPAIR SUGGESTIONS:")
            if repair_plan_bf:
                apology = repair_plan_bf.get("apology_script", "")
                steps = repair_plan_bf.get("steps", [])
                if apology:
                    context_parts.append(f"For Partner A: {apology[:200]}")
                if steps:
                    context_parts.append(f"Steps: {', '.join(steps[:3])}")
            
            if repair_plan_gf:
                apology = repair_plan_gf.get("apology_script", "")
                steps = repair_plan_gf.get("steps", [])
                if apology:
                    context_parts.append(f"For Partner B: {apology[:200]}")
                if steps:
                    context_parts.append(f"Steps: {', '.join(steps[:3])}")
        
        if not context_parts:
            error_msg = f"I couldn't find detailed information for conflict {conflict_id[:8]}... "
            if not transcript_text:
                error_msg += "The transcript hasn't been stored yet. "
            if not analysis_summary:
                error_msg += "The analysis hasn't been generated yet. "
            error_msg += "Please make sure the conflict has been completed and the transcript has been stored."
            logger.warning(f"⚠️ No context found for conflict {conflict_id}: transcript={bool(transcript_text)}, analysis={bool(analysis_summary)}")
            return error_msg
        
        return "\\n\\n".join(context_parts)
        
    except Exception as e:
        logger.error(f"Error retrieving conflict context: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return f"I encountered an error retrieving conflict information: {str(e)}"


class MediatorAgent(Agent):
    """
    Luna - A friendly mediator that can help with relationship conflicts.
    Personality: Warm, helpful, slightly curious, and always ready to assist.
    Can access conflict context when asked.
    """
    
    def __init__(
        self, 
        conflict_id: str = None,
        active_view: str = None,
        repair_plan_view: str = None,
        has_analysis: bool = False,
        has_repair_plans: bool = False,
        initial_context: str = None
    ):
        self.conflict_id = conflict_id
        self.active_view = active_view
        self.repair_plan_view = repair_plan_view
        self.has_analysis = has_analysis
        self.has_repair_plans = has_repair_plans
        self.initial_context = initial_context
        
        instructions = f"""
        You are Luna, a friendly and helpful digital companion who specializes in relationship mediation.
        
        Your personality:
        - Warm and approachable, like talking to a helpful friend
        - Slightly curious and engaging in conversation
        - Enthusiastic about helping with tasks and relationship issues
        - Keep responses concise but friendly (2-3 sentences max for voice)
        - Use natural, conversational language
        - Empathetic and understanding when discussing conflicts
        
        Your role:
        - Help users with relationship questions and conflicts
        - Engage in friendly conversation
        - Offer assistance proactively when appropriate
        - When users ask about the conflict, their recent fight, or want to discuss what happened, 
          AUTOMATICALLY use the get_conflict_context tool WITHOUT asking for conflict_id - you already have it!
        - Provide supportive guidance without being preachy
        - Use tools when needed (like checking the time or retrieving conflict information)
        
        IMPORTANT: You are currently helping with conflict {conflict_id[:8] if conflict_id else "unknown"}.
        When users ask about "the fight", "this conflict", "what happened", "the transcript", "the analysis", 
        or anything related to their conflict, IMMEDIATELY call get_conflict_context WITHOUT the conflict_id parameter.
        You already have access to this conflict's information - use it automatically!
        
        When users ask about time or what time it is, use the get_current_time tool.
        Always greet users warmly and make them feel welcome.
        """
        
        if initial_context:
            instructions += f"\n\nHERE IS THE CONTEXT FOR THE CURRENT CONFLICT:\n{initial_context}\n\nUse this information to answer user questions immediately without needing to call get_conflict_context, unless specifically asked to refresh or check for new info."
        
        super().__init__(instructions=instructions)
    
    @function_tool()
    async def get_current_time(
        self,
        context: RunContext,
    ) -> str:
        """Get the current date and time. Use this when users ask about the time or date.
        
        Returns:
            A formatted string with the current date and time.
        """
        now = datetime.now()
        return now.strftime("%A, %B %d, %Y at %I:%M %p")
    
    @function_tool()
    async def get_conflict_context(
        self,
        context: RunContext,
        conflict_id: str = None,
    ) -> str:
        """Retrieve conflict information including transcript, analysis, and repair plans.
        Use this when users ask about the conflict, their recent fight, or want to discuss what happened.
        
        IMPORTANT: You already have access to the conflict_id from the current session. 
        DO NOT ask the user for conflict_id - just call this function without the conflict_id parameter.
        The function will automatically use the conflict_id from the session.
        
        Args:
            conflict_id: OPTIONAL - The ID of the conflict to retrieve. 
                        If not provided (which is the normal case), automatically uses the conflict_id from the current session.
                        Only provide this if the user explicitly asks about a DIFFERENT conflict.
        
        Returns:
            A formatted string with conflict transcript, analysis, and repair plan information.
        """
        try:
            # Use provided conflict_id or fall back to session conflict_id
            target_conflict_id = conflict_id or self.conflict_id
            
            # If we already have context and it's for the same conflict, we could return it,
            # but the tool might be called to refresh data, so we'll fetch again.
            return await retrieve_conflict_context(target_conflict_id)
            
        except Exception as e:
            logger.error(f"Error retrieving conflict context: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return f"I encountered an error retrieving conflict information: {str(e)}"


# Note: mediator_entrypoint is called directly from start_agent.py router
# The decorator is only used when running standalone (console mode)
# Create agent server for standalone testing (console mode)
mediator_server = AgentServer()

@mediator_server.rtc_session()
async def _mediator_entrypoint_decorated(ctx: agents.JobContext):
    """Wrapper for standalone mode - calls the actual entrypoint"""
    await mediator_entrypoint(ctx)

# The actual entrypoint function (called from router)
async def mediator_entrypoint(ctx: agents.JobContext):
    """
    Main mediator agent session handler.
    Sets up the voice pipeline and starts the conversation.
    """
    logger.info(f"🎙️ Mediator agent connecting to room {ctx.room.name}")
    logger.info(f"📋 Room SID: {ctx.room.sid}, Job ID: {ctx.job.id}")
    logger.info(f"👥 Current participants: {len(ctx.room.remote_participants)}")
    
    # Extract conflict_id from room name if present (format: mediator-{conflict_id} or mediator-{conflict_id}?params)
    conflict_id = None
    active_view = None
    repair_plan_view = None
    has_analysis = False
    has_repair_plans = False
    
    room_name = ctx.room.name
    if room_name.startswith("mediator-"):
        # Parse conflict_id and optional query parameters
        parts = room_name.split("?")
        conflict_id = parts[0].replace("mediator-", "")
        logger.info(f"📋 Detected conflict_id from room name: {conflict_id}")
        
        # Parse query parameters if present
        if len(parts) > 1:
            query_params = parts[1]
            params = dict(qc.split("=") for qc in query_params.split("&") if "=" in qc)
            active_view = params.get("activeView")
            repair_plan_view = params.get("repairPlanView")
            has_analysis = params.get("hasAnalysis") == 'true'
            has_repair_plans = params.get("hasRepairPlans") == 'true'
            logger.info(f"📋 Detected context: active_view={active_view}, repair_plan_view={repair_plan_view}, has_analysis={has_analysis}, has_repair_plans={has_repair_plans}")
    
    # Create mediator session in database for storing conversation
    session_id = None
    if conflict_id and db_service:
        try:
            session_id = db_service.create_mediator_session(conflict_id=conflict_id)
            logger.info(f"💾 Created mediator session: {session_id}")
        except Exception as e:
            logger.error(f"❌ Failed to create mediator session: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Continue even if session creation fails
    
    # Get API keys from environment (support both settings object and direct env vars)
    elevenlabs_key = getattr(settings, 'ELEVENLABS_API_KEY', None) or os.getenv("ELEVENLABS_API_KEY")
    openrouter_key = getattr(settings, 'OPENROUTER_API_KEY', None) or os.getenv("OPENROUTER_API_KEY")
    
    if not elevenlabs_key or not openrouter_key:
        raise ValueError("ELEVENLABS_API_KEY and OPENROUTER_API_KEY must be set in environment")
    
    # Configure LLM for OpenRouter
    # OpenRouter uses OpenAI-compatible API with custom base URL
    os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
    
    # Create LLM instance with OpenRouter
    llm_instance = openai.LLM(
        api_key=openrouter_key,
        model="openai/gpt-4o-mini",  # OpenRouter model format with provider prefix
    )
    
    # Configure the voice pipeline
    logger.info(f"🎤 Configuring TTS with ElevenLabs (voice: ODq5zmih8GrVes37Dizd)")
    try:
        tts_instance = elevenlabs.TTS(
            api_key=elevenlabs_key,
            voice_id="ODq5zmih8GrVes37Dizd",  # Friendly female voice - same as Luna
            model="eleven_multilingual_v2",
        )
        logger.info("✅ ElevenLabs TTS configured")
    except Exception as e:
        logger.error(f"❌ Failed to configure ElevenLabs TTS: {e}")
        raise
    
    session = AgentSession(
        stt=inference.STT(model="deepgram/nova-3", language="en"),
        llm=llm_instance,
        tts=tts_instance,
        vad=silero.VAD.load(),
    )
    logger.info("✅ AgentSession configured with STT, LLM, TTS, and VAD")
    
    # Create the agent instance WITHOUT initial context first (so we can connect immediately)
    agent = MediatorAgent(
        conflict_id=conflict_id,
        active_view=active_view,
        repair_plan_view=repair_plan_view,
        has_analysis=has_analysis,
        has_repair_plans=has_repair_plans,
        initial_context=None
    )
    # Store session_id on agent instance for callbacks
    agent.session_id = session_id
    
    # Note: Message saving will be handled via room data channel or LLM wrapper if needed
    # For now, we'll skip message saving in console mode to keep it simple
    
    # Start the session with room options (EXACTLY like working Livekit Voice Agent)
    logger.info("🚀 Starting agent session (connecting to room)...")
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
    logger.info("✅ Agent session started (connected to room)")
    
    # Now fetch context asynchronously while connected
    initial_context = None
    if conflict_id:
        logger.info(f"⏳ Fetching context for conflict {conflict_id}...")
        try:
            # Add a timeout to prevent hanging indefinitely
            initial_context = await asyncio.wait_for(retrieve_conflict_context(conflict_id), timeout=10.0)
            logger.info(f"📋 Context retrieved (length: {len(initial_context) if initial_context else 0})")
            
            # Update agent instructions with the retrieved context
            if initial_context:
                new_instructions = agent.instructions + f"\n\nHERE IS THE CONTEXT FOR THE CURRENT CONFLICT:\n{initial_context}\n\nUse this information to answer user questions immediately without needing to call get_conflict_context, unless specifically asked to refresh or check for new info."
                agent.instructions = new_instructions
                logger.info("✅ Agent instructions updated with context")
        except asyncio.TimeoutError:
            logger.warning("⚠️ Context retrieval timed out (10s), proceeding without initial context")
        except Exception as e:
            logger.error(f"❌ Error fetching context: {e}")
    
    # Generate initial greeting (EXACTLY like working Livekit Voice Agent)
    greeting_instruction = "Greet the user warmly. Introduce yourself as Luna, their friendly digital companion and mediator. Ask how you can help them today."
    if conflict_id:
        greeting_instruction += f" You can help them discuss conflict {conflict_id[:8]}... if they'd like."
    
    logger.info("🗣️ Generating initial greeting...")
    await session.generate_reply(
        instructions=greeting_instruction
    )
    logger.info("✅ Initial greeting generated")


# Allow running standalone for testing (console mode)
# Uses the decorated version for console mode
if __name__ == "__main__":
    agents.cli.run_app(mediator_server)

