"""
Message Suggestion Service

Analyzes draft messages and generates Luna's suggestions for better communication.
Optimized for speed using Gemini 2.5 Flash and in-memory caching.
"""

import logging
import asyncio
import json
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from openai import OpenAI

from app.config import settings
from app.services.db_service import db_service
from app.services.pinecone_service import pinecone_service
from app.services.embeddings_service import embeddings_service
from app.services.profile_service import profile_service

logger = logging.getLogger(__name__)


# ============================================
# SIMPLE IN-MEMORY CACHE WITH TTL
# ============================================

class SimpleCache:
    """Simple in-memory cache with TTL for profiles."""

    def __init__(self, ttl_seconds: int = 300):  # 5 minute default
        self.cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
        self.ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            value, expiry = self.cache[key]
            if time.time() < expiry:
                return value
            else:
                del self.cache[key]
        return None

    def set(self, key: str, value: Any):
        self.cache[key] = (value, time.time() + self.ttl)

    def clear(self):
        self.cache.clear()


# Global caches
_profile_cache = SimpleCache(ttl_seconds=300)  # 5 min cache for profiles
_trigger_cache = SimpleCache(ttl_seconds=600)  # 10 min cache for triggers


# ============================================
# SIMPLIFIED PYDANTIC MODEL FOR FAST RESPONSE
# ============================================

class QuickSuggestion(BaseModel):
    """Simplified suggestion for fast LLM response."""
    risk: str = Field(..., description="safe, risky, or high_risk")
    suggestion: str = Field(..., description="The improved message, or original if safe")
    reason: str = Field(..., description="Brief reason for the suggestion")
    issue: Optional[str] = Field(None, description="Main issue detected, if any")


# ============================================
# PATTERNS FOR QUICK DETECTION
# ============================================

ACCUSATORY_PATTERNS = [
    'you always', 'you never', "you don't", "you can't",
    'your fault', 'you should', 'you make me', 'because of you',
    "you're always", "you're never", 'why do you always',
    'why can\'t you', 'what\'s wrong with you'
]

ESCALATION_WORDS = [
    'hate', 'sick of', 'done with', 'leave', 'divorce',
    'break up', "can't stand", 'over it', 'give up',
    'worst', 'stupid', 'idiot', 'pathetic'
]


class MessageSuggestionService:
    """
    Generates pre-send suggestions using Gemini 2.5 Flash for speed.
    Uses caching and simplified prompts for sub-2-second responses.
    """

    def __init__(self):
        # Use Gemini 2.5 Flash via OpenRouter for fast responses
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
            timeout=10.0,  # Shorter timeout for real-time use
        )
        self.model = "google/gemini-2.5-flash"
        self.pinecone = pinecone_service
        self.embeddings = embeddings_service
        self.namespace = "partner_messages"
        logger.info("✅ Initialized Message Suggestion Service (Gemini 2.5 Flash)")

    async def analyze_and_suggest(
        self,
        draft_message: str,
        conversation_id: str,
        sender_id: str,
        relationship_id: str,
        sensitivity: str = 'medium'
    ) -> Dict[str, Any]:
        """
        Analyze a draft message and generate suggestions if needed.
        Optimized for speed with caching and simplified LLM calls.
        """
        start_time = time.time()

        try:
            # 1. Quick risk check (no LLM call)
            quick_risk = self._quick_risk_check(draft_message, sensitivity)
            logger.info(f"Quick risk check for '{draft_message[:50]}...' with sensitivity={sensitivity}: {quick_risk}")

            # 2. If message seems safe, skip LLM
            if quick_risk == 'safe':
                logger.info("Message deemed safe, skipping LLM analysis")
                return self._create_safe_response(draft_message)

            # 3. Fetch context in parallel (with caching)
            profiles, triggers, recent_messages = await asyncio.gather(
                self._get_cached_profiles(relationship_id),
                self._get_cached_triggers(relationship_id),
                asyncio.to_thread(
                    db_service.get_partner_messages,
                    conversation_id=conversation_id,
                    limit=5  # Reduced from 10 for speed
                ),
                return_exceptions=True
            )

            # Handle any exceptions from gather
            if isinstance(profiles, Exception):
                logger.warning(f"Profile fetch error: {profiles}")
                profiles = {}
            if isinstance(triggers, Exception):
                logger.warning(f"Trigger fetch error: {triggers}")
                triggers = []
            if isinstance(recent_messages, Exception):
                logger.warning(f"Messages fetch error: {recent_messages}")
                recent_messages = []

            fetch_time = time.time() - start_time
            logger.info(f"Context fetch took {fetch_time:.2f}s")

            # 4. Fast LLM analysis with simplified prompt
            llm_start = time.time()
            result = await self._fast_llm_analysis(
                draft_message=draft_message,
                recent_messages=recent_messages,
                triggers=triggers,
                profiles=profiles,
                sender_id=sender_id
            )
            llm_time = time.time() - llm_start
            logger.info(f"LLM analysis took {llm_time:.2f}s, risk={result.risk}")

            # 5. Store suggestion (fire-and-forget, don't await)
            asyncio.create_task(asyncio.to_thread(
                self._store_suggestion,
                conversation_id=conversation_id,
                sender_id=sender_id,
                original_message=draft_message,
                result=result
            ))

            total_time = time.time() - start_time
            logger.info(f"Total suggestion time: {total_time:.2f}s")

            return {
                "suggestion_id": None,  # Will be set by background task
                "original_message": draft_message,
                "risk_assessment": result.risk,
                "detected_issues": [result.issue] if result.issue else [],
                "primary_suggestion": result.suggestion,
                "suggestion_rationale": result.reason,
                "alternatives": [],  # Simplified - no alternatives for speed
                "underlying_need": None,
                "historical_context": None
            }

        except Exception as e:
            logger.error(f"Error in analyze_and_suggest: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._create_safe_response(draft_message)

    async def _get_cached_profiles(self, relationship_id: str) -> Dict[str, Any]:
        """Get profiles with caching."""
        cache_key = f"profiles:{relationship_id}"
        cached = _profile_cache.get(cache_key)
        if cached:
            logger.debug("Profile cache hit")
            return cached

        profiles = await profile_service.get_both_partner_profiles(relationship_id)
        if profiles:
            _profile_cache.set(cache_key, profiles)
        return profiles or {}

    async def _get_cached_triggers(self, relationship_id: str) -> List[Dict]:
        """Get triggers with caching."""
        cache_key = f"triggers:{relationship_id}"
        cached = _trigger_cache.get(cache_key)
        if cached:
            logger.debug("Trigger cache hit")
            return cached

        triggers = await asyncio.to_thread(
            db_service.get_trigger_phrases_for_relationship,
            relationship_id
        )
        if triggers:
            _trigger_cache.set(cache_key, triggers)
        return triggers or []

    def _quick_risk_check(self, message: str, sensitivity: str) -> str:
        """Quick heuristic check before LLM call."""
        # High sensitivity = always use LLM
        if sensitivity == 'high':
            return 'needs_analysis'

        message_lower = message.lower()

        # Check for accusatory patterns
        for pattern in ACCUSATORY_PATTERNS:
            if pattern in message_lower:
                return 'needs_analysis'

        # Check for escalation words
        for word in ESCALATION_WORDS:
            if word in message_lower:
                return 'needs_analysis'

        # Check for excessive punctuation
        if message.count('!') >= 3 or message.count('?') >= 3:
            return 'needs_analysis'

        # Check for ALL CAPS
        alpha_chars = [c for c in message if c.isalpha()]
        if alpha_chars and len(alpha_chars) > 10:
            if sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars) > 0.5:
                return 'needs_analysis'

        # Medium sensitivity: check negative indicators
        if sensitivity == 'medium':
            negative_indicators = [
                'disappointed', 'frustrated', 'upset', 'annoyed',
                'hurt', 'angry', 'tired of', 'whatever', 'fine'
            ]
            for indicator in negative_indicators:
                if indicator in message_lower:
                    return 'needs_analysis'

        return 'safe'

    async def _fast_llm_analysis(
        self,
        draft_message: str,
        recent_messages: List[Dict],
        triggers: List[Dict],
        profiles: Dict,
        sender_id: str
    ) -> QuickSuggestion:
        """Fast LLM analysis with simplified prompt."""

        # Build minimal context
        other_partner = 'partner_b' if sender_id == 'partner_a' else 'partner_a'
        partner_profile = profiles.get(other_partner, {}) if profiles else {}
        partner_name = partner_profile.get('name', 'your partner') if partner_profile else 'your partner'

        # Recent conversation (last 3 messages only)
        conv_lines = []
        for msg in (recent_messages or [])[-3:]:
            sender = "You" if msg.get("sender_id") == sender_id else partner_name
            conv_lines.append(f"{sender}: {msg.get('content', '')[:100]}")
        conversation = "\n".join(conv_lines) if conv_lines else "(new conversation)"

        # Trigger phrases (max 5)
        trigger_list = []
        for t in (triggers or [])[:5]:
            phrase = t.get('phrase', t.get('trigger_phrase', ''))
            if phrase:
                trigger_list.append(phrase)
        trigger_str = ", ".join(trigger_list) if trigger_list else "none known"

        # Simplified prompt
        prompt = f"""Analyze this message someone is about to send to {partner_name}.

RECENT CHAT:
{conversation}

MESSAGE TO SEND:
"{draft_message}"

TRIGGER PHRASES TO AVOID: {trigger_str}

Respond with JSON:
{{"risk": "safe|risky|high_risk", "suggestion": "improved message or original if safe", "reason": "brief reason", "issue": "main issue or null"}}

Rules:
- "high_risk" = accusatory (you always/never), insults, threats
- "risky" = passive-aggressive, dismissive, might escalate
- "safe" = constructive, uses "I" statements
- If risky/high_risk, rewrite using "I feel..." statements
- Keep suggestion similar length to original"""

        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300,
            )

            content = response.choices[0].message.content.strip()

            # Parse JSON response
            # Handle markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            data = json.loads(content)

            return QuickSuggestion(
                risk=data.get("risk", "safe"),
                suggestion=data.get("suggestion", draft_message),
                reason=data.get("reason", ""),
                issue=data.get("issue")
            )

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            # Try to extract from non-JSON response
            return QuickSuggestion(
                risk="safe",
                suggestion=draft_message,
                reason="Unable to analyze",
                issue=None
            )
        except Exception as e:
            logger.error(f"LLM analysis error: {e}")
            return QuickSuggestion(
                risk="safe",
                suggestion=draft_message,
                reason="Analysis error",
                issue=None
            )

    def _create_safe_response(self, original_message: str) -> Dict[str, Any]:
        """Create a 'safe' response when no suggestion is needed."""
        return {
            "suggestion_id": None,
            "original_message": original_message,
            "risk_assessment": "safe",
            "detected_issues": [],
            "primary_suggestion": original_message,
            "suggestion_rationale": "Your message looks good!",
            "alternatives": [],
            "underlying_need": None,
            "historical_context": None
        }

    def _store_suggestion(
        self,
        conversation_id: str,
        sender_id: str,
        original_message: str,
        result: QuickSuggestion
    ) -> Optional[str]:
        """Store suggestion in database."""
        try:
            return db_service.save_message_suggestion(
                conversation_id=conversation_id,
                sender_id=sender_id,
                original_message=original_message,
                risk_assessment=result.risk,
                detected_issues=[result.issue] if result.issue else [],
                primary_suggestion=result.suggestion,
                suggestion_rationale=result.reason,
                alternatives=[],
                underlying_need=None,
                context_message_count=0
            )
        except Exception as e:
            logger.error(f"Error storing suggestion: {e}")
            return None

    def record_suggestion_response(
        self,
        suggestion_id: str,
        action: str,
        final_message_id: str = None,
        selected_index: int = None
    ) -> bool:
        """Record how the user responded to a suggestion."""
        try:
            return db_service.update_message_suggestion_response(
                suggestion_id=suggestion_id,
                user_action=action,
                final_message_id=final_message_id,
                selected_alternative_index=selected_index
            )
        except Exception as e:
            logger.error(f"Error recording suggestion response: {e}")
            return False

    async def embed_and_store_message(
        self,
        message_id: str,
        conversation_id: str,
        relationship_id: str,
        sender_id: str,
        content: str,
        sent_at: str,
        sentiment: str = None,
        had_conflict: bool = False,
        trigger_phrases: List[str] = None
    ) -> bool:
        """Embed a message and store in Pinecone for RAG."""
        try:
            if not self.pinecone.index:
                return False

            embedding = await asyncio.to_thread(
                self.embeddings.embed_text,
                content
            )

            metadata = {
                "message_id": message_id,
                "conversation_id": conversation_id,
                "relationship_id": relationship_id,
                "sender_id": sender_id,
                "sent_at": sent_at,
                "sentiment": sentiment or "unknown",
                "had_conflict": had_conflict,
                "trigger_phrases": trigger_phrases or [],
                "text": content[:1000]
            }

            await asyncio.to_thread(
                self.pinecone.index.upsert,
                vectors=[{
                    "id": f"msg_{message_id}",
                    "values": embedding,
                    "metadata": metadata
                }],
                namespace=self.namespace
            )

            return True
        except Exception as e:
            logger.error(f"Error embedding message: {e}")
            return False


# Singleton instance
message_suggestion_service = MessageSuggestionService()
