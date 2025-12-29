"""
Demo Partner Service - LLM-powered simulated partner for testing

Uses Gemini 2.5 Flash via OpenRouter to simulate partner_b responses
based on their onboarding profile and chat history.
"""
import logging
import asyncio
from typing import Optional, Dict, List, Any
from openai import OpenAI
from app.config import settings
from app.services.profile_service import profile_service
from app.services.db_service import db_service

logger = logging.getLogger(__name__)


class DemoPartnerService:
    """
    Service for generating LLM-powered partner responses in demo mode.

    When demo_mode is enabled, partner_b is simulated by an LLM that:
    - Uses the partner_b onboarding profile for personality/context
    - Remembers the full chat history
    - Responds realistically (not always agreeable)
    """

    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
            timeout=30.0,
        )
        # Use Gemini 2.5 Flash for fast, cost-effective responses
        self.model = "google/gemini-2.5-flash"
        logger.info("✅ Initialized Demo Partner Service (Gemini 2.5 Flash via OpenRouter)")

    async def generate_partner_response(
        self,
        relationship_id: str,
        conversation_id: str,
        user_message: str,
        chat_history: List[Dict[str, Any]],
        partner_a_name: str = "Partner A",
        partner_b_name: str = "Partner B",
        partner_b_profile: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Generate a response as partner_b based on their profile and chat context.

        Args:
            relationship_id: The relationship UUID
            conversation_id: The conversation UUID
            user_message: The message from partner_a
            chat_history: List of previous messages in the conversation
            partner_a_name: Name of partner_a (the user)
            partner_b_name: Name of partner_b (the simulated partner)
            partner_b_profile: Pre-fetched partner_b profile (optional, avoids duplicate fetch)

        Returns:
            Generated response text, or None if generation fails
        """
        try:
            # Use pre-fetched profile or fetch if not provided
            partner_profile = partner_b_profile
            if partner_profile is None:
                partner_profile = await profile_service.get_full_partner_profile(
                    relationship_id, "partner_b"
                )

            # Build the system prompt with partner_b's personality
            system_prompt = self._build_system_prompt(
                partner_profile,
                partner_a_name,
                partner_b_name
            )

            # Build conversation history for context
            messages = [{"role": "system", "content": system_prompt}]

            # Add chat history (last 20 messages for context)
            for msg in chat_history[-20:]:
                role = "assistant" if msg.get("sender_id") == "partner_b" else "user"
                messages.append({
                    "role": role,
                    "content": msg.get("content", "")
                })

            # Add the current message
            messages.append({"role": "user", "content": user_message})

            # Generate response
            response = await asyncio.to_thread(
                self._call_llm,
                messages
            )

            logger.info(f"✅ Generated demo partner response for conversation {conversation_id}")
            return response

        except Exception as e:
            logger.error(f"❌ Error generating demo partner response: {e}")
            return None

    def _build_system_prompt(
        self,
        profile: Optional[Dict[str, str]],
        partner_a_name: str,
        partner_b_name: str
    ) -> str:
        """Build the system prompt with partner_b's personality from their profile."""

        base_prompt = f"""You are {partner_b_name}, a real person in a relationship with {partner_a_name}.
You are having a text conversation with your partner.

CRITICAL RULES:
1. You ARE {partner_b_name}. Respond as yourself, not as an AI.
2. Keep responses SHORT and natural (1-3 sentences typically, like real texting).
3. Be AUTHENTIC - you can disagree, be frustrated, need space, or be loving depending on context.
4. Don't always agree. Real partners have different perspectives.
5. React based on your personality and emotional state.
6. Never break character or mention being an AI.
7. Use casual texting style - lowercase is fine, short sentences, occasional emoji if it fits your personality.

"""

        if profile:
            # Add personality context from profile
            personality_context = f"""
YOUR PERSONALITY & BACKGROUND:
- Name: {profile.get('name', partner_b_name)}
"""

            if profile.get('personality'):
                personality_context += f"""
- Communication style & personality: {profile.get('personality')}
"""

            if profile.get('background'):
                personality_context += f"""
- Background: {profile.get('background')}
"""

            if profile.get('partner_view'):
                personality_context += f"""
- How you see your partner: {profile.get('partner_view')}
"""

            if profile.get('repair_preferences'):
                personality_context += f"""
- How you handle conflicts: {profile.get('repair_preferences')}
"""

            if profile.get('reconnection'):
                personality_context += f"""
- What helps you reconnect: {profile.get('reconnection')}
"""

            base_prompt += personality_context
        else:
            # No profile available - use generic personality
            base_prompt += f"""
YOUR PERSONALITY:
- You're a thoughtful but sometimes busy person
- You care about your relationship but also have your own needs
- You can be direct when something bothers you
- You appreciate when your partner makes effort but notice when they don't
"""

        base_prompt += f"""

Remember: You're texting with {partner_a_name}. Be real, be yourself, keep it brief like actual text messages.
"""

        return base_prompt

    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """Make the actual LLM API call (synchronous, called via asyncio.to_thread)."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.8,  # Slightly higher for more varied responses
                max_tokens=150,   # Keep responses short like real texts
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"❌ LLM API call failed: {e}")
            raise


# Global singleton instance
try:
    demo_partner_service = DemoPartnerService()
except Exception as e:
    logger.error(f"❌ Failed to initialize DemoPartnerService: {e}")
    demo_partner_service = None
