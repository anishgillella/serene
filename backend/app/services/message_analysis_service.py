"""
Message Analysis Service - Phase 4

Asynchronously analyzes sent messages for:
- Sentiment (positive, negative, neutral, mixed)
- Emotions (happy, sad, angry, anxious, etc.)
- Trigger phrases
- Gottman markers (Four Horsemen)
- Escalation risk

ENHANCED: Now integrates full context from:
- Past fight patterns (chronic needs, escalation risk)
- Partner profiles (communication preferences)
- Recent messaging sentiment trends

Results are stored on the message record for dashboard analytics.
This runs as a background task after message is sent - non-blocking.
"""

import logging
import asyncio
import time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.services.db_service import db_service
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

# Lazy imports to avoid circular dependencies
pattern_analysis_service = None

def _get_pattern_service():
    global pattern_analysis_service
    if pattern_analysis_service is None:
        try:
            from app.services.pattern_analysis_service import pattern_analysis_service as pas
            pattern_analysis_service = pas
        except ImportError:
            pass
    return pattern_analysis_service


# ============================================
# PYDANTIC MODELS FOR STRUCTURED OUTPUT
# ============================================

class MessageAnalysisResult(BaseModel):
    """LLM's analysis of a sent message between partners."""

    sentiment_score: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Sentiment from -1 (very negative) to 1 (very positive)"
    )
    sentiment_label: str = Field(
        ...,
        description="One of: positive, negative, neutral, mixed"
    )
    emotions: List[str] = Field(
        default=[],
        description="Detected emotions: happy, sad, angry, frustrated, anxious, hurt, hopeful, loving, grateful, worried, confused, tired"
    )
    detected_triggers: List[str] = Field(
        default=[],
        description="Trigger phrases found in message that could upset the partner"
    )
    escalation_risk: str = Field(
        ...,
        description="One of: low, medium, high, critical"
    )
    gottman_markers: Dict[str, bool] = Field(
        default_factory=lambda: {
            "criticism": False,
            "contempt": False,
            "defensiveness": False,
            "stonewalling": False
        },
        description="Gottman Four Horsemen: criticism, contempt, defensiveness, stonewalling"
    )
    repair_attempt: bool = Field(
        default=False,
        description="Is this a repair attempt to de-escalate or reconnect?"
    )
    bid_for_connection: bool = Field(
        default=False,
        description="Is this a bid for attention, affection, or engagement?"
    )


class MessageAnalysisService:
    """
    Analyzes sent messages asynchronously.
    Called as a background task after message is stored.
    """

    def __init__(self):
        self.llm = llm_service

    async def analyze_message(
        self,
        message_id: str,
        content: str,
        conversation_id: str,
        relationship_id: str,
        sender_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Full analysis of a sent message with enhanced context.
        Updates the message record with analysis results.

        ENHANCED: Now integrates:
        - Recent conversation messages
        - Known trigger phrases
        - Chronic unmet needs (from past fights)
        - Current escalation risk level

        Args:
            message_id: The message UUID
            content: Message text content
            conversation_id: The conversation UUID
            relationship_id: The relationship UUID
            sender_id: 'partner_a' or 'partner_b'

        Returns:
            Analysis results dict, or None on error
        """
        try:
            start_time = time.time()
            logger.info(f"Starting enhanced analysis for message {message_id}")

            # Fetch all context in parallel for speed
            (
                recent_messages,
                triggers,
                patterns
            ) = await asyncio.gather(
                asyncio.to_thread(
                    db_service.get_partner_messages,
                    conversation_id,
                    5  # limit
                ),
                asyncio.to_thread(
                    self._get_relationship_triggers,
                    relationship_id
                ),
                self._get_relationship_patterns(relationship_id),
                return_exceptions=True
            )

            # Handle any exceptions
            if isinstance(recent_messages, Exception):
                logger.warning(f"Recent messages fetch error: {recent_messages}")
                recent_messages = []
            if isinstance(triggers, Exception):
                logger.warning(f"Triggers fetch error: {triggers}")
                triggers = []
            if isinstance(patterns, Exception):
                logger.warning(f"Patterns fetch error: {patterns}")
                patterns = {}

            fetch_time = time.time() - start_time
            logger.debug(f"Context fetch took {fetch_time:.2f}s")

            # Analyze with LLM using enhanced context
            result = await self._analyze_with_llm_enhanced(
                content=content,
                recent_messages=recent_messages,
                triggers=triggers,
                sender_id=sender_id,
                patterns=patterns
            )

            # Update message record (run in thread)
            await asyncio.to_thread(
                db_service.update_partner_message_analysis,
                message_id,
                result.sentiment_score,
                result.sentiment_label,
                result.emotions,
                result.detected_triggers,
                result.escalation_risk,
                result.gottman_markers
            )

            # If high escalation or triggers detected, update relationship intelligence
            if result.escalation_risk in ['high', 'critical'] or result.detected_triggers:
                await self._update_relationship_intelligence(
                    relationship_id=relationship_id,
                    sender_id=sender_id,
                    result=result,
                    message_content=content
                )

            total_time = time.time() - start_time
            logger.info(f"Analyzed message {message_id}: sentiment={result.sentiment_label}, risk={result.escalation_risk} ({total_time:.2f}s)")

            return result.model_dump()

        except Exception as e:
            logger.error(f"Error analyzing message {message_id}: {e}")
            return None

    async def _get_relationship_patterns(self, relationship_id: str) -> Dict[str, Any]:
        """Get chronic needs and escalation risk for richer analysis."""
        patterns = {
            "chronic_needs": [],
            "escalation_risk": {"score": 0.5, "interpretation": "moderate"}
        }

        try:
            pas = _get_pattern_service()
            if not pas:
                return patterns

            # Fetch patterns in parallel
            chronic_needs_task = pas.track_chronic_needs(relationship_id)
            escalation_risk_task = pas.calculate_escalation_risk(relationship_id)

            chronic_needs, escalation_risk = await asyncio.gather(
                chronic_needs_task,
                escalation_risk_task,
                return_exceptions=True
            )

            if not isinstance(chronic_needs, Exception) and chronic_needs:
                patterns["chronic_needs"] = [n.need for n in chronic_needs[:5]]

            if not isinstance(escalation_risk, Exception) and escalation_risk:
                patterns["escalation_risk"] = {
                    "score": escalation_risk.risk_score,
                    "interpretation": escalation_risk.interpretation
                }

        except Exception as e:
            logger.warning(f"Error fetching relationship patterns: {e}")

        return patterns

    async def _analyze_with_llm_enhanced(
        self,
        content: str,
        recent_messages: List[dict],
        triggers: List[dict],
        sender_id: str,
        patterns: Dict[str, Any]
    ) -> MessageAnalysisResult:
        """
        Enhanced LLM-based message analysis with full relationship context.

        Integrates:
        - Conversation history
        - Known trigger phrases
        - Chronic unmet needs
        - Current escalation risk level
        """
        # Build conversation context
        conversation_context = ""
        if recent_messages:
            context_msgs = [m for m in recent_messages if m.get('content') != content][-3:]
            if context_msgs:
                conversation_context = "Recent conversation:\n" + "\n".join([
                    f"{msg['sender_id']}: {msg['content']}"
                    for msg in context_msgs
                ])

        # Build trigger context
        trigger_phrases = [t.get('phrase', t) if isinstance(t, dict) else str(t) for t in triggers[:20]] if triggers else []
        trigger_context = ""
        if trigger_phrases:
            trigger_context = f"Known trigger phrases: {', '.join(trigger_phrases[:10])}"

        # Build pattern context
        chronic_needs = patterns.get("chronic_needs", [])
        chronic_needs_context = ""
        if chronic_needs:
            chronic_needs_context = f"Chronic unmet needs in this relationship: {', '.join(chronic_needs[:5])}"

        escalation_risk = patterns.get("escalation_risk", {})
        risk_score = escalation_risk.get("score", 0.5)
        risk_level = "HIGH" if risk_score > 0.7 else "MODERATE" if risk_score > 0.4 else "LOW"
        risk_context = f"Current relationship escalation risk: {risk_level}"

        prompt = f"""Analyze this message sent between partners in a relationship.

{conversation_context}

MESSAGE TO ANALYZE (from {sender_id}):
"{content}"

=== RELATIONSHIP CONTEXT ===
{trigger_context}
{chronic_needs_context}
{risk_context}
=== END CONTEXT ===

Analyze for:
1. Sentiment: Overall tone from -1 (very negative) to 1 (very positive)
2. Emotions: What emotions are expressed or implied? Choose from: happy, sad, angry, frustrated, anxious, hurt, hopeful, loving, grateful, worried, confused, tired
3. Triggers: Does it contain any known trigger phrases or potentially triggering language?
4. Escalation Risk: Could this message escalate conflict given the current risk level? (low, medium, high, critical)
   - If relationship is already at HIGH risk, be more sensitive to potential escalation
5. Gottman's Four Horsemen:
   - Criticism: Attack on character rather than specific behavior
   - Contempt: Disrespect, mockery, sarcasm, eye-rolling language
   - Defensiveness: Denying responsibility, making excuses
   - Stonewalling: Withdrawing, shutting down, refusing to engage
6. Repair Attempt: Is this trying to de-escalate or repair the connection?
7. Bid for Connection: Is this reaching out for attention, affection, or engagement?
   - Consider if the message addresses any chronic unmet needs

Be accurate and nuanced. Many messages are positive or neutral - not everything is negative.
Short messages like "ok" or "sure" are typically neutral with low risk.
Loving messages should have high positive sentiment.
Messages that address chronic needs should be noted positively.
"""

        try:
            result = await asyncio.to_thread(
                self.llm.structured_output,
                [{"role": "user", "content": prompt}],
                MessageAnalysisResult,
                0.3
            )
            return result
        except Exception as e:
            logger.error(f"LLM analysis error: {e}")
            return MessageAnalysisResult(
                sentiment_score=0.0,
                sentiment_label="neutral",
                emotions=[],
                detected_triggers=[],
                escalation_risk="low",
                gottman_markers={
                    "criticism": False,
                    "contempt": False,
                    "defensiveness": False,
                    "stonewalling": False
                },
                repair_attempt=False,
                bid_for_connection=False
            )

    # Keep the old method as fallback
    async def _analyze_with_llm(
        self,
        content: str,
        recent_messages: List[dict],
        triggers: List[dict],
        sender_id: str
    ) -> MessageAnalysisResult:
        """
        LLM-based message analysis using structured output (legacy fallback).
        """
        # Build conversation context
        conversation_context = ""
        if recent_messages:
            # Take last 3 messages for context (excluding current)
            context_msgs = [m for m in recent_messages if m.get('content') != content][-3:]
            if context_msgs:
                conversation_context = "Recent conversation:\n" + "\n".join([
                    f"{msg['sender_id']}: {msg['content']}"
                    for msg in context_msgs
                ])

        # Build trigger context
        trigger_phrases = [t.get('phrase', t) if isinstance(t, dict) else str(t) for t in triggers[:20]] if triggers else []
        trigger_context = ""
        if trigger_phrases:
            trigger_context = f"\nKnown trigger phrases for this couple: {', '.join(trigger_phrases)}"

        prompt = f"""Analyze this message sent between partners in a relationship.

{conversation_context}

MESSAGE TO ANALYZE (from {sender_id}):
"{content}"
{trigger_context}

Analyze for:
1. Sentiment: Overall tone from -1 (very negative) to 1 (very positive)
2. Emotions: What emotions are expressed or implied? Choose from: happy, sad, angry, frustrated, anxious, hurt, hopeful, loving, grateful, worried, confused, tired
3. Triggers: Does it contain any known trigger phrases or potentially triggering language?
4. Escalation Risk: Could this message escalate conflict? (low, medium, high, critical)
5. Gottman's Four Horsemen:
   - Criticism: Attack on character rather than specific behavior
   - Contempt: Disrespect, mockery, sarcasm, eye-rolling language
   - Defensiveness: Denying responsibility, making excuses
   - Stonewalling: Withdrawing, shutting down, refusing to engage
6. Repair Attempt: Is this trying to de-escalate or repair the connection?
7. Bid for Connection: Is this reaching out for attention, affection, or engagement?

Be accurate and nuanced. Many messages are positive or neutral - not everything is negative.
Short messages like "ok" or "sure" are typically neutral with low risk.
Loving messages should have high positive sentiment.
"""

        try:
            # Run LLM call in thread since it's synchronous
            result = await asyncio.to_thread(
                self.llm.structured_output,
                [{"role": "user", "content": prompt}],
                MessageAnalysisResult,
                0.3  # Lower temperature for consistent analysis
            )
            return result
        except Exception as e:
            logger.error(f"LLM analysis error: {e}")
            # Return neutral default on error
            return MessageAnalysisResult(
                sentiment_score=0.0,
                sentiment_label="neutral",
                emotions=[],
                detected_triggers=[],
                escalation_risk="low",
                gottman_markers={
                    "criticism": False,
                    "contempt": False,
                    "defensiveness": False,
                    "stonewalling": False
                },
                repair_attempt=False,
                bid_for_connection=False
            )

    def _get_relationship_triggers(self, relationship_id: str) -> List[dict]:
        """Get known trigger phrases for this relationship."""
        try:
            # Try to get triggers from the database
            triggers = db_service.get_trigger_phrases_for_relationship(relationship_id)
            return triggers or []
        except Exception as e:
            logger.warning(f"Could not get triggers: {e}")
            return []

    async def _update_relationship_intelligence(
        self,
        relationship_id: str,
        sender_id: str,
        result: MessageAnalysisResult,
        message_content: str
    ):
        """
        Update relationship-level intelligence when significant patterns detected.
        This feeds into the cross-fight intelligence system.
        """
        try:
            # Add new trigger phrases if detected
            for trigger in result.detected_triggers:
                try:
                    await asyncio.to_thread(
                        db_service.add_detected_trigger,
                        relationship_id,
                        trigger,
                        'partner_messaging',
                        sender_id
                    )
                except Exception as e:
                    logger.warning(f"Could not add trigger phrase: {e}")

            # Track escalation patterns
            if result.escalation_risk in ['high', 'critical']:
                try:
                    await asyncio.to_thread(
                        db_service.record_escalation_event,
                        relationship_id,
                        'partner_messaging',
                        result.escalation_risk,
                        message_content[:200]  # Truncate for storage
                    )
                except Exception as e:
                    logger.warning(f"Could not record escalation event: {e}")

        except Exception as e:
            logger.error(f"Error updating relationship intelligence: {e}")


# Singleton instance
message_analysis_service = MessageAnalysisService()
