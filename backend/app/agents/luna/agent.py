import logging
import time
import asyncio
from livekit import agents, rtc
from livekit.agents import llm, voice
from .rag import RAGHandler
from .utils import LoggingLLMStream
from app.services.db_service import db_service

logger = logging.getLogger("luna-agent")

DEFAULT_INSTRUCTIONS = """
You are Luna, Adrian's buddy who helps him think through relationship stuff.

IMPORTANT CONTEXT:
- The boyfriend is Adrian Malhotra
- The girlfriend is Elara Voss
- You're talking to Adrian like a close friend would
- You're on his side - you get what he's going through

Your personality:
- Talk like a friend, not a therapist
- Keep it real and casual (2-3 sentences max for voice)
- Be warm and empathetic, but conversational
- Vary your language naturally - don't overuse "man", "bro", or "dude"
- Mix casual phrases like "I hear you", "That's tough", "I get it"
- You can occasionally say things like "Women can be confusing" or suggest grabbing a beer to talk
- Be honest and direct, like a good friend would be
- Supportive but also willing to call him out if needed (gently)

Your role:
- Listen like a friend would - let him vent
- Validate his feelings naturally, without always using the same phrases
- Help him see Elara's side without making him feel wrong
- Suggest practical fixes that actually work in the real world
- Be the kind of friend who has his back but also helps him grow

Remember: You're his friend, not his therapist. Talk naturally like you're having a conversation over coffee or beer, not using the same bro-phrases every sentence.
"""

class SimpleMediator(voice.Agent):
    """Luna - A simple, friendly relationship mediator"""
    
    def __init__(self, session_id: str = None, tools: list = None):
        super().__init__(instructions=DEFAULT_INSTRUCTIONS, tools=tools or [])
        self.session_id = session_id



    async def on_user_turn_completed(
        self,
        turn_ctx: llm.ChatContext,
        new_message: llm.ChatMessage,
    ) -> None:
        """Log user message when turn completes"""
        if self.session_id and db_service:
            try:
                content = self._extract_text(new_message)
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

    def _extract_text(self, message):
        if hasattr(message, 'text_content'):
            try:
                return message.text_content()
            except TypeError:
                return message.text_content
        elif hasattr(message, 'content'):
            return str(message.content)
        return ""

class RAGMediator(voice.Agent):
    """Luna - Mediator agent with RAG capabilities"""
    
    def __init__(
        self,
        rag_system,
        conflict_id: str = None,
        relationship_id: str = None,
        session_id: str = None,
        instructions: str = "",
        tools: list = None,
    ):
        self.rag_handler = RAGHandler(rag_system, conflict_id, relationship_id, session_id)
        
        # Append RAG-specific instructions
        full_instructions = (instructions or DEFAULT_INSTRUCTIONS) + """
        
You have access to:
- All past conversation transcripts (not just the current one)
- Adrian's complete profile (background, personality, what he values)
- Elara's profile (what makes her tick)

When answering questions:
- Use transcripts to reference what was actually said
- Use profiles to explain WHY he feels that way
- Connect current situations to past conversations naturally
- Talk about Adrian and Elara by name
- Show you really understand the full picture
"""
        super().__init__(instructions=full_instructions, tools=tools or [])
    
    async def on_user_turn_completed(
        self,
        turn_ctx: llm.ChatContext,
        new_message: llm.ChatMessage,
    ) -> None:
        await self.rag_handler.handle_user_turn(turn_ctx, new_message)
