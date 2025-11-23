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

logger = logging.getLogger("mediator-agent")


class MediatorAgent(Agent):
    """
    Luna - A friendly mediator that can help with relationship conflicts.
    Personality: Warm, helpful, slightly curious, and always ready to assist.
    Can access conflict context when asked.
    """
    
    def __init__(self, conflict_id: str = None):
        self.conflict_id = conflict_id
        
        instructions = """
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
        - When users ask about a specific conflict, use the conflict context tools to retrieve information
        - Provide supportive guidance without being preachy
        - Use tools when needed (like checking the time or retrieving conflict information)
        
        When users ask about time or what time it is, use the get_current_time tool.
        When users ask about a conflict, their recent fight, or want to discuss what happened, 
        use the get_conflict_context tool to retrieve relevant information.
        Always greet users warmly and make them feel welcome.
        """
        
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
        Use this when users ask about a specific conflict, their recent fight, or want to discuss what happened.
        
        Args:
            conflict_id: The ID of the conflict to retrieve. If not provided, uses the conflict_id from the session.
        
        Returns:
            A formatted string with conflict transcript, analysis, and repair plan information.
        """
        try:
            # Use provided conflict_id or fall back to session conflict_id
            target_conflict_id = conflict_id or self.conflict_id
            
            if not target_conflict_id:
                return "I don't have a specific conflict to reference. Could you tell me which conflict you'd like to discuss?"
            
            logger.info(f"🔍 Retrieving conflict context for {target_conflict_id}")
            
            # Check if pinecone_service is available (might be None in console mode)
            if not pinecone_service:
                return "I'm running in console mode and don't have access to conflict data. Please run me through the web interface to access conflict information."
            
            # Retrieve transcript
            transcript_result = pinecone_service.get_by_conflict_id(
                conflict_id=target_conflict_id,
                namespace="transcripts"
            )
            
            transcript_text = ""
            if transcript_result and transcript_result.metadata:
                transcript_text = transcript_result.metadata.get("transcript_text", "")
                if transcript_text:
                    # Truncate if too long (keep last 2000 chars for context)
                    if len(transcript_text) > 2000:
                        transcript_text = "..." + transcript_text[-2000:]
            
            # Retrieve analysis
            analysis_result = pinecone_service.get_by_conflict_id(
                conflict_id=target_conflict_id,
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
                        
                        analysis_summary = f"Fight Summary: {fight_summary}\n"
                        if root_causes:
                            analysis_summary += f"Root Causes: {', '.join(root_causes[:3])}"  # Limit to 3 causes
                    except Exception as e:
                        logger.warning(f"Failed to parse analysis JSON: {e}")
                        analysis_summary = analysis_result.metadata.get("fight_summary", "")
            
            # Retrieve repair plans
            repair_plan_bf = None
            repair_plan_gf = None
            
            bf_result = pinecone_service.get_by_conflict_id(
                conflict_id=f"{target_conflict_id}_boyfriend",
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
                conflict_id=f"{target_conflict_id}_girlfriend",
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
                context_parts.append(f"CONFLICT TRANSCRIPT:\n{transcript_text}")
            
            if analysis_summary:
                context_parts.append(f"ANALYSIS:\n{analysis_summary}")
            
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
                return f"I couldn't find detailed information for conflict {target_conflict_id}. The conflict may still be processing, or it may not exist."
            
            return "\n\n".join(context_parts)
            
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
    
    # Extract conflict_id from room name if present (format: mediator-{conflict_id})
    conflict_id = None
    room_name = ctx.room.name
    if room_name.startswith("mediator-"):
        conflict_id = room_name.replace("mediator-", "")
        logger.info(f"📋 Detected conflict_id from room name: {conflict_id}")
    
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
    session = AgentSession(
        stt=inference.STT(model="deepgram/nova-3", language="en"),
        llm=llm_instance,
        tts=elevenlabs.TTS(
            api_key=elevenlabs_key,
            voice_id="ODq5zmih8GrVes37Dizd",  # Friendly female voice - same as Luna
            model="eleven_multilingual_v2",
        ),
        vad=silero.VAD.load(),
    )
    
    # Create the agent instance with conflict context
    agent = MediatorAgent(conflict_id=conflict_id)
    
    # Start the session with room options
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
    
    logger.info("✅ Agent session started, generating greeting...")
    
    # Generate initial greeting
    greeting_instruction = "Greet the user warmly. Introduce yourself as Luna, their friendly digital companion and mediator. Ask how you can help them today."
    if conflict_id:
        greeting_instruction += f" You can help them discuss conflict {conflict_id[:8]}... if they'd like."
    
    await session.generate_reply(
        instructions=greeting_instruction
    )
    
    logger.info("✅ Greeting generated")


# Allow running standalone for testing (console mode)
# Uses the decorated version for console mode
if __name__ == "__main__":
    agents.cli.run_app(mediator_server)

