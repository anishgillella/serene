"""
Message Suggestion Service

Analyzes draft messages and generates Luna's suggestions for better communication.
Optimized for speed using Gemini 2.5 Flash and in-memory caching.

ENHANCED: Now integrates full context from:
- Fight transcripts (past conflicts, patterns)
- Luna session insights (chronic needs, escalation triggers)
- Messaging patterns (sentiment trends, Gottman markers)
- Partner profiles
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

# Lazy imports to avoid circular dependencies
pattern_analysis_service = None
gottman_service = None

def _get_pattern_service():
    global pattern_analysis_service
    if pattern_analysis_service is None:
        from app.services.pattern_analysis_service import pattern_analysis_service as pas
        pattern_analysis_service = pas
    return pattern_analysis_service

def _get_gottman_service():
    global gottman_service
    if gottman_service is None:
        from app.services.gottman_analysis_service import gottman_service as gs
        gottman_service = gs
    return gottman_service


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
_pattern_cache = SimpleCache(ttl_seconds=600)  # 10 min cache for patterns (chronic needs, escalation risk)
_gottman_cache = SimpleCache(ttl_seconds=600)  # 10 min cache for Gottman relationship scores
_messaging_analytics_cache = SimpleCache(ttl_seconds=300)  # 5 min cache for messaging analytics


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

        ENHANCED: Now integrates full context from:
        - Fight transcripts (past conflicts, patterns)
        - Luna session insights (chronic needs, escalation triggers)
        - Messaging patterns (sentiment trends, Gottman markers)
        - Partner profiles

        Optimized for speed with caching and parallel fetching.
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

            # 3. Fetch ALL context in parallel (with caching)
            # This is the key enhancement - we now fetch from ALL sources
            (
                profiles,
                triggers,
                recent_messages,
                patterns,
                gottman_scores,
                messaging_analytics,
                conflicts_summary
            ) = await asyncio.gather(
                self._get_cached_profiles(relationship_id),
                self._get_cached_triggers(relationship_id),
                asyncio.to_thread(
                    db_service.get_partner_messages,
                    conversation_id=conversation_id,
                    limit=5
                ),
                self._get_cached_patterns(relationship_id),
                self._get_cached_gottman(relationship_id),
                self._get_cached_messaging_analytics(relationship_id),
                self._get_recent_conflicts_summary(relationship_id, limit=3),
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
            if isinstance(patterns, Exception):
                logger.warning(f"Pattern fetch error: {patterns}")
                patterns = {}
            if isinstance(gottman_scores, Exception):
                logger.warning(f"Gottman fetch error: {gottman_scores}")
                gottman_scores = {}
            if isinstance(messaging_analytics, Exception):
                logger.warning(f"Messaging analytics fetch error: {messaging_analytics}")
                messaging_analytics = {}
            if isinstance(conflicts_summary, Exception):
                logger.warning(f"Conflicts summary fetch error: {conflicts_summary}")
                conflicts_summary = ""

            fetch_time = time.time() - start_time
            logger.info(f"Full context fetch took {fetch_time:.2f}s")

            # 4. Enhanced LLM analysis with full context
            llm_start = time.time()
            result = await self._enhanced_llm_analysis(
                draft_message=draft_message,
                recent_messages=recent_messages,
                triggers=triggers,
                profiles=profiles,
                sender_id=sender_id,
                patterns=patterns,
                gottman_scores=gottman_scores,
                messaging_analytics=messaging_analytics,
                conflicts_summary=conflicts_summary
            )
            llm_time = time.time() - llm_start
            logger.info(f"Enhanced LLM analysis took {llm_time:.2f}s, risk={result.risk}")

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
                "historical_context": conflicts_summary if conflicts_summary else None
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

    async def _get_cached_patterns(self, relationship_id: str) -> Dict[str, Any]:
        """Get chronic needs and escalation risk with caching."""
        cache_key = f"patterns:{relationship_id}"
        cached = _pattern_cache.get(cache_key)
        if cached:
            logger.debug("Pattern cache hit")
            return cached

        try:
            pas = _get_pattern_service()

            # Fetch chronic needs and escalation risk in parallel
            chronic_needs_task = pas.track_chronic_needs(relationship_id)
            escalation_risk_task = pas.calculate_escalation_risk(relationship_id)

            chronic_needs, escalation_risk = await asyncio.gather(
                chronic_needs_task,
                escalation_risk_task,
                return_exceptions=True
            )

            patterns = {
                "chronic_needs": [],
                "escalation_risk": {"score": 0.5, "interpretation": "moderate"},
            }

            if not isinstance(chronic_needs, Exception) and chronic_needs:
                patterns["chronic_needs"] = [n.need for n in chronic_needs[:5]]

            if not isinstance(escalation_risk, Exception) and escalation_risk:
                patterns["escalation_risk"] = {
                    "score": escalation_risk.risk_score,
                    "interpretation": escalation_risk.interpretation
                }

            _pattern_cache.set(cache_key, patterns)
            return patterns

        except Exception as e:
            logger.warning(f"Error fetching patterns: {e}")
            return {"chronic_needs": [], "escalation_risk": {"score": 0.5, "interpretation": "moderate"}}

    async def _get_cached_gottman(self, relationship_id: str) -> Dict[str, Any]:
        """Get Gottman relationship scores with caching."""
        cache_key = f"gottman:{relationship_id}"
        cached = _gottman_cache.get(cache_key)
        if cached:
            logger.debug("Gottman cache hit")
            return cached

        try:
            gs = _get_gottman_service()
            scores = await gs.get_relationship_scores(relationship_id)

            if scores:
                gottman_data = {
                    "avg_criticism": scores.get("avg_criticism_score", 0),
                    "avg_contempt": scores.get("avg_contempt_score", 0),
                    "avg_defensiveness": scores.get("avg_defensiveness_score", 0),
                    "avg_stonewalling": scores.get("avg_stonewalling_score", 0),
                    "total_repairs": scores.get("total_repair_attempts", 0),
                    "repair_success_rate": scores.get("repair_success_rate", 0),
                    "most_concerning": scores.get("most_concerning_horseman"),
                }
                _gottman_cache.set(cache_key, gottman_data)
                return gottman_data

        except Exception as e:
            logger.warning(f"Error fetching Gottman scores: {e}")

        return {}

    async def _get_cached_messaging_analytics(self, relationship_id: str) -> Dict[str, Any]:
        """Get messaging analytics with caching."""
        cache_key = f"msg_analytics:{relationship_id}"
        cached = _messaging_analytics_cache.get(cache_key)
        if cached:
            logger.debug("Messaging analytics cache hit")
            return cached

        try:
            analytics = await asyncio.to_thread(
                db_service.get_messaging_analytics,
                relationship_id,
                30  # Last 30 days
            )

            if analytics:
                _messaging_analytics_cache.set(cache_key, analytics)
                return analytics

        except Exception as e:
            logger.warning(f"Error fetching messaging analytics: {e}")

        return {}

    async def _get_recent_conflicts_summary(self, relationship_id: str, limit: int = 3) -> str:
        """Get a summary of recent conflicts for context."""
        try:
            conflicts = await asyncio.to_thread(
                db_service.get_previous_conflicts,
                relationship_id,
                limit
            )

            if not conflicts:
                return ""

            summaries = []
            for c in conflicts:
                topic = c.get("metadata", {}).get("topic", "Unknown topic")
                status = "resolved" if c.get("is_resolved") else "unresolved"
                summaries.append(f"- {topic} ({status})")

            return "Recent conflicts:\n" + "\n".join(summaries)

        except Exception as e:
            logger.warning(f"Error fetching conflicts summary: {e}")
            return ""

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

    async def _enhanced_llm_analysis(
        self,
        draft_message: str,
        recent_messages: List[Dict],
        triggers: List[Dict],
        profiles: Dict,
        sender_id: str,
        patterns: Dict[str, Any],
        gottman_scores: Dict[str, Any],
        messaging_analytics: Dict[str, Any],
        conflicts_summary: str
    ) -> QuickSuggestion:
        """
        Enhanced LLM analysis with FULL context from all sources.

        Integrates:
        - Partner profiles (personality, communication style)
        - Trigger phrases (from past fights)
        - Chronic needs (recurring unmet needs)
        - Escalation risk score
        - Gottman patterns (criticism, contempt, defensiveness, stonewalling)
        - Recent messaging sentiment trends
        - Recent conflict summaries
        """

        # Build rich context
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

        # Chronic needs context
        chronic_needs = patterns.get("chronic_needs", [])
        chronic_needs_str = ", ".join(chronic_needs[:3]) if chronic_needs else "none identified"

        # Escalation risk context
        escalation_risk = patterns.get("escalation_risk", {})
        risk_score = escalation_risk.get("score", 0.5)
        risk_level = "HIGH" if risk_score > 0.7 else "MODERATE" if risk_score > 0.4 else "LOW"

        # Gottman patterns context
        gottman_context = ""
        if gottman_scores:
            concerning = gottman_scores.get("most_concerning")
            if concerning:
                gottman_context = f"Watch for {concerning} patterns. "
            if gottman_scores.get("avg_contempt", 0) > 3:
                gottman_context += "History of contemptuous communication. "
            if gottman_scores.get("avg_criticism", 0) > 3:
                gottman_context += "History of criticism. "

        # Messaging analytics context
        sentiment_context = ""
        if messaging_analytics:
            sentiment_dist = messaging_analytics.get("sentiment_distribution", {})
            positive_ratio = sentiment_dist.get("positive_ratio", 0.5)
            if positive_ratio < 0.3:
                sentiment_context = "Recent messages have been mostly negative. "
            elif positive_ratio > 0.7:
                sentiment_context = "Recent messages have been positive. "

        # Partner preferences from profile
        partner_preferences = ""
        if partner_profile:
            post_conflict = partner_profile.get("post_conflict_need", "")
            if post_conflict:
                partner_preferences += f"{partner_name} needs '{post_conflict}' after conflict. "
            apology_pref = partner_profile.get("apology_preferences", "")
            if apology_pref:
                partner_preferences += f"They appreciate: {apology_pref[:100]}. "

        # Build enhanced prompt with all context
        prompt = f"""Analyze this message someone is about to send to {partner_name}.

RECENT CHAT:
{conversation}

MESSAGE TO SEND:
"{draft_message}"

=== RELATIONSHIP CONTEXT (from fights, Luna sessions, messaging history) ===

TRIGGER PHRASES TO AVOID: {trigger_str}

CHRONIC UNMET NEEDS: {chronic_needs_str}
(These needs come up repeatedly in fights - addressing them helps)

ESCALATION RISK: {risk_level} ({risk_score:.0%})
{gottman_context}{sentiment_context}

PARTNER PREFERENCES:
{partner_preferences if partner_preferences else "No specific preferences on file"}

{conflicts_summary}

=== END CONTEXT ===

Respond with JSON:
{{"risk": "safe|risky|high_risk", "suggestion": "improved message or original if safe", "reason": "brief reason referencing context", "issue": "main issue or null"}}

Rules:
- "high_risk" = accusatory (you always/never), insults, threats, touches chronic needs harshly
- "risky" = passive-aggressive, dismissive, ignores partner's needs, might escalate given current risk level
- "safe" = constructive, uses "I" statements, addresses needs compassionately
- If risky/high_risk, rewrite to:
  * Use "I feel..." statements
  * Avoid known triggers
  * Acknowledge chronic needs where relevant
  * Match partner's communication preferences
- Keep suggestion similar length to original
- Reference the context in your reason (e.g., "avoids trigger phrase", "addresses unmet need")"""

        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=400,  # Slightly more for richer suggestions
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

    # Keep the old method as fallback
    async def _fast_llm_analysis(
        self,
        draft_message: str,
        recent_messages: List[Dict],
        triggers: List[Dict],
        profiles: Dict,
        sender_id: str
    ) -> QuickSuggestion:
        """Fast LLM analysis with simplified prompt (fallback/legacy)."""

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
