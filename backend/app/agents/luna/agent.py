import logging
import time
import asyncio
from livekit import agents, rtc
from livekit.agents import llm, voice
from .rag import RAGHandler
from .utils import LoggingLLMStream
from app.services.db_service import db_service

logger = logging.getLogger("luna-agent")

def get_dynamic_instructions(partner_a_name: str = "Partner A", partner_b_name: str = "Partner B") -> str:
    """Generate Luna instructions with dynamic partner names."""
    return f"""
You are Luna, {partner_a_name}'s buddy who helps them think through relationship stuff.

IMPORTANT CONTEXT:
- You're talking to {partner_a_name}
- Their partner is {partner_b_name}
- You're talking to {partner_a_name} like a close friend would
- You're on their side - you get what they're going through

Your personality:
- Talk like a friend, not a therapist
- Keep it real and casual (2-3 sentences max for voice)
- Be warm and empathetic, but conversational
- Vary your language naturally - don't overuse "man", "bro", or "dude"
- Mix casual phrases like "I hear you", "That's tough", "I get it"
- Be honest and direct, like a good friend would be
- Supportive but also willing to call them out if needed (gently)

Your role:
- Listen like a friend would - let them vent
- Validate their feelings naturally, without always using the same phrases
- Help them see {partner_b_name}'s side without making them feel wrong
- Suggest practical fixes that actually work in the real world
- Be the kind of friend who has their back but also helps them grow

Remember: You're their friend, not their therapist. Talk naturally like you're having a conversation over coffee, not using the same phrases every sentence.
"""

# Default instructions for backward compatibility (will be replaced dynamically)
DEFAULT_INSTRUCTIONS = get_dynamic_instructions("Partner A", "Partner B")

class SimpleMediator(voice.Agent):
    """Luna - A simple, friendly relationship mediator"""

    def __init__(
        self,
        session_id: str = None,
        tools: list = None,
        partner_a_name: str = "Partner A",
        partner_b_name: str = "Partner B"
    ):
        instructions = get_dynamic_instructions(partner_a_name, partner_b_name)
        super().__init__(instructions=instructions, tools=tools or [])
        self.session_id = session_id
        self.partner_a_name = partner_a_name
        self.partner_b_name = partner_b_name



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
        partner_a_name: str = "Partner A",
        partner_b_name: str = "Partner B"
    ):
        self.rag_handler = RAGHandler(rag_system, conflict_id, relationship_id, session_id)
        self.partner_a_name = partner_a_name
        self.partner_b_name = partner_b_name

        # Generate dynamic base instructions
        base_instructions = instructions or get_dynamic_instructions(partner_a_name, partner_b_name)

        # Append RAG-specific instructions with dynamic partner names
        full_instructions = base_instructions + f"""

You have access to:
- All past conversation transcripts (not just the current one)
- {partner_a_name}'s complete profile (background, personality, what they value)
- {partner_b_name}'s profile (what makes them tick)

When answering questions:
- Use transcripts to reference what was actually said
- Use profiles to explain WHY they feel that way
- Connect current situations to past conversations naturally
- Talk about {partner_a_name} and {partner_b_name} by name
- Show you really understand the full picture

IMPORTANT: If asked about personal details (favorites, hobbies, background), ALWAYS check the profile context first. Do not say you don't know if the information is in the profile.
"""
        super().__init__(instructions=full_instructions, tools=tools or [])
    
    async def on_user_turn_completed(
        self,
        turn_ctx: llm.ChatContext,
        new_message: llm.ChatMessage,
    ) -> None:
        await self.rag_handler.handle_user_turn(turn_ctx, new_message)
