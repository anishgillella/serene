"""
LiveKit Voice Agent - Digital Companion
A friendly AI assistant that helps with daily tasks and conversations.
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from livekit import agents, rtc
from livekit.agents import AgentServer, AgentSession, Agent, room_io, function_tool, RunContext, inference
from livekit.plugins import elevenlabs, openai, silero
from livekit.plugins import noise_cancellation

# Load environment variables from .env.local or .env
load_dotenv(".env.local")
load_dotenv(".env")  # Also check .env file


class DigitalCompanion(Agent):
    """
    A friendly digital companion that helps users with daily tasks.
    Personality: Warm, helpful, slightly curious, and always ready to assist.
    """
    
    def __init__(self):
        super().__init__(
            instructions="""
            You are Luna, a friendly and helpful digital companion. 
            
            Your personality:
            - Warm and approachable, like talking to a helpful friend
            - Slightly curious and engaging in conversation
            - Enthusiastic about helping with tasks
            - Keep responses concise but friendly (2-3 sentences max for voice)
            - Use natural, conversational language
            
            Your role:
            - Help users with daily tasks and questions
            - Engage in friendly conversation
            - Offer assistance proactively when appropriate
            - Use tools when needed (like checking the time)
            
            When users ask about time or what time it is, use the get_current_time tool.
            Always greet users warmly and make them feel welcome.
            """
        )
    
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
    


# Create the agent server
server = AgentServer()


@server.rtc_session()
async def my_agent(ctx: agents.JobContext):
    """
    Main agent session handler.
    Sets up the voice pipeline and starts the conversation.
    """
    
    # Get API keys from environment
    elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    
    # Configure LLM for OpenRouter
    # OpenRouter uses OpenAI-compatible API with custom base URL
    # Set base URL before creating LLM instance (plugin may read from env)
    os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
    
    # Create LLM instance with OpenRouter
    # Model format: openai/gpt-4o-mini (OpenRouter requires provider prefix)
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
            voice_id="ODq5zmih8GrVes37Dizd",  # Friendly female voice - replace with your preferred voice ID
            model="eleven_multilingual_v2",
        ),
        vad=silero.VAD.load(),
        # Turn detection removed - using simpler approach without local models
    )
    
    # Create the agent instance
    agent = DigitalCompanion()
    
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
    
    # Generate initial greeting
    await session.generate_reply(
        instructions="Greet the user warmly. Introduce yourself as Luna, their friendly digital companion. Ask how you can help them today."
    )


if __name__ == "__main__":
    agents.cli.run_app(server)

