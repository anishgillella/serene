"""
Advanced Analytics Service
Provides deep relationship insights including:
1. Surface vs Underlying Concerns mapping
2. Emotional Temperature Timeline (per-conflict + trends)
3. Partner-Specific Trigger Sensitivity
4. Conflict Replay with Annotations
"""
import asyncio
import logging
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from psycopg2.extras import RealDictCursor

from app.services.llm_service import llm_service
from app.services.db_service import db_service

logger = logging.getLogger(__name__)


# ============================================================================
# PYDANTIC MODELS FOR LLM STRUCTURED OUTPUT
# ============================================================================

class SurfaceUnderlyingItem(BaseModel):
    """Maps a surface statement to its underlying meaning"""
    surface_statement: str = Field(description="The exact quote or paraphrased surface complaint")
    surface_category: str = Field(description="Category: complaint, accusation, withdrawal, dismissal, demand, sarcasm")
    underlying_concern: str = Field(description="What they really mean or need")
    underlying_emotion: str = Field(description="Primary emotion: hurt, fear, loneliness, overwhelm, rejection, disrespect, anxiety, sadness")
    underlying_need: str = Field(description="Core need: feeling_heard, trust, appreciation, respect, autonomy, security, intimacy, validation")
    speaker: str = Field(description="partner_a or partner_b")
    confidence: float = Field(description="Confidence in interpretation 0.0-1.0")
    evidence: str = Field(description="Quote or context supporting this interpretation")


class SurfaceUnderlyingAnalysis(BaseModel):
    """Complete surface vs underlying analysis for a conflict"""
    mappings: List[SurfaceUnderlyingItem] = Field(description="List of surface-to-underlying mappings")
    overall_pattern: str = Field(description="Summary of the main communication pattern observed")
    key_insight: str = Field(description="The most important insight about what's really going on")


class EmotionalMoment(BaseModel):
    """Emotional state at a specific moment in the conflict"""
    message_sequence: int = Field(description="The sequence number of this message")
    speaker: str = Field(description="partner_a or partner_b")
    emotional_intensity: int = Field(description="0-10 scale of emotional intensity")
    negativity_score: int = Field(description="0-10 scale of negativity (0=positive, 10=very negative)")
    defensiveness_level: int = Field(description="0-10 scale of defensiveness")
    primary_emotion: str = Field(description="Primary emotion: anger, hurt, frustration, sadness, contempt, fear, anxiety, disappointment")
    secondary_emotion: Optional[str] = Field(description="Secondary emotion if present")
    is_escalation_point: bool = Field(description="True if this moment escalated the conflict")
    is_repair_attempt: bool = Field(description="True if this was a repair attempt")
    is_de_escalation: bool = Field(description="True if this de-escalated the conflict")
    moment_note: str = Field(description="Brief note about what's happening emotionally")


class EmotionalTimelineAnalysis(BaseModel):
    """Complete emotional timeline for a conflict"""
    moments: List[EmotionalMoment] = Field(description="Emotional state at each message")
    peak_intensity_moment: int = Field(description="Sequence number of peak intensity")
    peak_emotion: str = Field(description="The dominant emotion at peak")
    total_escalations: int = Field(description="Number of escalation points")
    total_repair_attempts: int = Field(description="Number of repair attempts")
    successful_de_escalations: int = Field(description="Number of successful de-escalations")
    emotional_arc: str = Field(description="Description of the overall emotional arc: escalating, volatile, recovering, resolved")


class TriggerSensitivity(BaseModel):
    """A specific trigger sensitivity for a partner"""
    trigger_category: str = Field(description="Category: criticism, dismissal, past_reference, tone, interruption, topic_money, topic_family, topic_work, comparison, silence")
    trigger_description: str = Field(description="Human-readable description of what triggers this")
    sensitivity_score: float = Field(description="0.0-1.0 how sensitive they are to this")
    reaction_type: str = Field(description="How they typically react: defensive, withdrawal, escalation, tears, anger")
    example_phrases: List[str] = Field(description="Example phrases that trigger this reaction")


class PartnerSensitivityAnalysis(BaseModel):
    """Trigger sensitivity analysis for both partners"""
    partner_a_triggers: List[TriggerSensitivity] = Field(description="Partner A's trigger sensitivities")
    partner_b_triggers: List[TriggerSensitivity] = Field(description="Partner B's trigger sensitivities")
    cross_trigger_patterns: List[str] = Field(description="Patterns where one partner's behavior triggers the other")


class ConflictAnnotation(BaseModel):
    """An annotation for a specific moment in the conflict"""
    message_sequence_start: int = Field(description="Start of annotated section")
    message_sequence_end: Optional[int] = Field(description="End of section (null for single message)")
    annotation_type: str = Field(description="Type: escalation, repair_attempt, missed_bid, horseman, breakthrough, suggestion, insight")
    annotation_title: str = Field(description="Brief title for the annotation")
    annotation_text: str = Field(description="Detailed annotation text")
    suggested_alternative: Optional[str] = Field(description="What could have been said instead")
    severity: str = Field(description="info, warning, critical, positive")
    related_horseman: Optional[str] = Field(description="If horseman detected: criticism, contempt, defensiveness, stonewalling")


class ConflictAnnotationsAnalysis(BaseModel):
    """Complete annotations for conflict replay"""
    annotations: List[ConflictAnnotation] = Field(description="List of annotations for the conflict")
    key_turning_points: List[int] = Field(description="Message sequence numbers of key turning points")
    overall_assessment: str = Field(description="Overall assessment of the conflict dynamics")
    primary_improvement_area: str = Field(description="The main thing this couple should work on")


# ============================================================================
# PHASE 2: ATTACHMENT STYLE + BID-RESPONSE MODELS
# ============================================================================

class AttachmentIndicator(BaseModel):
    """A behavioral indicator of attachment style"""
    behavior: str = Field(description="The observed behavior pattern")
    frequency: str = Field(description="How often: frequent, occasional, rare")
    example: str = Field(description="Example from transcripts")


class PartnerAttachmentProfile(BaseModel):
    """Attachment style assessment for one partner"""
    partner: str = Field(description="partner_a or partner_b")
    primary_style: str = Field(description="secure, anxious, avoidant, or fearful_avoidant")
    secondary_style: Optional[str] = Field(default=None, description="Secondary attachment tendency if present")
    confidence: float = Field(description="0.0-1.0 confidence in classification")
    behavioral_indicators: List[AttachmentIndicator] = Field(description="Evidence supporting this classification")
    summary: str = Field(description="Brief summary of this partner's attachment pattern")


class AttachmentStyleAnalysis(BaseModel):
    """Complete attachment style analysis for both partners"""
    partner_a: PartnerAttachmentProfile = Field(description="Partner A's attachment profile")
    partner_b: PartnerAttachmentProfile = Field(description="Partner B's attachment profile")
    interaction_dynamic: str = Field(description="How their attachment styles interact, e.g., anxious-avoidant trap")


class BidInstance(BaseModel):
    """A single bid for connection and the response"""
    partner_making_bid: str = Field(description="partner_a or partner_b")
    bid_type: str = Field(description="attention, affection, humor, support, understanding, engagement, play, exploration")
    response_type: str = Field(description="toward, away, or against")
    message_sequence: Optional[int] = Field(default=None, description="Approximate message sequence number")
    bid_text: str = Field(description="What was said/done as a bid")
    response_text: str = Field(description="How the partner responded")


class BidResponseAnalysis(BaseModel):
    """Complete bid-response analysis for a conflict"""
    bids: List[BidInstance] = Field(description="All identified bids and responses in this conflict")
    summary: str = Field(description="Overall summary of bid-response dynamics")


# ============================================================================
# NARRATIVE INSIGHTS MODEL
# ============================================================================

class NarrativeInsights(BaseModel):
    """AI-generated narrative insights that tie metrics to actionable understanding"""
    overview_digest: str = Field(description="2-3 sentence weekly digest of the relationship state")
    fight_quality_insight: str = Field(description="How this couple fights — patterns, horsemen, repair dynamics")
    trigger_insight: str = Field(description="What triggers conflicts and why")
    growth_insight: str = Field(description="Growth trajectory — what's improving and what needs work")
    cross_metric_correlations: List[str] = Field(description="2-4 cross-metric correlations tying different data points together")


# ============================================================================
# ADVANCED ANALYTICS SERVICE
# ============================================================================

class AdvancedAnalyticsService:
    """Service for advanced relationship analytics"""

    # ========================================================================
    # 1. SURFACE VS UNDERLYING CONCERNS
    # ========================================================================

    async def analyze_surface_underlying(
        self,
        conflict_id: str,
        transcript: str,
        relationship_id: str,
        partner_a_name: str = "Partner A",
        partner_b_name: str = "Partner B"
    ) -> SurfaceUnderlyingAnalysis:
        """
        Analyze transcript to map surface statements to underlying concerns.
        Reveals what people really mean vs what they say.
        """
        try:
            logger.info(f"�� Analyzing surface vs underlying for conflict {conflict_id}")

            prompt = f"""Analyze this conflict transcript to identify what each partner SAYS vs what they REALLY MEAN.

TRANSCRIPT:
{transcript}

Partner names: {partner_a_name} = partner_a, {partner_b_name} = partner_b

ANALYSIS REQUIREMENTS:
1. Identify 3-8 key statements where surface meaning differs from underlying meaning
2. For each statement, identify:
   - The surface complaint/statement (what was literally said)
   - The surface category (complaint, accusation, withdrawal, dismissal, demand, sarcasm)
   - The underlying concern (what they really need/mean)
   - The underlying emotion driving it (hurt, fear, loneliness, overwhelm, rejection, disrespect)
   - The underlying need (feeling_heard, trust, appreciation, respect, autonomy, security, intimacy, validation)
   - Who said it (partner_a or partner_b)
   - Confidence in interpretation (0.0-1.0)
   - Evidence (quote or context)

3. Identify the overall communication pattern
4. Provide ONE key insight about what's really going on beneath the surface

EXAMPLES of surface vs underlying:
- Surface: "You never help with anything!"
  Underlying: "I feel overwhelmed and alone in managing our home" (emotion: overwhelm, need: appreciation)

- Surface: "Fine, do whatever you want"
  Underlying: "My opinion doesn't seem to matter to you" (emotion: hurt, need: feeling_heard)

- Surface: "It's not a big deal"
  Underlying: "I'm shutting down because I feel attacked" (emotion: fear, need: security)

Focus on transforming blame into understanding. What would help each partner understand the other better?"""

            messages = [{"role": "user", "content": prompt}]

            result = await asyncio.to_thread(
                llm_service.structured_output,
                messages=messages,
                response_model=SurfaceUnderlyingAnalysis,
                temperature=0.6,
                max_tokens=2500
            )

            # Save to database
            await self._save_surface_underlying(conflict_id, relationship_id, result)

            logger.info(f"✅ Surface/underlying analysis complete: {len(result.mappings)} mappings found")
            return result

        except Exception as e:
            logger.error(f"❌ Error in surface/underlying analysis: {str(e)}")
            raise

    async def _save_surface_underlying(
        self,
        conflict_id: str,
        relationship_id: str,
        analysis: SurfaceUnderlyingAnalysis
    ) -> None:
        """Save surface/underlying mappings to database"""
        try:
            with db_service.get_db_context() as conn:
                with conn.cursor() as cursor:
                    for mapping in analysis.mappings:
                        cursor.execute("""
                            INSERT INTO surface_underlying_mapping (
                                conflict_id, relationship_id, speaker,
                                surface_statement, surface_category,
                                underlying_concern, underlying_emotion, underlying_need,
                                confidence, evidence
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT DO NOTHING;
                        """, (
                            conflict_id, relationship_id, mapping.speaker,
                            mapping.surface_statement, mapping.surface_category,
                            mapping.underlying_concern, mapping.underlying_emotion, mapping.underlying_need,
                            mapping.confidence, mapping.evidence
                        ))
                    conn.commit()
            logger.info(f"Saved {len(analysis.mappings)} surface/underlying mappings")
        except Exception as e:
            logger.error(f"Error saving surface/underlying mappings: {str(e)}")

    # ========================================================================
    # 2. EMOTIONAL TEMPERATURE TIMELINE
    # ========================================================================

    async def analyze_emotional_timeline(
        self,
        conflict_id: str,
        transcript: str,
        relationship_id: str,
        messages: List[Dict] = None,
        partner_a_name: str = "Partner A",
        partner_b_name: str = "Partner B"
    ) -> EmotionalTimelineAnalysis:
        """
        Analyze emotional intensity at each message in the conflict.
        Creates a timeline showing escalation, repair attempts, and de-escalation.
        """
        try:
            logger.info(f"📈 Analyzing emotional timeline for conflict {conflict_id}")

            # Format messages with sequence numbers if available
            if messages:
                formatted_messages = "\n".join([
                    f"[{i+1}] {msg.get('partner_id', 'unknown')}: {msg.get('content', '')}"
                    for i, msg in enumerate(messages)
                ])
            else:
                formatted_messages = transcript

            prompt = f"""Analyze the emotional intensity at EACH message in this conflict.

TRANSCRIPT (with sequence numbers):
{formatted_messages}

Partner names: {partner_a_name} = partner_a, {partner_b_name} = partner_b

For EACH message, analyze:
1. emotional_intensity (0-10): Overall emotional charge
2. negativity_score (0-10): How negative (0=positive/neutral, 10=hostile)
3. defensiveness_level (0-10): How defensive
4. primary_emotion: anger, hurt, frustration, sadness, contempt, fear, anxiety, disappointment, neutral
5. secondary_emotion: if present
6. is_escalation_point: Did this message escalate the conflict?
7. is_repair_attempt: Did this try to de-escalate or repair?
8. is_de_escalation: Did this successfully calm things down?
9. moment_note: Brief note about what's happening

IMPORTANT:
- Track the message_sequence number (1, 2, 3, etc.)
- Identify THE moment of peak intensity
- Count total escalations, repair attempts, and successful de-escalations
- Describe the overall emotional arc

Escalation indicators: raised voice markers (caps, !), accusations, bringing up past, contempt, dismissal
De-escalation indicators: acknowledgment, apology, softening, taking a break, validation
Repair attempts: humor, changing topic, offering solution, expressing care, admitting fault"""

            messages_list = [{"role": "user", "content": prompt}]

            result = await asyncio.to_thread(
                llm_service.structured_output,
                messages=messages_list,
                response_model=EmotionalTimelineAnalysis,
                temperature=0.5,
                max_tokens=3000
            )

            # Save to database
            await self._save_emotional_timeline(conflict_id, relationship_id, result)

            logger.info(f"✅ Emotional timeline complete: {len(result.moments)} moments, peak at {result.peak_intensity_moment}")
            return result

        except Exception as e:
            logger.error(f"❌ Error in emotional timeline analysis: {str(e)}")
            raise

    async def _save_emotional_timeline(
        self,
        conflict_id: str,
        relationship_id: str,
        analysis: EmotionalTimelineAnalysis
    ) -> None:
        """Save emotional timeline to database"""
        try:
            with db_service.get_db_context() as conn:
                with conn.cursor() as cursor:
                    # Calculate escalation delta for each moment
                    prev_intensity = 5  # Start at neutral
                    for moment in analysis.moments:
                        delta = moment.emotional_intensity - prev_intensity
                        prev_intensity = moment.emotional_intensity

                        cursor.execute("""
                            INSERT INTO emotional_temperature (
                                conflict_id, relationship_id, message_sequence, speaker,
                                emotional_intensity, negativity_score, defensiveness_level,
                                escalation_delta, is_escalation_point, is_repair_attempt, is_de_escalation,
                                primary_emotion, secondary_emotion, moment_note
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT DO NOTHING;
                        """, (
                            conflict_id, relationship_id, moment.message_sequence, moment.speaker,
                            moment.emotional_intensity, moment.negativity_score, moment.defensiveness_level,
                            delta, moment.is_escalation_point, moment.is_repair_attempt, moment.is_de_escalation,
                            moment.primary_emotion, moment.secondary_emotion, moment.moment_note
                        ))
                    conn.commit()
            logger.info(f"Saved emotional timeline with {len(analysis.moments)} moments")
        except Exception as e:
            logger.error(f"Error saving emotional timeline: {str(e)}")

    async def get_emotional_trends(
        self,
        relationship_id: str,
        period_type: str = "weekly",
        periods: int = 8
    ) -> List[Dict]:
        """
        Get emotional trends across multiple conflicts over time.
        Shows how emotional patterns are changing.
        """
        try:
            with db_service.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Validate period_type to prevent injection
                    if period_type not in ('daily', 'weekly', 'monthly'):
                        period_type = 'weekly'

                    cursor.execute("""
                        SELECT
                            DATE_TRUNC(%s, c.started_at) as period,
                            COUNT(DISTINCT c.id) as conflicts_count,
                            AVG(et.emotional_intensity) as avg_intensity,
                            MAX(et.emotional_intensity) as peak_intensity,
                            AVG(et.negativity_score) as avg_negativity,
                            COUNT(*) FILTER (WHERE et.is_escalation_point) as total_escalations,
                            COUNT(*) FILTER (WHERE et.is_repair_attempt) as total_repair_attempts,
                            COUNT(*) FILTER (WHERE et.is_de_escalation) as total_de_escalations
                        FROM conflicts c
                        LEFT JOIN emotional_temperature et ON et.conflict_id = c.id
                        WHERE c.relationship_id = %s
                          AND c.started_at >= NOW() - make_interval(weeks => %s)
                        GROUP BY DATE_TRUNC(%s, c.started_at)
                        ORDER BY period DESC
                        LIMIT %s;
                    """, (period_type, relationship_id, periods, period_type, periods))

                    rows = cursor.fetchall()

            # Calculate trends
            trends = []
            for i, row in enumerate(rows):
                trend_data = dict(row)
                if i < len(rows) - 1:
                    prev = rows[i + 1]
                    trend_data['intensity_trend'] = 'improving' if row['avg_intensity'] < prev['avg_intensity'] else 'worsening' if row['avg_intensity'] > prev['avg_intensity'] else 'stable'
                else:
                    trend_data['intensity_trend'] = 'stable'
                trends.append(trend_data)

            return trends

        except Exception as e:
            logger.error(f"Error getting emotional trends: {str(e)}")
            return []

    # ========================================================================
    # 3. PARTNER-SPECIFIC TRIGGER SENSITIVITY
    # ========================================================================

    async def analyze_trigger_sensitivity(
        self,
        relationship_id: str,
        partner_a_name: str = "Partner A",
        partner_b_name: str = "Partner B"
    ) -> PartnerSensitivityAnalysis:
        """
        Analyze trigger sensitivity patterns for each partner based on all conflicts.
        Identifies what triggers each partner and how they react.
        """
        try:
            logger.info(f"🎯 Analyzing trigger sensitivity for relationship {relationship_id}")

            # Get recent conflicts for analysis
            conflicts = db_service.get_previous_conflicts(relationship_id, limit=10)
            if not conflicts:
                logger.info("No conflicts found for trigger analysis")
                return PartnerSensitivityAnalysis(
                    partner_a_triggers=[],
                    partner_b_triggers=[],
                    cross_trigger_patterns=[]
                )

            # Gather transcripts
            transcripts = []
            for conflict in conflicts:
                transcript_data = db_service.get_conflict_transcript(conflict['id'])
                if transcript_data and transcript_data.get('transcript_text'):
                    transcripts.append(f"--- Conflict {conflict['id'][:8]} ---\n{transcript_data['transcript_text'][:1500]}")

            combined_context = "\n\n".join(transcripts[:5])  # Limit to 5 most recent

            prompt = f"""Analyze these conflict transcripts to identify trigger sensitivities for each partner.

CONFLICT HISTORY:
{combined_context}

Partner names: {partner_a_name} = partner_a, {partner_b_name} = partner_b

ANALYZE FOR EACH PARTNER:
1. What topics/phrases/behaviors trigger strong emotional reactions?
2. How do they typically react when triggered (defensive, withdrawal, escalation, tears, anger)?
3. What patterns repeat across multiple conflicts?

TRIGGER CATEGORIES to consider:
- criticism: Direct criticism of character or behavior
- dismissal: Being dismissed, interrupted, or ignored
- past_reference: Bringing up past failures/mistakes
- tone: Sarcasm, condescension, raised voice
- interruption: Being cut off or talked over
- topic_money: Financial disagreements
- topic_family: In-laws or family issues
- topic_work: Work-life balance issues
- comparison: Unfavorable comparisons to others
- silence: Partner going silent or stonewalling

For each partner, identify 3-5 trigger sensitivities with:
- Category and description
- Sensitivity score (0.0-1.0) - how reactive they are
- Typical reaction type
- Example phrases that trigger this

Also identify cross-trigger patterns where one partner's behavior predictably triggers the other."""

            messages = [{"role": "user", "content": prompt}]

            result = await asyncio.to_thread(
                llm_service.structured_output,
                messages=messages,
                response_model=PartnerSensitivityAnalysis,
                temperature=0.5,
                max_tokens=2500
            )

            # Save to database
            await self._save_trigger_sensitivity(relationship_id, result)

            logger.info(f"✅ Trigger sensitivity analysis complete: {len(result.partner_a_triggers)} for A, {len(result.partner_b_triggers)} for B")
            return result

        except Exception as e:
            logger.error(f"❌ Error in trigger sensitivity analysis: {str(e)}")
            raise

    async def _save_trigger_sensitivity(
        self,
        relationship_id: str,
        analysis: PartnerSensitivityAnalysis
    ) -> None:
        """Save trigger sensitivity scores to database"""
        try:
            with db_service.get_db_context() as conn:
                with conn.cursor() as cursor:
                    # Save Partner A triggers
                    for trigger in analysis.partner_a_triggers:
                        cursor.execute("""
                            INSERT INTO partner_trigger_sensitivity (
                                relationship_id, partner, trigger_category, trigger_description,
                                sensitivity_score, example_phrases
                            ) VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (relationship_id, partner, trigger_category)
                            DO UPDATE SET
                                trigger_description = EXCLUDED.trigger_description,
                                sensitivity_score = EXCLUDED.sensitivity_score,
                                example_phrases = EXCLUDED.example_phrases,
                                updated_at = NOW();
                        """, (
                            relationship_id, 'partner_a', trigger.trigger_category,
                            trigger.trigger_description, trigger.sensitivity_score,
                            trigger.example_phrases
                        ))

                    # Save Partner B triggers
                    for trigger in analysis.partner_b_triggers:
                        cursor.execute("""
                            INSERT INTO partner_trigger_sensitivity (
                                relationship_id, partner, trigger_category, trigger_description,
                                sensitivity_score, example_phrases
                            ) VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (relationship_id, partner, trigger_category)
                            DO UPDATE SET
                                trigger_description = EXCLUDED.trigger_description,
                                sensitivity_score = EXCLUDED.sensitivity_score,
                                example_phrases = EXCLUDED.example_phrases,
                                updated_at = NOW();
                        """, (
                            relationship_id, 'partner_b', trigger.trigger_category,
                            trigger.trigger_description, trigger.sensitivity_score,
                            trigger.example_phrases
                        ))

                    conn.commit()
            logger.info(f"Saved trigger sensitivity data")
        except Exception as e:
            logger.error(f"Error saving trigger sensitivity: {str(e)}")

    async def get_partner_sensitivities(
        self,
        relationship_id: str
    ) -> Dict[str, Any]:
        """Get stored trigger sensitivities for a relationship"""
        try:
            with db_service.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT * FROM partner_trigger_sensitivity
                        WHERE relationship_id = %s
                        ORDER BY sensitivity_score DESC;
                    """, (relationship_id,))
                    rows = cursor.fetchall()

            partner_a = [dict(r) for r in rows if r['partner'] == 'partner_a']
            partner_b = [dict(r) for r in rows if r['partner'] == 'partner_b']

            return {
                'partner_a_triggers': partner_a,
                'partner_b_triggers': partner_b
            }

        except Exception as e:
            logger.error(f"Error getting partner sensitivities: {str(e)}")
            return {'partner_a_triggers': [], 'partner_b_triggers': []}

    # ========================================================================
    # 4. CONFLICT REPLAY WITH ANNOTATIONS
    # ========================================================================

    async def generate_conflict_annotations(
        self,
        conflict_id: str,
        transcript: str,
        relationship_id: str,
        messages: List[Dict] = None,
        partner_a_name: str = "Partner A",
        partner_b_name: str = "Partner B"
    ) -> ConflictAnnotationsAnalysis:
        """
        Generate annotations for conflict replay.
        Marks escalation points, repair attempts, missed bids, and suggestions.
        """
        try:
            logger.info(f"📝 Generating annotations for conflict {conflict_id}")

            # Format messages with sequence numbers
            if messages:
                formatted_messages = "\n".join([
                    f"[{i+1}] {msg.get('partner_id', 'unknown')}: {msg.get('content', '')}"
                    for i, msg in enumerate(messages)
                ])
            else:
                formatted_messages = transcript

            prompt = f"""Analyze this conflict and generate annotations for each significant moment.

TRANSCRIPT (with sequence numbers):
{formatted_messages}

Partner names: {partner_a_name} = partner_a, {partner_b_name} = partner_b

GENERATE ANNOTATIONS FOR:

1. **Escalation Points** (severity: warning/critical)
   - Where did things get worse?
   - What was said that escalated?
   - Suggest what could have been said instead

2. **Repair Attempts** (severity: positive/info)
   - When did someone try to de-escalate?
   - Was it successful?
   - If failed, why?

3. **Missed Bids for Connection** (severity: warning)
   - When did someone reach out and get ignored?
   - Examples: "I just wanted to talk" met with dismissal

4. **Four Horsemen Appearances** (severity: critical)
   - Criticism, Contempt, Defensiveness, Stonewalling
   - Mark exact moment and suggest alternative

5. **Breakthroughs** (severity: positive)
   - Moments of genuine understanding
   - Successful repairs
   - Vulnerability that was well-received

6. **Suggestions** (severity: info)
   - What could have been said differently
   - Communication techniques that would help

FOR EACH ANNOTATION:
- message_sequence_start: Which message number
- message_sequence_end: End range (null for single message)
- annotation_type: escalation, repair_attempt, missed_bid, horseman, breakthrough, suggestion, insight
- annotation_title: Brief title (e.g., "Criticism Detected", "Missed Repair Opportunity")
- annotation_text: Detailed explanation
- suggested_alternative: What could have been said instead (if applicable)
- severity: info, warning, critical, positive
- related_horseman: If horseman detected

Also identify:
- Key turning points (message numbers)
- Overall assessment
- Primary area for improvement"""

            messages_list = [{"role": "user", "content": prompt}]

            result = await asyncio.to_thread(
                llm_service.structured_output,
                messages=messages_list,
                response_model=ConflictAnnotationsAnalysis,
                temperature=0.5,
                max_tokens=3000
            )

            # Save to database
            await self._save_annotations(conflict_id, relationship_id, result)

            logger.info(f"✅ Generated {len(result.annotations)} annotations")
            return result

        except Exception as e:
            logger.error(f"❌ Error generating annotations: {str(e)}")
            raise

    async def _save_annotations(
        self,
        conflict_id: str,
        relationship_id: str,
        analysis: ConflictAnnotationsAnalysis
    ) -> None:
        """Save annotations to database"""
        try:
            with db_service.get_db_context() as conn:
                with conn.cursor() as cursor:
                    # Delete existing auto-generated annotations for this conflict
                    cursor.execute("""
                        DELETE FROM conflict_annotations
                        WHERE conflict_id = %s AND is_auto_generated = TRUE;
                    """, (conflict_id,))

                    for annotation in analysis.annotations:
                        cursor.execute("""
                            INSERT INTO conflict_annotations (
                                conflict_id, relationship_id,
                                message_sequence_start, message_sequence_end,
                                annotation_type, annotation_title, annotation_text,
                                suggested_alternative, severity, related_horseman,
                                is_auto_generated
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE);
                        """, (
                            conflict_id, relationship_id,
                            annotation.message_sequence_start, annotation.message_sequence_end,
                            annotation.annotation_type, annotation.annotation_title, annotation.annotation_text,
                            annotation.suggested_alternative, annotation.severity, annotation.related_horseman
                        ))
                    conn.commit()
            logger.info(f"Saved {len(analysis.annotations)} annotations")
        except Exception as e:
            logger.error(f"Error saving annotations: {str(e)}")

    async def get_conflict_annotations(
        self,
        conflict_id: str
    ) -> List[Dict]:
        """Get annotations for a specific conflict"""
        try:
            with db_service.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT * FROM conflict_annotations
                        WHERE conflict_id = %s
                        ORDER BY message_sequence_start;
                    """, (conflict_id,))
                    rows = cursor.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error getting annotations: {str(e)}")
            return []

    # ========================================================================
    # 5. ATTACHMENT STYLE TRACKING
    # ========================================================================

    async def analyze_attachment_patterns(
        self,
        relationship_id: str,
        partner_a_name: str = "Partner A",
        partner_b_name: str = "Partner B"
    ) -> Dict[str, Any]:
        """
        Analyze attachment style patterns from conflict transcripts.
        Classifies each partner as secure/anxious/avoidant/fearful-avoidant.
        """
        try:
            logger.info(f"🔍 Analyzing attachment patterns for {relationship_id}")

            # Get recent conflicts
            conflicts = db_service.get_previous_conflicts(relationship_id, limit=10)
            if not conflicts:
                return {"partner_a": None, "partner_b": None, "interaction_dynamic": None}

            # Gather transcripts
            transcripts = []
            for conflict in conflicts:
                transcript_data = db_service.get_conflict_transcript(conflict['id'])
                if transcript_data and transcript_data.get('transcript_text'):
                    transcripts.append(f"--- Conflict {conflict['id'][:8]} ---\n{transcript_data['transcript_text'][:1500]}")

            combined_context = "\n\n".join(transcripts[:5])

            prompt = f"""Analyze these conflict transcripts to identify each partner's attachment style.

CONFLICT HISTORY:
{combined_context}

Partner names: {partner_a_name} = partner_a, {partner_b_name} = partner_b

ATTACHMENT STYLES TO CLASSIFY:
- **secure**: Comfortable with intimacy and independence. Communicates needs clearly, manages emotions well.
- **anxious**: Fears abandonment. Seeks reassurance, escalates to get attention, hypervigilant about partner's mood.
- **avoidant**: Uncomfortable with closeness. Withdraws under stress, minimizes emotions, values independence excessively.
- **fearful_avoidant**: Desires closeness but fears it. Push-pull behavior, unpredictable reactions, difficulty trusting.

FOR EACH PARTNER:
1. Classify primary and secondary (if any) attachment style
2. Confidence level (0.0-1.0)
3. Behavioral indicators with examples from transcripts
4. Brief summary paragraph

Also describe the INTERACTION DYNAMIC between their styles (e.g., "anxious-avoidant dance where {partner_a_name}'s need for reassurance triggers {partner_b_name}'s withdrawal").

Focus on concrete behavioral evidence from the transcripts."""

            messages = [{"role": "user", "content": prompt}]

            result = await asyncio.to_thread(
                llm_service.structured_output,
                messages=messages,
                response_model=AttachmentStyleAnalysis,
                temperature=0.5,
                max_tokens=3000
            )

            # Save to database
            await self._save_attachment_styles(relationship_id, result, len(conflicts))

            return {
                "partner_a": {
                    "partner": "partner_a",
                    "primary_style": result.partner_a.primary_style,
                    "secondary_style": result.partner_a.secondary_style,
                    "confidence": result.partner_a.confidence,
                    "behavioral_indicators": [i.model_dump() for i in result.partner_a.behavioral_indicators],
                    "summary": result.partner_a.summary,
                },
                "partner_b": {
                    "partner": "partner_b",
                    "primary_style": result.partner_b.primary_style,
                    "secondary_style": result.partner_b.secondary_style,
                    "confidence": result.partner_b.confidence,
                    "behavioral_indicators": [i.model_dump() for i in result.partner_b.behavioral_indicators],
                    "summary": result.partner_b.summary,
                },
                "interaction_dynamic": result.interaction_dynamic
            }

        except Exception as e:
            logger.error(f"❌ Error analyzing attachment patterns: {str(e)}")
            raise

    async def _save_attachment_styles(
        self,
        relationship_id: str,
        analysis: AttachmentStyleAnalysis,
        conflicts_analyzed: int
    ) -> None:
        """Save attachment style data to database"""
        try:
            with db_service.get_db_context() as conn:
                with conn.cursor() as cursor:
                    for profile in [analysis.partner_a, analysis.partner_b]:
                        indicators = [i.model_dump() for i in profile.behavioral_indicators]
                        cursor.execute("""
                            INSERT INTO attachment_style_tracking (
                                relationship_id, partner, primary_style, secondary_style,
                                confidence, behavioral_indicators, summary,
                                interaction_dynamic, conflicts_analyzed, last_updated
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                            ON CONFLICT (relationship_id, partner)
                            DO UPDATE SET
                                primary_style = EXCLUDED.primary_style,
                                secondary_style = EXCLUDED.secondary_style,
                                confidence = EXCLUDED.confidence,
                                behavioral_indicators = EXCLUDED.behavioral_indicators,
                                summary = EXCLUDED.summary,
                                interaction_dynamic = EXCLUDED.interaction_dynamic,
                                conflicts_analyzed = EXCLUDED.conflicts_analyzed,
                                last_updated = NOW();
                        """, (
                            relationship_id, profile.partner,
                            profile.primary_style, profile.secondary_style,
                            profile.confidence, json.dumps(indicators),
                            profile.summary, analysis.interaction_dynamic,
                            conflicts_analyzed
                        ))
                    conn.commit()
            logger.info(f"Saved attachment style data for {relationship_id}")
        except Exception as e:
            logger.error(f"Error saving attachment styles: {str(e)}")

    # ========================================================================
    # 6. BID-RESPONSE TRACKING
    # ========================================================================

    async def analyze_bid_response(
        self,
        conflict_id: str,
        transcript: str,
        relationship_id: str,
        partner_a_name: str = "Partner A",
        partner_b_name: str = "Partner B"
    ) -> BidResponseAnalysis:
        """
        Analyze bids for connection and responses in a conflict transcript.
        """
        try:
            logger.info(f"🤝 Analyzing bid-response for conflict {conflict_id}")

            prompt = f"""Analyze this conflict transcript for Gottman's "bids for connection."

A BID is any attempt by one partner to connect — seeking attention, affection, humor, support, understanding, engagement, play, or exploration.

RESPONSES to bids:
- **toward**: Engaging positively with the bid (acknowledging, reciprocating, showing interest)
- **away**: Ignoring or not noticing the bid (changing subject, distracted, no response)
- **against**: Rejecting the bid with hostility (dismissing, criticizing, attacking)

TRANSCRIPT:
{transcript}

Partner names: {partner_a_name} = partner_a, {partner_b_name} = partner_b

Identify ALL bids for connection in this conflict. For each:
1. Who made the bid (partner_a or partner_b)
2. Type of bid (attention, affection, humor, support, understanding, engagement, play, exploration)
3. How the partner responded (toward, away, against)
4. Approximate message sequence number
5. What was said as the bid
6. What the response was

NOTE: Even in conflicts, there are bids — "Can you just listen to me?" is a bid for understanding.
"I'm trying to tell you how I feel" is a bid for attention/understanding.

The Gottman benchmark: Stable relationships turn toward bids 86% of the time.
Provide a summary of the overall bid-response dynamic."""

            messages = [{"role": "user", "content": prompt}]

            result = await asyncio.to_thread(
                llm_service.structured_output,
                messages=messages,
                response_model=BidResponseAnalysis,
                temperature=0.5,
                max_tokens=3000
            )

            # Save to database
            await self._save_bid_response(conflict_id, relationship_id, result)

            logger.info(f"✅ Bid-response analysis complete: {len(result.bids)} bids found")
            return result

        except Exception as e:
            logger.error(f"❌ Error in bid-response analysis: {str(e)}")
            raise

    async def _save_bid_response(
        self,
        conflict_id: str,
        relationship_id: str,
        analysis: BidResponseAnalysis
    ) -> None:
        """Save bid-response data to database"""
        try:
            with db_service.get_db_context() as conn:
                with conn.cursor() as cursor:
                    for bid in analysis.bids:
                        cursor.execute("""
                            INSERT INTO bid_response_tracking (
                                relationship_id, conflict_id,
                                partner_making_bid, bid_type, response_type,
                                message_sequence, bid_text, response_text
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                        """, (
                            relationship_id, conflict_id,
                            bid.partner_making_bid, bid.bid_type, bid.response_type,
                            bid.message_sequence, bid.bid_text, bid.response_text
                        ))
                    conn.commit()
            logger.info(f"Saved {len(analysis.bids)} bid-response records")
        except Exception as e:
            logger.error(f"Error saving bid-response data: {str(e)}")

    async def get_bid_response_ratios(
        self,
        relationship_id: str
    ) -> Dict[str, Any]:
        """Get aggregated bid-response ratios across all conflicts"""
        try:
            with db_service.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Overall ratios
                    cursor.execute("""
                        SELECT
                            COUNT(*) as total_bids,
                            COUNT(*) FILTER (WHERE response_type = 'toward') as toward,
                            COUNT(*) FILTER (WHERE response_type = 'away') as away,
                            COUNT(*) FILTER (WHERE response_type = 'against') as against
                        FROM bid_response_tracking
                        WHERE relationship_id = %s;
                    """, (relationship_id,))
                    overall = cursor.fetchone()

                    # Per-partner ratios
                    cursor.execute("""
                        SELECT
                            partner_making_bid,
                            COUNT(*) as total_bids,
                            COUNT(*) FILTER (WHERE response_type = 'toward') as toward,
                            COUNT(*) FILTER (WHERE response_type = 'away') as away,
                            COUNT(*) FILTER (WHERE response_type = 'against') as against
                        FROM bid_response_tracking
                        WHERE relationship_id = %s
                        GROUP BY partner_making_bid;
                    """, (relationship_id,))
                    per_partner = cursor.fetchall()

            total = overall['total_bids'] or 0
            toward = overall['toward'] or 0

            partner_data = {}
            for row in per_partner:
                p_total = row['total_bids'] or 0
                partner_data[row['partner_making_bid']] = {
                    "total_bids": p_total,
                    "toward": row['toward'] or 0,
                    "away": row['away'] or 0,
                    "against": row['against'] or 0,
                    "toward_rate": round((row['toward'] or 0) / p_total * 100, 1) if p_total > 0 else 0
                }

            return {
                "has_data": total > 0,
                "overall": {
                    "total_bids": total,
                    "toward": toward,
                    "away": overall['away'] or 0,
                    "against": overall['against'] or 0,
                    "toward_rate": round(toward / total * 100, 1) if total > 0 else 0,
                    "gottman_benchmark": 86.0
                },
                "per_partner": partner_data
            }

        except Exception as e:
            logger.error(f"Error getting bid-response ratios: {str(e)}")
            return {"has_data": False, "overall": {"total_bids": 0}, "per_partner": {}}

    # ========================================================================
    # NARRATIVE INSIGHTS (AI-GENERATED DIGEST)
    # ========================================================================

    async def generate_narrative_insights(
        self,
        metrics: Dict[str, Any],
        partner_a_name: str = "Partner A",
        partner_b_name: str = "Partner B",
        viewer_role: Optional[str] = None
    ) -> NarrativeInsights:
        """
        Generate AI narrative insights from all metric data.
        Ties numbers to actionable understanding.
        """
        try:
            logger.info("Generating narrative insights")

            # Build context from all available metrics
            context_parts = []

            dashboard = metrics.get("dashboard", {})
            if dashboard:
                context_parts.append(f"Health score: {dashboard.get('health_score', 'N/A')}/100")
                m = dashboard.get("metrics", {})
                context_parts.append(f"Total conflicts: {m.get('total_conflicts', 0)}, resolved: {m.get('resolved_conflicts', 0)}, resolution rate: {m.get('resolution_rate', 0):.0f}%")
                risk = dashboard.get("escalation_risk", {})
                context_parts.append(f"Escalation risk: {risk.get('interpretation', 'unknown')} ({risk.get('risk_score', 0):.2f})")

            gottman = metrics.get("gottman", {})
            if gottman and gottman.get("has_data"):
                fh = gottman.get("four_horsemen", {})
                context_parts.append(f"Gottman score: {gottman.get('gottman_health_score', 0)}/100")
                context_parts.append(f"Four Horsemen — criticism: {fh.get('criticism', 0)}, contempt: {fh.get('contempt', 0)}, defensiveness: {fh.get('defensiveness', 0)}, stonewalling: {fh.get('stonewalling', 0)}")
                rm = gottman.get("repair_metrics", {})
                context_parts.append(f"Repair success rate: {rm.get('success_rate', 0)}%, attempts: {rm.get('total_attempts', 0)}")

            sentiment = metrics.get("sentiment", {})
            if sentiment and sentiment.get("has_data"):
                agg = sentiment.get("aggregate", {})
                context_parts.append(f"Avg sentiment shift: {agg.get('avg_shift', 0)} (trend: {agg.get('trend_direction', 'stable')})")

            growth = metrics.get("growth", {})
            if growth and growth.get("has_data"):
                gp = growth.get("growth_percentages", [])
                if gp:
                    latest = gp[-1]
                    context_parts.append(f"Latest growth — I-statement ratio: {latest.get('i_statement_ratio', 0)}%, repair success: {latest.get('repair_success_rate', 0)}%")

            frequency = metrics.get("frequency", {})
            if frequency and frequency.get("has_data"):
                context_parts.append(f"Avg days between fights: {frequency.get('average_days_between', 'N/A')}")

            recovery = metrics.get("recovery", {})
            if recovery and recovery.get("has_data"):
                context_parts.append(f"Avg recovery time: {recovery.get('average_recovery_days', 'N/A')} days (trend: {recovery.get('trend', 'stable')})")

            attachment = metrics.get("attachment", {})
            if attachment and attachment.get("has_data"):
                pa = attachment.get("partner_a", {})
                pb = attachment.get("partner_b", {})
                if pa and pb:
                    context_parts.append(f"Attachment styles — {partner_a_name}: {pa.get('primary_style', '?')}, {partner_b_name}: {pb.get('primary_style', '?')}")
                    context_parts.append(f"Interaction dynamic: {attachment.get('interaction_dynamic', 'N/A')}")

            bid_response = metrics.get("bid_response", {})
            if bid_response and bid_response.get("has_data"):
                overall = bid_response.get("overall", {})
                context_parts.append(f"Bid-response toward rate: {overall.get('toward_rate', 0)}% (benchmark: 86%)")

            metrics_context = "\n".join(f"- {p}" for p in context_parts)

            # Determine viewer personalization
            if viewer_role == "partner_a":
                viewer_name = partner_a_name
                their_partner_name = partner_b_name
            elif viewer_role == "partner_b":
                viewer_name = partner_b_name
                their_partner_name = partner_a_name
            else:
                viewer_name = None
                their_partner_name = None

            viewer_instruction = ""
            if viewer_name:
                viewer_instruction = f"""
PERSONALIZATION:
The person reading this is {viewer_name}. Address them directly as "you" and refer to {their_partner_name} by name.
For example: "You've been initiating repairs more often, {viewer_name}" or "When {their_partner_name} brings up..."
Frame advice and observations from {viewer_name}'s perspective — what THEY can do, what THEIR patterns are, what to watch for in THEIR behavior.
Still mention {their_partner_name}'s patterns where relevant, but the primary audience is {viewer_name}.
"""

            prompt = f"""You are a relationship therapist writing brief, warm, actionable insights for a couple.

RELATIONSHIP METRICS:
{metrics_context}

Partner names: {partner_a_name} and {partner_b_name}
{viewer_instruction}
Generate narrative insights:

1. **overview_digest**: A 2-3 sentence weekly digest. Be specific about numbers but warm in tone. Mention what's going well AND one area to watch.

2. **fight_quality_insight**: How does this couple fight? Reference Four Horsemen levels, repair success rate, sentiment shifts. Be specific. One paragraph.

3. **trigger_insight**: What triggers their conflicts? Reference any trigger patterns, attachment dynamics, chronic needs. One paragraph.

4. **growth_insight**: Are they growing? Reference communication growth trends, recovery time trends, fight frequency changes. One paragraph.

5. **cross_metric_correlations**: 2-4 specific correlations that connect different metrics, e.g., "Your high repair rate (X%) likely contributes to your improving recovery time." Each should be one sentence connecting two specific data points.

RULES:
- Use partner names, never "Partner A/B"
- Reference specific numbers from the data
- Be warm but honest — don't sugarcoat concerning patterns
- Keep each insight concise (2-4 sentences max)
- If data is missing for a section, say what would help (e.g., "Log more conflicts to see trends")"""

            messages = [{"role": "user", "content": prompt}]

            result = await asyncio.to_thread(
                llm_service.structured_output,
                messages=messages,
                response_model=NarrativeInsights,
                temperature=0.7,
                max_tokens=1500
            )

            logger.info("Narrative insights generated successfully")
            return result

        except Exception as e:
            logger.error(f"Error generating narrative insights: {str(e)}")
            raise

    # ========================================================================
    # COMPREHENSIVE ANALYSIS (ALL FEATURES)
    # ========================================================================

    async def run_full_analysis(
        self,
        conflict_id: str,
        relationship_id: str,
        partner_a_name: str = "Partner A",
        partner_b_name: str = "Partner B"
    ) -> Dict[str, Any]:
        """
        Run all four advanced analytics on a conflict.
        Returns combined results.
        """
        try:
            logger.info(f"🚀 Running full advanced analytics for conflict {conflict_id}")

            # Get transcript and messages
            transcript_data = db_service.get_conflict_transcript(conflict_id)
            if not transcript_data:
                raise ValueError(f"No transcript found for conflict {conflict_id}")

            transcript = transcript_data.get('transcript_text', '')
            messages = transcript_data.get('messages', [])

            # Run all analyses in parallel (including bid-response)
            results = await asyncio.gather(
                self.analyze_surface_underlying(
                    conflict_id, transcript, relationship_id,
                    partner_a_name, partner_b_name
                ),
                self.analyze_emotional_timeline(
                    conflict_id, transcript, relationship_id, messages,
                    partner_a_name, partner_b_name
                ),
                self.generate_conflict_annotations(
                    conflict_id, transcript, relationship_id, messages,
                    partner_a_name, partner_b_name
                ),
                self.analyze_bid_response(
                    conflict_id, transcript, relationship_id,
                    partner_a_name, partner_b_name
                ),
                return_exceptions=True
            )

            surface_underlying, emotional_timeline, annotations, bid_response = results

            # Handle any errors
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Analysis {i} failed: {str(result)}")

            # Re-analyze attachment styles every 3rd conflict
            attachment_result = None
            try:
                conflicts = db_service.get_previous_conflicts(relationship_id, limit=100)
                if len(conflicts) % 3 == 0 or len(conflicts) <= 3:
                    attachment_result = await self.analyze_attachment_patterns(
                        relationship_id, partner_a_name, partner_b_name
                    )
            except Exception as e:
                logger.error(f"Attachment analysis failed: {str(e)}")

            return {
                'conflict_id': conflict_id,
                'surface_underlying': surface_underlying if not isinstance(surface_underlying, Exception) else None,
                'emotional_timeline': emotional_timeline if not isinstance(emotional_timeline, Exception) else None,
                'annotations': annotations if not isinstance(annotations, Exception) else None,
                'bid_response': bid_response if not isinstance(bid_response, Exception) else None,
                'attachment_styles': attachment_result,
            }

        except Exception as e:
            logger.error(f"❌ Error in full analysis: {str(e)}")
            raise


# Singleton instance
advanced_analytics_service = AdvancedAnalyticsService()
