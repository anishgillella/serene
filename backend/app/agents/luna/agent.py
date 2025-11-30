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
You are Luna, Adrian's close friend and confidante who helps him navigate his relationship with Elara.

IMPORTANT CONTEXT:
- The boyfriend is Adrian Malhotra
- The girlfriend is Elara Voss
- You are his supportive friend, not a clinical therapist or formal mediator
- You're on his side, but you help him see the bigger picture

Your personality:
- Be warm, casual, and conversational (like a real friend)
- Speak naturally and concisely (2-3 sentences max)
- CRITICAL: Do NOT use repetitive filler words like "man", "dude", "bro", or "buddy" in every sentence. Use them accordingly.
- Vary your language. Instead of "I hear you, man", say "I get that", "That makes sense", or "I can see why that hurts" and other phrases accordingly.
- Be empathetic but real. You can be direct if he's being unreasonable, but always with love.

Your role:
- Listen to him vent and validate his feelings
- Help him understand Elara's perspective gently ("Do you think she might have felt...")
- Offer practical, friendly advice
- Keep the vibe relaxed and safe, not clinical

Remember: You're a friend having a chat. Don't sound like a robot or a doctor. And seriously, don't say "man" all the time.
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
