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
    """Luna - Mediator agent with RAG capabilities and pattern awareness (Phase 3)"""

    def __init__(
        self,
        rag_system,
        conflict_id: str = None,
        relationship_id: str = None,
        session_id: str = None,
        instructions: str = "",
        tools: list = None,
        partner_a_name: str = "Partner A",
        partner_b_name: str = "Partner B",
        mediation_context: dict = None
    ):
        self.rag_handler = RAGHandler(rag_system, conflict_id, relationship_id, session_id)
        self.partner_a_name = partner_a_name
        self.partner_b_name = partner_b_name
        self.conflict_id = conflict_id
        self.relationship_id = relationship_id
        self.mediation_context = mediation_context or {}

        # Generate dynamic base instructions
        base_instructions = instructions or get_dynamic_instructions(partner_a_name, partner_b_name)

        # Build context-aware instructions with pattern analysis (Phase 3)
        full_instructions = base_instructions + self._build_context_instructions(
            partner_a_name, partner_b_name
        )

        super().__init__(instructions=full_instructions, tools=tools or [])

    def _build_context_instructions(self, partner_a_name: str, partner_b_name: str) -> str:
        """Build context-aware instructions using mediation context (Phase 3)"""
        context_section = f"""

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

        # Add relationship pattern awareness if context available (Phase 3)
        if self.mediation_context:
            context_section += self._build_pattern_awareness_section()

        return context_section

    def _build_pattern_awareness_section(self) -> str:
        """Build pattern-aware section from mediation context (Phase 3)"""
        section = "\n## RELATIONSHIP PATTERNS (Critical Context for This Mediation):\n"

        # Escalation risk awareness
        escalation = self.mediation_context.get("escalation_risk", {})
        if escalation:
            risk_score = escalation.get("score", 0)
            interpretation = escalation.get("interpretation", "unknown")
            section += f"- Escalation Risk: {interpretation.upper()} ({risk_score*100:.0f}%)\n"
            if escalation.get("is_critical"):
                section += "  ⚠️ THIS RELATIONSHIP IS AT CRITICAL ESCALATION RISK - Use extra care\n"

        # Chronic unmet needs awareness
        chronic_needs = self.mediation_context.get("chronic_needs", [])
        if chronic_needs:
            section += f"- Chronic Unmet Needs: {', '.join(chronic_needs)}\n"
            section += "  These are recurring pain points - address them sensitively\n"

        # High-impact triggers
        triggers = self.mediation_context.get("high_impact_triggers", [])
        if triggers:
            section += "- Known Escalation Triggers:\n"
            for trigger in triggers[:3]:
                phrase = trigger.get("phrase", "")
                escalation_rate = trigger.get("escalation_rate", 0)
                section += f"  • \"{phrase}\" (escalates {escalation_rate*100:.0f}% of the time)\n"
            section += "  Avoid these phrases or help them understand the impact\n"

        # Unresolved issues
        unresolved = self.mediation_context.get("unresolved_issues", [])
        if unresolved:
            section += f"- {len(unresolved)} Unresolved Issues Still Pending:\n"
            for issue in unresolved[:3]:
                topic = issue.get("topic", "Unknown")
                days = issue.get("days_unresolved", 0)
                section += f"  • {topic} (unresolved for {days}+ days)\n"
            section += "  Consider whether this current conflict is connected to these\n"

        section += "\nUse this context to:\n"
        section += "1. Recognize and name the patterns they're stuck in\n"
        section += "2. Help them see how current conflict repeats past issues\n"
        section += "3. Suggest breaks if escalation risk is critical\n"
        section += "4. Focus on the chronic needs causing the conflict\n\n"

        return section

    async def on_user_turn_completed(
        self,
        turn_ctx: llm.ChatContext,
        new_message: llm.ChatMessage,
    ) -> None:
        await self.rag_handler.handle_user_turn(turn_ctx, new_message)

    @staticmethod
    async def create_with_context(
        rag_system,
        conflict_id: str,
        relationship_id: str,
        session_id: str = None,
        instructions: str = "",
        tools: list = None,
        partner_a_name: str = "Partner A",
        partner_b_name: str = "Partner B"
    ):
        """Factory method to create RAGMediator with enriched context (Phase 3)"""
        from app.routes.mediator_context import get_mediation_context as fetch_context

        try:
            # Fetch mediation context from analytics
            context_data = await fetch_context(conflict_id)

            return RAGMediator(
                rag_system=rag_system,
                conflict_id=conflict_id,
                relationship_id=relationship_id,
                session_id=session_id,
                instructions=instructions,
                tools=tools,
                partner_a_name=partner_a_name,
                partner_b_name=partner_b_name,
                mediation_context=context_data
            )
        except Exception as e:
            logger.warning(f"Could not fetch mediation context: {str(e)}. Creating agent without context.")
            return RAGMediator(
                rag_system=rag_system,
                conflict_id=conflict_id,
                relationship_id=relationship_id,
                session_id=session_id,
                instructions=instructions,
                tools=tools,
                partner_a_name=partner_a_name,
                partner_b_name=partner_b_name
            )
