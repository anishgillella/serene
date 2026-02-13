"""
Pydantic models for HeartSync data structures

Note: This module uses gender-neutral terminology (partner_a, partner_b)
to support all relationship types (same-sex, non-binary, etc.)
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Any
from datetime import datetime


class SpeakerSegment(BaseModel):
    """A single speaker segment in a transcript"""
    speaker: str  # Dynamic partner name (e.g., "Alex", "Jordan")
    text: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class ConflictTranscript(BaseModel):
    """Model for storing conflict transcripts in Pinecone"""
    conflict_id: str
    relationship_id: str
    transcript_text: str
    speaker_segments: List[SpeakerSegment]
    timestamp: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float  # in seconds
    partner_a_id: str
    partner_b_id: str
    speaker_labels: dict = Field(
        default_factory=dict,
        description="Mapping of speaker IDs to partner names, e.g., {0: 'Partner A Name', 1: 'Partner B Name'}"
    )


class EscalationPoint(BaseModel):
    """A point where the conflict escalated"""
    timestamp: Optional[float] = None
    reason: str
    description: Optional[str] = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def coerce_timestamp(cls, v: Any) -> Optional[float]:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            # Handle "MM:SS" or "HH:MM:SS" strings from LLM
            try:
                parts = v.split(":")
                if len(parts) == 2:
                    return float(parts[0]) * 60 + float(parts[1])
                if len(parts) == 3:
                    return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
                return float(v)
            except (ValueError, IndexError):
                return None
        return None


class ConflictAnalysis(BaseModel):
    """Model for conflict analysis results"""
    conflict_id: str
    fight_summary: str = Field(description="A concise summary of what the fight was about")
    root_causes: List[str] = Field(description="Underlying issues that led to the conflict")
    escalation_points: List[EscalationPoint] = Field(
        default_factory=list,
        description="Key moments where the conflict escalated"
    )
    # Gender-neutral field names
    unmet_needs_partner_a: List[str] = Field(
        default_factory=list,
        description="Needs that partner A expressed but weren't met"
    )
    unmet_needs_partner_b: List[str] = Field(
        default_factory=list,
        description="Needs that partner B expressed but weren't met"
    )
    # Backward compatibility aliases
    @property
    def unmet_needs_boyfriend(self) -> List[str]:
        """Backward compatibility alias for unmet_needs_partner_a"""
        return self.unmet_needs_partner_a

    @property
    def unmet_needs_girlfriend(self) -> List[str]:
        """Backward compatibility alias for unmet_needs_partner_b"""
        return self.unmet_needs_partner_b

    communication_breakdowns: List[str] = Field(
        default_factory=list,
        description="Specific communication failures that occurred"
    )
    analyzed_at: datetime = Field(default_factory=datetime.now)


class RepairPlan(BaseModel):
    """Model for repair plan and coaching"""
    conflict_id: Optional[str] = Field(default=None, description="Set programmatically, not by LLM")
    partner_requesting: Optional[str] = Field(default=None, description="Set programmatically, not by LLM")
    steps: List[str] = Field(description="Actionable steps for repair")
    apology_script: str = Field(description="Personalized apology script")
    timing_suggestion: str = Field(description="When and how to approach the repair")
    risk_factors: List[str] = Field(
        default_factory=list,
        description="Potential risks or things to avoid"
    )
    generated_at: datetime = Field(default_factory=datetime.now)


# Helper functions for pdf_type normalization
def normalize_pdf_type(pdf_type: str) -> str:
    """Convert legacy pdf_type values to gender-neutral equivalents."""
    mapping = {
        'boyfriend_profile': 'partner_a_profile',
        'girlfriend_profile': 'partner_b_profile',
        'boyfriend': 'partner_a_profile',
        'girlfriend': 'partner_b_profile',
    }
    return mapping.get(pdf_type, pdf_type)


def is_partner_a_profile(pdf_type: str) -> bool:
    """Check if pdf_type refers to partner A's profile."""
    return pdf_type in ('boyfriend_profile', 'partner_a_profile', 'boyfriend', 'partner_a')


def is_partner_b_profile(pdf_type: str) -> bool:
    """Check if pdf_type refers to partner B's profile."""
    return pdf_type in ('girlfriend_profile', 'partner_b_profile', 'girlfriend', 'partner_b')


# ============================================================================
# Phase 1: Conflict Triggers & Escalation Analysis Models
# ============================================================================

class TriggerPhrase(BaseModel):
    """A phrase that escalates conflicts"""
    phrase: str
    phrase_category: str  # 'temporal_reference', 'passive_aggressive', 'blame', etc.
    emotional_intensity: int = Field(ge=1, le=10)
    references_past: bool = False
    speaker: Optional[str] = None  # 'partner_a' or 'partner_b'
    is_escalation_trigger: bool = False
    past_conflict_id: Optional[str] = None


class UnmetNeed(BaseModel):
    """An unmet need identified in a conflict"""
    need: str  # 'feeling_heard', 'trust', 'appreciation', etc.
    identified_by: str = "gpt_analysis"  # 'gpt_analysis' or 'manual'
    confidence: float = Field(ge=0.0, le=1.0)
    speaker: Optional[str] = None  # 'partner_a', 'partner_b', or 'both'
    evidence: Optional[str] = None  # supporting quote


class ConflictEnrichment(BaseModel):
    """Enriched conflict data with relationships and patterns"""
    conflict_id: str
    parent_conflict_id: Optional[str] = None
    trigger_phrases: List[TriggerPhrase] = Field(default_factory=list)
    unmet_needs: List[UnmetNeed] = Field(default_factory=list)
    resentment_level: int = Field(ge=1, le=10)
    has_past_references: bool = False
    conflict_chain_id: Optional[str] = None
    is_continuation: bool = False


class ConflictWithEnrichment(BaseModel):
    """Complete conflict data including enrichment"""
    id: str
    relationship_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    transcript_path: Optional[str] = None
    status: str = "active"

    # Enrichment fields
    parent_conflict_id: Optional[str] = None
    resentment_level: Optional[int] = None
    unmet_needs: List[str] = Field(default_factory=list)
    has_past_references: bool = False
    conflict_chain_id: Optional[str] = None
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None

    # Related data
    trigger_phrases: List[TriggerPhrase] = Field(default_factory=list)
    all_unmet_needs: List[UnmetNeed] = Field(default_factory=list)


class TriggerPhraseAnalysis(BaseModel):
    """Analysis of trigger phrase patterns"""
    phrase: str
    phrase_category: str
    usage_count: int
    avg_emotional_intensity: float
    escalation_rate: float  # 0.0-1.0
    speaker: Optional[str] = None
    is_pattern_trigger: bool


class UnmetNeedRecurrence(BaseModel):
    """Tracking of recurring unmet needs"""
    need: str
    conflict_count: int
    first_appeared: datetime
    days_appeared_in: int
    is_chronic: bool
    percentage_of_conflicts: float


class EscalationRiskReport(BaseModel):
    """Risk assessment for escalation"""
    risk_score: float = Field(ge=0.0, le=1.0)
    interpretation: str  # 'low', 'medium', 'high', 'critical'
    unresolved_issues: int
    days_until_predicted_conflict: int
    factors: dict = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)


# ============================================================================
# Phase 2: Personalized Repair Plan Models
# ============================================================================

class RepairStep(BaseModel):
    """A single repair step with mandatory citation"""
    action: str = Field(description="What to do")
    rationale: str = Field(description="Why this will help")
    citation_type: str = Field(description="profile, transcript, pattern, or calendar")
    citation_detail: str = Field(description="Specific reference, e.g., 'Sarah needs space after conflicts'")


class AvoidanceItem(BaseModel):
    """Something to avoid with citation"""
    what_to_avoid: str
    why: str
    citation_type: str  # 'profile', 'transcript', 'pattern'
    citation_detail: str


class PersonalizedRepairPlan(BaseModel):
    """Repair plan with mandatory citations and personalization"""
    conflict_id: str
    requesting_partner: str = Field(description="Who is initiating repair")
    target_partner: str = Field(description="Who they are approaching")
    generated_at: datetime = Field(default_factory=datetime.now)

    # Timing
    when_to_approach: str = Field(description="Specific timing recommendation")
    timing_rationale: str = Field(description="Why this timing, referencing profile/patterns")
    timing_citation: str = Field(description="Reference to profile post_conflict_need")

    # Steps (3-6 required)
    steps: List[RepairStep] = Field(
        description="Actionable steps with citations"
    )

    # Apology
    apology_script: str = Field(description="Personalized apology script")
    apology_rationale: str = Field(description="How this aligns with their apology_preferences")

    # Gesture
    suggested_gesture: str = Field(description="Specific gesture from their repair_gestures list")
    gesture_citation: str = Field(description="Reference to their profile")

    # Avoidances (minimum 2)
    things_to_avoid: List[AvoidanceItem] = Field(
        description="Things to avoid with citations"
    )

    # Historical references (if available)
    lessons_from_past: List[str] = Field(
        default_factory=list,
        description="References to past fights and what worked/didn't"
    )

    # Meta
    personalization_score: str = Field(
        default="medium",
        description="Self-assessment of citation coverage: high, medium, low"
    )
    missing_data: List[str] = Field(
        default_factory=list,
        description="Profile fields that were empty/missing"
    )


# ============================================================================
# Phase 3: Fight Debrief Models
# ============================================================================

class RepairAttemptOutcome(BaseModel):
    """A single repair attempt and its outcome within a fight"""
    timestamp: str = Field(description="Approximate time in transcript, e.g., '3:42'")
    speaker: str  # 'partner_a' or 'partner_b'
    speaker_name: str

    # What they did
    action_type: str = Field(
        description="apologized, validated_feelings, took_responsibility, offered_solution, used_humor, physical_affection, asked_for_break, redirected_topic, expressed_love, other"
    )
    what_they_said_or_did: str = Field(description="Quote or description of the attempt")

    # What happened next
    outcome: str  # 'helped', 'hurt', 'neutral'
    outcome_evidence: str = Field(description="What happened in the next 30-60 seconds")

    # Learnings
    why_it_worked_or_failed: str = Field(description="Analysis of why this attempt had this outcome")


class FightDebrief(BaseModel):
    """Comprehensive post-fight analysis - generated once per fight"""
    conflict_id: str
    relationship_id: str
    analyzed_at: datetime = Field(default_factory=datetime.now)

    # === WHAT HAPPENED ===
    topic: str = Field(description="Main topic/issue, 2-5 words")
    summary: str = Field(description="What happened in 2-3 sentences")
    duration_estimate: str = Field(description="e.g., '15 minutes', '1 hour'")
    intensity_peak: str  # 'low', 'medium', 'high', 'explosive'

    key_moments: List[str] = Field(
        default_factory=list,
        description="3-5 pivotal moments with timestamps"
    )

    # === REPAIR DYNAMICS ===
    repair_attempts: List[RepairAttemptOutcome] = Field(default_factory=list)
    who_initiated_repairs: str  # 'partner_a', 'partner_b', 'both', 'neither'
    total_repair_attempts: int = 0
    successful_repairs: int = 0
    failed_repairs: int = 0

    most_effective_moment: Optional[str] = Field(
        default=None,
        description="The moment that helped most, with quote"
    )
    most_damaging_moment: Optional[str] = Field(
        default=None,
        description="The moment that hurt most, with quote"
    )

    # === RESOLUTION ===
    resolution_status: str  # 'resolved', 'unresolved', 'temporary_truce'
    what_resolved_it: Optional[str] = Field(
        default=None,
        description="If resolved, what worked"
    )
    what_remains_unresolved: Optional[str] = Field(
        default=None,
        description="Issues still open"
    )

    # === LEARNINGS ===
    phrases_to_avoid: List[str] = Field(
        default_factory=list,
        description="Things said that made it worse"
    )
    phrases_that_helped: List[str] = Field(
        default_factory=list,
        description="Things said that helped"
    )
    unmet_needs_partner_a: List[str] = Field(default_factory=list)
    unmet_needs_partner_b: List[str] = Field(default_factory=list)

    what_would_have_helped: str = Field(
        default="",
        description="What could have prevented escalation or resolved faster"
    )

    # === CONNECTION TO PAST ===
    similar_to_past_topics: List[str] = Field(
        default_factory=list,
        description="Topics from past fights this resembles"
    )
    recurring_pattern_detected: Optional[str] = Field(
        default=None,
        description="If this fight follows a pattern seen before"
    )


# ============================================================================
# Phase 4: Cross-Fight Intelligence Models
# ============================================================================

class EscalationTriggerPattern(BaseModel):
    """Pattern of a phrase/behavior that consistently escalates fights"""
    trigger_phrase: str = Field(description="The phrase or behavior")
    occurrence_count: int = Field(description="How many times this triggered escalation")
    total_fights_analyzed: int = Field(description="Total fights where this was seen")
    escalation_rate: float = Field(description="Percentage of times this led to escalation (0.0-1.0)")
    example_conflicts: List[str] = Field(
        default_factory=list,
        description="Conflict IDs where this occurred"
    )
    who_typically_says_it: str = Field(
        default="both",
        description="partner_a, partner_b, or both"
    )


class DeescalationTechnique(BaseModel):
    """A technique that has helped de-escalate fights"""
    technique: str = Field(description="What was said or done")
    success_count: int = Field(description="Times this helped")
    attempt_count: int = Field(description="Total times attempted")
    success_rate: float = Field(description="Success rate (0.0-1.0)")
    action_type: str = Field(
        description="apologized, validated_feelings, took_responsibility, etc."
    )
    who_typically_uses_it: str = Field(
        default="both",
        description="partner_a, partner_b, or both"
    )
    best_timing: Optional[str] = Field(
        default=None,
        description="When this works best (early, mid, late in fight)"
    )


class RecurringTopic(BaseModel):
    """A topic that comes up repeatedly in conflicts"""
    topic: str = Field(description="The recurring topic/issue")
    occurrence_count: int = Field(description="Number of fights about this")
    first_seen: str = Field(description="Date of first fight about this")
    last_seen: str = Field(description="Date of most recent fight")
    resolution_rate: float = Field(
        description="Percentage of times this was resolved (0.0-1.0)"
    )
    average_intensity: str = Field(
        description="Average intensity: low, medium, high"
    )
    underlying_need_partner_a: Optional[str] = Field(
        default=None,
        description="What Partner A typically needs regarding this topic"
    )
    underlying_need_partner_b: Optional[str] = Field(
        default=None,
        description="What Partner B typically needs regarding this topic"
    )


class RepairOutcomeInference(BaseModel):
    """Inferred outcome of a past repair plan without user feedback"""
    conflict_id: str
    repair_plan_generated_at: str
    inference_method: str = Field(
        description="no_recurrence, same_topic_recurred, topic_resolved, insufficient_data"
    )
    inferred_success: bool
    confidence: str = Field(description="high, medium, low")
    evidence: str = Field(description="What led to this inference")
    days_until_next_similar_fight: Optional[int] = Field(
        default=None,
        description="Days until a similar fight occurred (if any)"
    )


class CrossFightIntelligence(BaseModel):
    """Aggregated intelligence from all past fights for a relationship"""
    relationship_id: str
    generated_at: datetime = Field(default_factory=datetime.now)
    total_fights_analyzed: int = Field(default=0)
    analysis_period_days: int = Field(
        default=90,
        description="How many days of data this covers"
    )

    # === ESCALATION PATTERNS ===
    escalation_triggers: List[EscalationTriggerPattern] = Field(
        default_factory=list,
        description="Phrases/behaviors that consistently escalate fights"
    )
    top_escalation_trigger: Optional[str] = Field(
        default=None,
        description="The single most problematic trigger"
    )

    # === DE-ESCALATION TECHNIQUES ===
    deescalation_techniques: List[DeescalationTechnique] = Field(
        default_factory=list,
        description="What has worked to calm things down"
    )
    most_effective_technique: Optional[str] = Field(
        default=None,
        description="The single most effective technique"
    )

    # === RECURRING TOPICS ===
    recurring_topics: List[RecurringTopic] = Field(
        default_factory=list,
        description="Topics that come up repeatedly"
    )
    chronic_unresolved_issue: Optional[str] = Field(
        default=None,
        description="The topic that keeps coming back unresolved"
    )

    # === REPAIR STRATEGY EFFECTIVENESS ===
    repair_outcomes: List[RepairOutcomeInference] = Field(
        default_factory=list,
        description="Inferred outcomes of past repair plans"
    )
    overall_repair_success_rate: float = Field(
        default=0.0,
        description="Percentage of repair plans that seem to have worked"
    )

    # === PARTNER DYNAMICS ===
    who_initiates_repairs_more: str = Field(
        default="both",
        description="partner_a, partner_b, or both equally"
    )
    repair_initiation_counts: dict = Field(
        default_factory=lambda: {"partner_a": 0, "partner_b": 0, "both": 0, "neither": 0}
    )

    # === TIMING INSIGHTS ===
    average_fight_duration: str = Field(
        default="unknown",
        description="Average duration of conflicts"
    )
    average_days_between_fights: Optional[float] = Field(
        default=None,
        description="Average days between conflicts"
    )
    high_risk_periods: List[str] = Field(
        default_factory=list,
        description="Time periods when fights are more likely"
    )

    # === RECOMMENDATIONS ===
    key_insight: str = Field(
        default="",
        description="The most important insight from analyzing all fights"
    )
    prevention_recommendations: List[str] = Field(
        default_factory=list,
        description="What could prevent future fights"
    )


class SimilarFightResult(BaseModel):
    """A past fight that is similar to the current one"""
    conflict_id: str
    topic: str
    date: str
    similarity_score: float = Field(description="0.0-1.0 similarity")
    resolution_status: str
    what_worked: Optional[str] = None
    what_failed: Optional[str] = None
    key_lesson: str = Field(
        default="",
        description="The main takeaway from this past fight"
    )


# ============================================
# PARTNER MESSAGING MODELS
# ============================================

class PartnerConversation(BaseModel):
    """A conversation between partners"""
    id: str
    relationship_id: str
    created_at: Optional[str] = None
    last_message_at: Optional[str] = None
    last_message_preview: Optional[str] = None
    message_count: int = 0


class PartnerMessage(BaseModel):
    """A single message between partners"""
    id: str
    conversation_id: str
    sender_id: str  # 'partner_a' or 'partner_b'
    content: str
    status: str = 'sent'  # 'sent', 'delivered', 'read'
    sent_at: Optional[str] = None
    delivered_at: Optional[str] = None
    read_at: Optional[str] = None
    sentiment_label: Optional[str] = None
    emotions: List[str] = Field(default_factory=list)
    escalation_risk: Optional[str] = None
    luna_intervened: bool = False


class SendMessageRequest(BaseModel):
    """Request to send a partner message"""
    conversation_id: str
    sender_id: str = Field(..., pattern='^(partner_a|partner_b)$')
    content: str = Field(..., min_length=1, max_length=5000)
    request_luna_review: bool = False
    original_content: Optional[str] = None
    luna_intervened: bool = False


class SendMessageResponse(BaseModel):
    """Response after sending a message"""
    message: PartnerMessage
    luna_suggestion: Optional[dict] = None  # For Phase 3


class GetMessagesRequest(BaseModel):
    """Request to get messages"""
    conversation_id: str
    limit: int = Field(default=50, ge=1, le=100)
    before: Optional[str] = None  # ISO timestamp for pagination


class GetMessagesResponse(BaseModel):
    """Response with messages list"""
    messages: List[PartnerMessage]
    has_more: bool
    oldest_timestamp: Optional[str] = None


class MessagingPreferences(BaseModel):
    """User preferences for messaging and Luna assistance"""
    id: str
    relationship_id: str
    partner_id: str
    luna_assistance_enabled: bool = True
    suggestion_mode: str = 'on_request'  # 'always', 'on_request', 'high_risk_only', 'off'
    intervention_enabled: bool = True
    intervention_sensitivity: str = 'medium'  # 'low', 'medium', 'high'
    push_notifications_enabled: bool = True
    notification_sound: bool = True
    show_sentiment_indicators: bool = False
    show_read_receipts: bool = True
    show_typing_indicators: bool = True
    demo_mode_enabled: bool = False  # When true, partner_b is simulated by LLM
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UpdatePreferencesRequest(BaseModel):
    """Request to update messaging preferences"""
    luna_assistance_enabled: Optional[bool] = None
    suggestion_mode: Optional[str] = Field(
        default=None,
        pattern='^(always|on_request|high_risk_only|off)$'
    )
    intervention_enabled: Optional[bool] = None
    intervention_sensitivity: Optional[str] = Field(
        default=None,
        pattern='^(low|medium|high)$'
    )
    push_notifications_enabled: Optional[bool] = None
    notification_sound: Optional[bool] = None
    show_sentiment_indicators: Optional[bool] = None
    show_read_receipts: Optional[bool] = None
    show_typing_indicators: Optional[bool] = None
    demo_mode_enabled: Optional[bool] = None


# ============================================
# CONNECTION GESTURES MODELS
# ============================================

from enum import Enum


class GestureType(str, Enum):
    """Types of connection gestures"""
    HUG = "hug"
    KISS = "kiss"
    THINKING_OF_YOU = "thinking_of_you"


class ConnectionGesture(BaseModel):
    """A connection gesture between partners"""
    id: str
    relationship_id: str
    gesture_type: str  # 'hug', 'kiss', 'thinking_of_you'
    sent_by: str  # 'partner_a' or 'partner_b'
    message: Optional[str] = None
    ai_generated: bool = False
    sent_at: Optional[str] = None
    delivered_at: Optional[str] = None
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    response_gesture_id: Optional[str] = None


class SendGestureRequest(BaseModel):
    """Request to send a connection gesture"""
    relationship_id: str
    gesture_type: GestureType
    sender_id: str = Field(..., pattern='^(partner_a|partner_b)$')
    message: Optional[str] = Field(default=None, max_length=280)
    ai_generated: bool = False
    ai_context: Optional[dict] = None  # What context AI used


class SendGestureResponse(BaseModel):
    """Response after sending a gesture"""
    gesture: ConnectionGesture
    recipient_online: bool


class AcknowledgeGestureRequest(BaseModel):
    """Request to acknowledge a received gesture"""
    gesture_id: str
    acknowledged_by: str = Field(..., pattern='^(partner_a|partner_b)$')
    send_back: bool = False
    send_back_type: Optional[GestureType] = None
    send_back_message: Optional[str] = Field(default=None, max_length=280)


class AcknowledgeGestureResponse(BaseModel):
    """Response after acknowledging a gesture"""
    acknowledged: bool
    response_gesture: Optional[ConnectionGesture] = None


class PendingGesturesResponse(BaseModel):
    """Response with pending gestures for a partner"""
    gestures: List[ConnectionGesture]
    count: int


class GenerateGestureMessageRequest(BaseModel):
    """Request to generate AI message for a gesture"""
    relationship_id: str
    sender_id: str = Field(..., pattern='^(partner_a|partner_b)$')
    gesture_type: GestureType


class GenerateGestureMessageResponse(BaseModel):
    """Response with AI-generated message"""
    message: str
    context_used: List[str]  # What context sources were used


# ============================================================================
# REPAIR PLAN COMPLIANCE MODELS
# ============================================================================

class RepairComplianceStep(BaseModel):
    """A single step in a repair plan compliance checklist"""
    id: str
    repair_plan_id: str
    conflict_id: str
    relationship_id: str
    partner: str  # 'partner_a' or 'partner_b'
    step_index: int
    step_description: str
    completed: bool = False
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class RepairComplianceStatus(BaseModel):
    """Status of repair plan compliance for a conflict"""
    conflict_id: str
    has_data: bool
    steps: List[RepairComplianceStep] = Field(default_factory=list)
    progress: dict = Field(default_factory=lambda: {"total": 0, "completed": 0, "percentage": 0})


class RepairComplianceSummary(BaseModel):
    """Overall compliance rate across all conflicts"""
    has_data: bool
    overall: dict = Field(default_factory=lambda: {
        "total_steps": 0, "completed_steps": 0,
        "compliance_rate": 0, "conflicts_with_plans": 0
    })
    per_conflict: List[dict] = Field(default_factory=list)


# ============================================================================
# ADVANCED METRICS RESPONSE MODELS
# ============================================================================

class SentimentShiftConflict(BaseModel):
    """Sentiment shift data for a single conflict"""
    conflict_id: str
    started_at: str
    start_intensity: float
    end_intensity: float
    shift_score: float


class SentimentShiftAggregate(BaseModel):
    """Aggregate sentiment shift statistics"""
    avg_shift: float
    trend_direction: str  # 'improving', 'declining', 'stable'
    total_analyzed: int


class SentimentShiftResponse(BaseModel):
    """Response for sentiment shift endpoint"""
    has_data: bool
    per_conflict: List[SentimentShiftConflict] = Field(default_factory=list)
    aggregate: SentimentShiftAggregate = Field(
        default_factory=lambda: SentimentShiftAggregate(avg_shift=0, trend_direction='stable', total_analyzed=0)
    )


class MonthlyCommData(BaseModel):
    """Communication metrics for a single month"""
    month: str
    conflicts_count: int
    i_statement_ratio: float
    interruptions_per_conflict: float
    active_listening_per_conflict: float
    repair_success_rate: float


class MonthlyGrowth(BaseModel):
    """Month-over-month growth percentages"""
    month: str
    i_statement_ratio: float = 0
    interruptions_per_conflict: float = 0
    active_listening_per_conflict: float = 0
    repair_success_rate: float = 0


class CommunicationGrowthResponse(BaseModel):
    """Response for communication growth endpoint"""
    has_data: bool
    monthly_data: List[MonthlyCommData] = Field(default_factory=list)
    growth_percentages: List[MonthlyGrowth] = Field(default_factory=list)


class FightPeriodData(BaseModel):
    """Fight data for a single period"""
    period_start: str
    fight_count: int
    resolved_count: int
    avg_duration_minutes: float


class FightFrequencyResponse(BaseModel):
    """Response for fight frequency endpoint"""
    has_data: bool
    period: str
    periods: List[FightPeriodData] = Field(default_factory=list)
    average_days_between: Optional[float] = None


class RecoveryConflict(BaseModel):
    """Recovery data for a single conflict"""
    conflict_id: str
    ended_at: str
    next_positive_date: Optional[str] = None
    recovery_days: Optional[int] = None


class RecoveryTimeResponse(BaseModel):
    """Response for recovery time endpoint"""
    has_data: bool
    per_conflict: List[RecoveryConflict] = Field(default_factory=list)
    average_recovery_days: Optional[float] = None
    trend: str = 'stable'


class AttachmentPartnerData(BaseModel):
    """Attachment style data for a partner"""
    model_config = {"arbitrary_types_allowed": True}

    partner: str
    primary_style: str
    secondary_style: Optional[str] = None
    confidence: float
    behavioral_indicators: Any = Field(default_factory=list)
    summary: str
    interaction_dynamic: Optional[str] = None
    conflicts_analyzed: Optional[int] = None
    last_updated: Optional[Any] = None


class AttachmentStyleResponse(BaseModel):
    """Response for attachment styles endpoint"""
    has_data: bool
    partner_a: Optional[AttachmentPartnerData] = None
    partner_b: Optional[AttachmentPartnerData] = None
    interaction_dynamic: Optional[str] = None


class BidResponseOverall(BaseModel):
    """Overall bid-response statistics"""
    total_bids: int
    toward: int = 0
    away: int = 0
    against: int = 0
    toward_rate: float = 0
    gottman_benchmark: float = 86.0


class BidResponsePartner(BaseModel):
    """Per-partner bid-response data"""
    total_bids: int
    toward: int = 0
    away: int = 0
    against: int = 0
    toward_rate: float = 0


class BidResponseRatioResponse(BaseModel):
    """Response for bid-response ratio endpoint"""
    has_data: bool
    overall: BidResponseOverall = Field(default_factory=lambda: BidResponseOverall(total_bids=0))
    per_partner: dict = Field(default_factory=dict)


class BidResponseConflictResponse(BaseModel):
    """Response for per-conflict bid-response endpoint"""
    conflict_id: str
    has_data: bool
    bids: List[dict] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)


class NarrativeInsightsResponse(BaseModel):
    """Response for narrative insights endpoint"""
    has_data: bool
    overview_digest: Optional[str] = None
    fight_quality_insight: Optional[str] = None
    trigger_insight: Optional[str] = None
    growth_insight: Optional[str] = None
    cross_metric_correlations: List[str] = Field(default_factory=list)


