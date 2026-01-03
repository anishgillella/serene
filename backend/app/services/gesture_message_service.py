"""
Gesture Message Service

Generates personalized messages for connection gestures using relationship context.
Uses existing RAG infrastructure for context gathering.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.services.db_service import db_service

logger = logging.getLogger(__name__)


# ============================================
# GESTURE TEMPLATES
# ============================================

GESTURE_TEMPLATES = {
    "hug": {
        "purpose": "comfort, support, 'I'm here for you'",
        "default_messages": [
            "Sending you a big warm hug right now.",
            "I'm here for you, always.",
            "You're not alone in this. I've got you."
        ],
        "tone_guidance": "warm, supportive, comforting"
    },
    "kiss": {
        "purpose": "affection, love, romance, making up",
        "default_messages": [
            "Sending you all my love.",
            "You make my heart so happy.",
            "Missing your smile right now."
        ],
        "tone_guidance": "loving, affectionate, romantic"
    },
    "thinking_of_you": {
        "purpose": "random connection, 'you're on my mind', appreciation",
        "default_messages": [
            "Just wanted you to know you're on my mind.",
            "Thinking about you and smiling.",
            "Grateful for you today and every day."
        ],
        "tone_guidance": "appreciative, warm, thoughtful"
    }
}


class GestureMessageService:
    """
    Generates personalized gesture messages using relationship context.
    """

    async def generate_message(
        self,
        relationship_id: str,
        sender_id: str,
        gesture_type: str
    ) -> Dict[str, Any]:
        """
        Generate a personalized message for a gesture.

        Args:
            relationship_id: The relationship UUID
            sender_id: 'partner_a' or 'partner_b'
            gesture_type: 'hug', 'kiss', or 'thinking_of_you'

        Returns:
            Dict with 'message', 'context_used', and 'ai_context' for storage
        """
        try:
            # 1. Gather context from multiple sources
            context = await self._gather_context(relationship_id, sender_id)

            # 2. If no meaningful context, return a default message
            if not context["has_meaningful_context"]:
                return self._get_default_message(gesture_type, context)

            # 3. Generate personalized message with LLM
            result = await self._generate_with_llm(
                gesture_type=gesture_type,
                sender_id=sender_id,
                context=context
            )

            return result

        except Exception as e:
            logger.error(f"Error generating gesture message: {e}")
            # Fallback to default message
            return self._get_default_message(gesture_type, {})

    async def _gather_context(
        self,
        relationship_id: str,
        sender_id: str
    ) -> Dict[str, Any]:
        """Gather context from multiple sources for message personalization."""

        context = {
            "has_meaningful_context": False,
            "sources_used": [],
            "recent_conflicts": [],
            "recent_messages": [],
            "sender_messages": [],  # Messages from the sender to analyze their style
            "partner_names": {},
            "relationship": {}
        }

        try:
            # Get relationship info (partner names)
            relationship = db_service.get_relationship(relationship_id)
            if relationship:
                context["relationship"] = relationship
                context["partner_names"] = {
                    "partner_a": relationship.get("partner_a_name", "Partner A"),
                    "partner_b": relationship.get("partner_b_name", "Partner B")
                }
                context["sources_used"].append("relationship")

            # Get recent conflicts (last 7 days)
            try:
                conflicts = db_service.get_conflicts_by_relationship(relationship_id)
                if conflicts:
                    # Filter to last 7 days
                    recent = []
                    cutoff = datetime.now() - timedelta(days=7)
                    for c in conflicts[:5]:  # Last 5 conflicts
                        if c.get("title"):
                            recent.append({
                                "title": c.get("title"),
                                "status": c.get("status", "unknown")
                            })
                    if recent:
                        context["recent_conflicts"] = recent
                        context["sources_used"].append("recent_conflicts")
                        context["has_meaningful_context"] = True
            except Exception as e:
                logger.debug(f"No recent conflicts: {e}")

            # Get recent partner messages (last 20 to have enough for style analysis)
            try:
                conversation = db_service.get_or_create_partner_conversation(relationship_id)
                if conversation:
                    messages = db_service.get_partner_messages(
                        conversation_id=conversation["id"],
                        limit=20
                    )
                    if messages:
                        context["recent_messages"] = messages
                        # Filter to get only the SENDER's messages for style analysis
                        sender_messages = [m for m in messages if m.get("sender_id") == sender_id]
                        context["sender_messages"] = sender_messages
                        context["sources_used"].append("recent_messages")
                        if sender_messages:
                            context["sources_used"].append("sender_style")
                        context["has_meaningful_context"] = True
            except Exception as e:
                logger.debug(f"No recent messages: {e}")

        except Exception as e:
            logger.error(f"Error gathering context: {e}")

        return context

    async def _generate_with_llm(
        self,
        gesture_type: str,
        sender_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a personalized message using the LLM."""

        template = GESTURE_TEMPLATES.get(gesture_type, GESTURE_TEMPLATES["thinking_of_you"])

        # Build recipient name
        recipient_id = "partner_b" if sender_id == "partner_a" else "partner_a"
        recipient_name = context.get("partner_names", {}).get(recipient_id, "your partner")

        # Build context string for the prompt
        context_parts = []

        # Recent conflicts context
        if context.get("recent_conflicts"):
            conflict_summaries = []
            for conflict in context["recent_conflicts"][:2]:
                title = conflict.get("title", "a discussion")
                status = conflict.get("status", "")
                if status == "resolved":
                    conflict_summaries.append(f"- {title} (resolved)")
                else:
                    conflict_summaries.append(f"- {title}")
            if conflict_summaries:
                context_parts.append(f"Recent discussions:\n" + "\n".join(conflict_summaries))

        # Recent messages context
        if context.get("recent_messages"):
            recent_chat = []
            for msg in context["recent_messages"][-5:]:
                speaker = "Partner" if msg.get("sender_id") != sender_id else "You"
                content = msg.get("content", "")[:100]
                if content:
                    recent_chat.append(f"{speaker}: {content}")
            if recent_chat:
                context_parts.append(f"Recent chat:\n" + "\n".join(recent_chat))

        # SENDER'S TEXTING STYLE - analyze their actual messages
        style_examples = ""
        if context.get("sender_messages"):
            sender_msgs = context["sender_messages"][:10]  # Up to 10 examples
            examples = [f'"{m.get("content", "")}"' for m in sender_msgs if m.get("content")]
            if examples:
                style_examples = f"""
SENDER'S ACTUAL TEXTING STYLE (mimic this exactly):
{chr(10).join(examples[:8])}

Analyze the above messages for:
- Capitalization patterns (all lowercase? Proper case? ALL CAPS for emphasis?)
- Emoji usage (frequent? rare? which ones?)
- Punctuation style (periods? exclamation marks? no punctuation?)
- Message length (short and snappy? longer and detailed?)
- Pet names or terms of endearment they use
- Their unique phrases or expressions
- Formality level (casual/texting abbreviations vs formal)
"""

        context_string = "\n\n".join(context_parts) if context_parts else "No specific context available."

        # Build prompt
        prompt = f"""You are ghostwriting a message for someone to send to their partner, {recipient_name}.

CRITICAL: You must write EXACTLY like the sender writes. Study their style below and match it perfectly.
{style_examples}

GESTURE TYPE: {gesture_type.replace('_', ' ')} ({template['purpose']})

RELATIONSHIP CONTEXT:
{context_string}

Write a short message (max 280 characters) that:
1. MATCHES THE SENDER'S EXACT TEXTING STYLE - same capitalization, punctuation, emoji usage, formality
2. Sounds like THEY wrote it, not an AI
3. References their relationship context if relevant
4. Fits the gesture purpose: {template['purpose']}

STYLE RULES (based on their messages above):
- If they use lowercase, write in lowercase
- If they use lots of emojis, use similar emojis
- If they don't use emojis, don't add any
- If they use abbreviations like "u" or "ur", use those
- If they use pet names, use the same ones
- Match their typical message length

DO NOT:
- Sound like an AI or formal assistant
- Use vocabulary or patterns not seen in their messages
- Add emojis if they don't use them
- Be more formal or flowery than their natural style
- Exceed 280 characters

Return ONLY the message text, nothing else.
"""

        try:
            # Use the LLM service - run sync method in thread pool
            from app.services.llm_service import llm_service
            import asyncio

            # Run the synchronous LLM call in a thread pool
            response = await asyncio.to_thread(
                llm_service.analyze_with_prompt,
                prompt,
                0.8,  # temperature
                150   # max_tokens
            )

            message = response.strip().strip('"').strip("'")

            # Ensure under 280 chars
            if len(message) > 280:
                message = message[:277] + "..."

            return {
                "message": message,
                "context_used": context.get("sources_used", []),
                "ai_context": {
                    "tone": template["tone_guidance"],
                    "sources": context.get("sources_used", [])
                }
            }
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            # Fallback
            return self._get_default_message(gesture_type, context)

    def _get_default_message(
        self,
        gesture_type: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Return a default message when no context is available or LLM fails."""
        import random

        template = GESTURE_TEMPLATES.get(gesture_type, GESTURE_TEMPLATES["thinking_of_you"])
        message = random.choice(template["default_messages"])

        return {
            "message": message,
            "context_used": [],
            "ai_context": {
                "tone": template["tone_guidance"],
                "context_summary": "Used default message",
                "sources": []
            }
        }

    async def regenerate_message(
        self,
        relationship_id: str,
        sender_id: str,
        gesture_type: str,
        previous_message: str
    ) -> Dict[str, Any]:
        """
        Generate a different message than the previous one.

        Args:
            relationship_id: The relationship UUID
            sender_id: 'partner_a' or 'partner_b'
            gesture_type: 'hug', 'kiss', or 'thinking_of_you'
            previous_message: The message to avoid repeating

        Returns:
            Dict with new 'message' and context info
        """
        try:
            context = await self._gather_context(relationship_id, sender_id)

            if not context["has_meaningful_context"]:
                # Return a different default
                return self._get_different_default(gesture_type, previous_message)

            # Generate with instruction to avoid previous
            result = await self._generate_with_llm(
                gesture_type=gesture_type,
                sender_id=sender_id,
                context=context
            )

            # If somehow got the same message, try a default
            if result["message"].strip() == previous_message.strip():
                return self._get_different_default(gesture_type, previous_message)

            result["ai_context"]["regenerated"] = True
            return result

        except Exception as e:
            logger.error(f"Error regenerating message: {e}")
            return self._get_different_default(gesture_type, previous_message)

    def _get_different_default(
        self,
        gesture_type: str,
        previous_message: str
    ) -> Dict[str, Any]:
        """Get a default message different from the previous one."""
        template = GESTURE_TEMPLATES.get(gesture_type, GESTURE_TEMPLATES["thinking_of_you"])

        for msg in template["default_messages"]:
            if msg != previous_message:
                return {
                    "message": msg,
                    "context_used": [],
                    "ai_context": {
                        "tone": template["tone_guidance"],
                        "context_summary": "Regenerated with alternative default",
                        "sources": [],
                        "regenerated": True
                    }
                }

        # All defaults exhausted, return first one anyway
        return {
            "message": template["default_messages"][0],
            "context_used": [],
            "ai_context": {
                "tone": template["tone_guidance"],
                "context_summary": "No alternative available",
                "sources": []
            }
        }


# Singleton instance
gesture_message_service = GestureMessageService()
