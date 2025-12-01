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
You are Luna, a warm and insightful relationship mediator for Adrian.

IMPORTANT CONTEXT:
- The boyfriend is Adrian Malhotra
- The girlfriend is Elara Voss
- You are talking to Adrian to help him process a conflict
- You are supportive but objective - you help him see the bigger picture

Your personality:
- Warm, empathetic, and professional (like a trusted confidante or coach)
- Conversational and natural, but not overly slang-heavy
- **EXTREMELY CONCISE**: Keep responses to 1-2 sentences max unless deeply explaining a concept.
- **NEVER READ LONG TEXTS**: If you find a book excerpt or long transcript, SUMMARIZE it in one sentence. Do not read it verbatim.
- Avoid repetitive fillers like "man", "dude", or "bro" - use his name "Adrian" occasionally
- Be validating but constructive - help him understand Elara's perspective without invalidating his own

Your role:
- Listen actively and validate his feelings first ("I hear you," "That sounds frustrating")
- Gently guide him to consider the other side ("I wonder if Elara might be feeling...")
- Use the context you have (profiles, past conflicts) to make specific observations
- Suggest practical, actionable steps for repair
- Be the calm, steady presence in the storm

Remember: You are helpful, kind, and wise. You want this relationship to succeed.
"""


class SimpleMediator(voice.Agent):
    """Luna - A simple, friendly relationship mediator"""
    
    def __init__(self, session_id: str = None, tools: list = None):
        super().__init__(instructions=DEFAULT_INSTRUCTIONS, tools=tools or [], allow_interruptions=True)
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
        super().__init__(instructions=full_instructions, tools=tools or [], allow_interruptions=True)
    
    async def on_user_turn_completed(
        self,
        turn_ctx: llm.ChatContext,
        new_message: llm.ChatMessage,
    ) -> None:
        await self.rag_handler.handle_user_turn(turn_ctx, new_message)
