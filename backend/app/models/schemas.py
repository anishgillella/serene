"""
Pydantic models for HeartSync data structures

Note: This module uses gender-neutral terminology (partner_a, partner_b)
to support all relationship types (same-sex, non-binary, etc.)
"""
from pydantic import BaseModel, Field
from typing import List, Optional
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
    conflict_id: str
    partner_requesting: str  # "partner_a" or "partner_b" (or partner's actual name)
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



