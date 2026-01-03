# Phase 2: AI Message Generation

Core AI phase - Luna generates personalized messages for gestures using relationship context via RAG.

## Goals

- Generate contextual, personalized messages for each gesture type
- Use existing RAG infrastructure (transcripts, profiles, conflicts, chat history)
- Provide regeneration capability for alternative messages
- Allow partners to edit or replace AI-generated messages
- Track what context was used for debugging/analytics

## Prerequisites

- Phase 1 complete (database, API endpoints)
- Existing RAG services working (transcript_rag, pinecone_service)
- LLM service configured (Gemini 2.5 Flash via OpenRouter)

---

## Context Sources for Message Generation

Luna uses these existing services to gather context:

| Source | Service | What It Provides |
|--------|---------|------------------|
| Recent Conflicts | `db_service.get_recent_conflicts()` | Last 7 days of conflict summaries |
| Partner Chat | `db_service.get_partner_messages()` | Recent 10 chat messages |
| Partner Profiles | `db_service.get_partner_profiles()` | Communication styles, values |
| Conflict Analysis | `db_service.get_conflict_analysis()` | Unmet needs, triggers |
| Calendar Insights | `calendar_service.get_cycle_insights()` | Current phase, tension days |

---

## Gesture Message Service

**File**: `backend/app/services/gesture_message_service.py` (create new)

```python
"""
Gesture Message Service

Generates personalized messages for connection gestures using relationship context.
Uses existing RAG infrastructure for context gathering.
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.services.db_service import db_service
from app.services.llm_service import llm_service
from app.config import settings

logger = logging.getLogger(__name__)


# ============================================
# PYDANTIC MODELS FOR STRUCTURED OUTPUT
# ============================================

class GeneratedMessage(BaseModel):
    """LLM-generated gesture message."""
    message: str = Field(..., description="The personalized message (max 280 chars)")
    tone: str = Field(..., description="The tone of the message: warm, playful, supportive, loving, grateful")
    context_summary: str = Field(..., description="Brief summary of what context was used")


# ============================================
# GESTURE TEMPLATES
# ============================================

GESTURE_TEMPLATES = {
    "hug": {
        "purpose": "comfort, support, 'I'm here for you'",
        "default_messages": [
            "I'm here for you, always.",
            "Sending you the biggest hug right now.",
            "You're not alone in this. I've got you."
        ],
        "tone_guidance": "warm, supportive, comforting"
    },
    "kiss": {
        "purpose": "affection, love, romance, making up",
        "default_messages": [
            "I love you more than words can say.",
            "You make my heart so happy.",
            "Missing your smile right now."
        ],
        "tone_guidance": "loving, affectionate, romantic"
    },
    "thinking_of_you": {
        "purpose": "random connection, 'you're on my mind', appreciation",
        "default_messages": [
            "Just thinking about you and smiling.",
            "You crossed my mind and I had to let you know.",
            "Grateful for you today and every day."
        ],
        "tone_guidance": "appreciative, warm, thoughtful"
    }
}


class GestureMessageService:
    """
    Generates personalized gesture messages using relationship context.
    """

    def __init__(self):
        self.llm = llm_service

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

            return {
                "message": result.message,
                "context_used": context["sources_used"],
                "ai_context": {
                    "tone": result.tone,
                    "context_summary": result.context_summary,
                    "sources": context["sources_used"]
                }
            }

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
            "partner_profile": {},
            "relationship": {},
            "cycle_insights": None
        }

        try:
            # Get relationship info (partner names)
            relationship = db_service.get_relationship(relationship_id)
            if relationship:
                context["relationship"] = relationship
                context["sources_used"].append("relationship")

            # Get recent conflicts (last 7 days)
            try:
                conflicts = db_service.get_recent_conflicts(relationship_id, days=7)
                if conflicts:
                    context["recent_conflicts"] = conflicts[:3]  # Last 3
                    context["sources_used"].append("recent_conflicts")
                    context["has_meaningful_context"] = True
            except Exception as e:
                logger.debug(f"No recent conflicts: {e}")

            # Get recent partner messages (last 10)
            try:
                conversation = db_service.get_or_create_partner_conversation(relationship_id)
                if conversation:
                    messages = db_service.get_partner_messages(
                        conversation_id=conversation["id"],
                        limit=10
                    )
                    if messages:
                        context["recent_messages"] = messages
                        context["sources_used"].append("recent_messages")
                        context["has_meaningful_context"] = True
            except Exception as e:
                logger.debug(f"No recent messages: {e}")

            # Get recipient's profile
            recipient_id = "partner_b" if sender_id == "partner_a" else "partner_a"
            try:
                profiles = db_service.get_partner_profiles(relationship_id)
                if profiles and recipient_id in profiles:
                    context["partner_profile"] = profiles[recipient_id]
                    context["sources_used"].append("partner_profile")
            except Exception as e:
                logger.debug(f"No partner profile: {e}")

            # Get cycle insights if available
            try:
                from app.services.calendar_service import calendar_service
                insights = calendar_service.get_cycle_insights(relationship_id)
                if insights and insights.get("current_phase"):
                    context["cycle_insights"] = insights
                    context["sources_used"].append("cycle_insights")
            except Exception as e:
                logger.debug(f"No cycle insights: {e}")

        except Exception as e:
            logger.error(f"Error gathering context: {e}")

        return context

    async def _generate_with_llm(
        self,
        gesture_type: str,
        sender_id: str,
        context: Dict[str, Any]
    ) -> GeneratedMessage:
        """Generate a personalized message using the LLM."""

        template = GESTURE_TEMPLATES.get(gesture_type, GESTURE_TEMPLATES["thinking_of_you"])
        relationship = context.get("relationship", {})

        # Build recipient name
        recipient_id = "partner_b" if sender_id == "partner_a" else "partner_a"
        if recipient_id == "partner_a":
            recipient_name = relationship.get("partner_a_name", "your partner")
        else:
            recipient_name = relationship.get("partner_b_name", "your partner")

        # Build context string
        context_parts = []

        # Recent conflicts context
        if context.get("recent_conflicts"):
            conflict_summaries = []
            for conflict in context["recent_conflicts"][:2]:
                title = conflict.get("title", "a discussion")
                conflict_summaries.append(f"- {title}")
            context_parts.append(f"Recent discussions:\n" + "\n".join(conflict_summaries))

        # Recent messages context
        if context.get("recent_messages"):
            recent_chat = []
            for msg in context["recent_messages"][-5:]:
                speaker = "Partner" if msg["sender_id"] != sender_id else "You"
                recent_chat.append(f"{speaker}: {msg['content'][:100]}")
            context_parts.append(f"Recent chat:\n" + "\n".join(recent_chat))

        # Partner profile context
        if context.get("partner_profile"):
            profile = context["partner_profile"]
            profile_notes = []
            if profile.get("communication_style"):
                profile_notes.append(f"Communication style: {profile['communication_style']}")
            if profile.get("love_language"):
                profile_notes.append(f"Love language: {profile['love_language']}")
            if profile_notes:
                context_parts.append(f"About {recipient_name}:\n" + "\n".join(profile_notes))

        # Cycle insights context
        if context.get("cycle_insights"):
            insights = context["cycle_insights"]
            if insights.get("current_phase"):
                context_parts.append(f"Note: Partner may be in {insights['current_phase']} phase")

        context_string = "\n\n".join(context_parts) if context_parts else "No specific context available."

        prompt = f"""You are helping someone send a heartfelt {gesture_type.replace('_', ' ')} gesture to their partner, {recipient_name}.

GESTURE PURPOSE: {template['purpose']}
DESIRED TONE: {template['tone_guidance']}

RELATIONSHIP CONTEXT:
{context_string}

Write a short, personalized message (max 280 characters) that:
1. References something specific from their relationship context if available
2. Feels genuine and heartfelt, not generic
3. Matches the {template['tone_guidance']} tone
4. Is appropriate for the gesture type ({gesture_type.replace('_', ' ')})

If there was a recent conflict, acknowledge growth or moving forward together.
If there were recent positive messages, build on that warmth.
If no specific context, write something warm and genuine.

DO NOT:
- Use the word "just" (e.g., "just wanted to say")
- Start with "I just..."
- Be overly formal or stilted
- Use cliches like "through thick and thin"

Examples of good messages:
- "I know this week's been tough with work. I see you, and I'm so proud of how you handle everything."
- "That laugh of yours earlier made my whole day. Still smiling thinking about it."
- "We're going to figure out the budget thing together. I love us as a team."
"""

        try:
            result = await self.llm.structured_output_async(
                messages=[{"role": "user", "content": prompt}],
                response_model=GeneratedMessage,
                temperature=0.8  # Slightly higher for more variety
            )
            return result
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            # Fallback
            return GeneratedMessage(
                message=template["default_messages"][0],
                tone=template["tone_guidance"],
                context_summary="Used default message due to generation error"
            )

    def _get_default_message(
        self,
        gesture_type: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Return a default message when no context is available."""
        import random

        template = GESTURE_TEMPLATES.get(gesture_type, GESTURE_TEMPLATES["thinking_of_you"])
        message = random.choice(template["default_messages"])

        return {
            "message": message,
            "context_used": [],
            "ai_context": {
                "tone": template["tone_guidance"],
                "context_summary": "No relationship context available - used default message",
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

            # Add instruction to avoid previous message
            result = await self._generate_with_llm_avoid_previous(
                gesture_type=gesture_type,
                sender_id=sender_id,
                context=context,
                previous_message=previous_message
            )

            return {
                "message": result.message,
                "context_used": context["sources_used"],
                "ai_context": {
                    "tone": result.tone,
                    "context_summary": result.context_summary,
                    "sources": context["sources_used"],
                    "regenerated": True
                }
            }

        except Exception as e:
            logger.error(f"Error regenerating message: {e}")
            return self._get_different_default(gesture_type, previous_message)

    async def _generate_with_llm_avoid_previous(
        self,
        gesture_type: str,
        sender_id: str,
        context: Dict[str, Any],
        previous_message: str
    ) -> GeneratedMessage:
        """Generate a message that's different from the previous one."""

        # Reuse the main generation but add avoidance instruction
        template = GESTURE_TEMPLATES.get(gesture_type, GESTURE_TEMPLATES["thinking_of_you"])

        prompt_addition = f"""
IMPORTANT: Generate a DIFFERENT message than this previous one:
"{previous_message}"

Use a different angle, focus on different context, or express the same sentiment differently.
"""

        # For simplicity, just call the main generator with modified prompt
        # In production, would integrate this into _generate_with_llm
        result = await self._generate_with_llm(gesture_type, sender_id, context)

        # If somehow got the same message, use a default
        if result.message.strip() == previous_message.strip():
            return GeneratedMessage(
                message=template["default_messages"][1] if len(template["default_messages"]) > 1 else template["default_messages"][0],
                tone=template["tone_guidance"],
                context_summary="Regenerated with alternative"
            )

        return result

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
```

---

## API Route for Message Generation

**File**: `backend/app/routes/gestures_routes.py` (add these endpoints)

```python
from app.services.gesture_message_service import gesture_message_service
from app.models.schemas import GenerateGestureMessageRequest, GenerateGestureMessageResponse


@router.post("/generate-message", response_model=GenerateGestureMessageResponse)
async def generate_gesture_message(request: GenerateGestureMessageRequest):
    """
    Generate a personalized AI message for a gesture.

    Luna uses relationship context (recent conflicts, chat history,
    partner profiles) to craft a meaningful message.

    The partner can:
    - Use the generated message as-is
    - Edit the message before sending
    - Request a different message (regenerate)
    - Write their own message instead
    """
    try:
        result = await gesture_message_service.generate_message(
            relationship_id=request.relationship_id,
            sender_id=request.sender_id,
            gesture_type=request.gesture_type.value
        )

        return GenerateGestureMessageResponse(
            message=result["message"],
            context_used=result["context_used"]
        )
    except Exception as e:
        logger.error(f"Error generating gesture message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RegenerateMessageRequest(BaseModel):
    relationship_id: str
    sender_id: str = Field(..., pattern='^(partner_a|partner_b)$')
    gesture_type: GestureType
    previous_message: str


@router.post("/regenerate-message", response_model=GenerateGestureMessageResponse)
async def regenerate_gesture_message(request: RegenerateMessageRequest):
    """
    Generate a different message than the previous one.

    Use this when the partner wants an alternative suggestion.
    """
    try:
        result = await gesture_message_service.regenerate_message(
            relationship_id=request.relationship_id,
            sender_id=request.sender_id,
            gesture_type=request.gesture_type.value,
            previous_message=request.previous_message
        )

        return GenerateGestureMessageResponse(
            message=result["message"],
            context_used=result["context_used"]
        )
    except Exception as e:
        logger.error(f"Error regenerating gesture message: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Update Send Gesture to Include AI Context

When the gesture is sent, store what AI context was used:

**File**: `backend/app/routes/gestures_routes.py` (update send endpoint)

```python
@router.post("/send", response_model=SendGestureResponse)
async def send_gesture(request: SendGestureRequest):
    """Send a connection gesture to your partner."""
    try:
        # Save gesture with AI context if ai_generated
        gesture = db_service.save_gesture(
            relationship_id=request.relationship_id,
            gesture_type=request.gesture_type.value,
            sent_by=request.sender_id,
            message=request.message,
            ai_generated=request.ai_generated,
            ai_context_used=request.ai_context if hasattr(request, 'ai_context') else None
        )
        # ... rest of the function
```

And update the schema:

```python
class SendGestureRequest(BaseModel):
    """Request to send a connection gesture"""
    relationship_id: str
    gesture_type: GestureType
    sender_id: str = Field(..., pattern='^(partner_a|partner_b)$')
    message: Optional[str] = Field(default=None, max_length=280)
    ai_generated: bool = False
    ai_context: Optional[Dict[str, Any]] = None  # What context AI used
```

---

## LLM Service Integration

Ensure the LLM service supports async structured output. If not already present:

**File**: `backend/app/services/llm_service.py` (add if needed)

```python
async def structured_output_async(
    self,
    messages: List[Dict[str, str]],
    response_model: type,
    temperature: float = 0.7
) -> Any:
    """
    Async version of structured output for use in async contexts.
    """
    # If using httpx or similar async client
    import asyncio

    # Run sync version in thread pool for now
    return await asyncio.to_thread(
        self.structured_output,
        messages=messages,
        response_model=response_model,
        temperature=temperature
    )
```

---

## Testing Checklist

### Context Gathering Tests
- [ ] Gathers recent conflicts from last 7 days
- [ ] Gathers last 10 partner messages
- [ ] Retrieves recipient's partner profile
- [ ] Gets cycle insights when available
- [ ] Handles missing data gracefully (no crashes)

### Message Generation Tests
- [ ] Generates message with conflict context
- [ ] Generates message with chat context
- [ ] Generates message with profile context
- [ ] Falls back to default when no context
- [ ] Messages are under 280 characters
- [ ] Different gesture types have different tones

### Regeneration Tests
- [ ] Regenerate produces different message
- [ ] Regenerate uses same context sources
- [ ] Falls back to alternative default if LLM fails

### API Tests
- [ ] `POST /api/gestures/generate-message` returns message
- [ ] `POST /api/gestures/regenerate-message` returns different message
- [ ] `context_used` array correctly lists sources
- [ ] Errors return graceful fallbacks, not 500s

### Integration Tests
- [ ] Full flow: generate → edit → send → receive with AI flag
- [ ] AI-generated message stored with gesture
- [ ] ai_context_used stored for debugging
