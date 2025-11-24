"""
Pydantic models for HeartSync data structures
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class SpeakerSegment(BaseModel):
    """A single speaker segment in a transcript"""
    speaker: str  # "Boyfriend" or "Girlfriend"
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
        description="Mapping of speaker IDs to names, e.g., {0: 'Boyfriend', 1: 'Girlfriend'}"
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
    unmet_needs_boyfriend: List[str] = Field(
        default_factory=list,
        description="Needs that the boyfriend expressed but weren't met"
    )
    unmet_needs_girlfriend: List[str] = Field(
        default_factory=list,
        description="Needs that the girlfriend expressed but weren't met"
    )
    communication_breakdowns: List[str] = Field(
        default_factory=list,
        description="Specific communication failures that occurred"
    )
    analyzed_at: datetime = Field(default_factory=datetime.now)


class RepairPlan(BaseModel):
    """Model for repair plan and coaching"""
    conflict_id: str
    partner_requesting: str  # "Boyfriend" or "Girlfriend"
    steps: List[str] = Field(description="Actionable steps for repair")
    apology_script: str = Field(description="Personalized apology script")
    timing_suggestion: str = Field(description="When and how to approach the repair")
    risk_factors: List[str] = Field(
        default_factory=list,
        description="Potential risks or things to avoid"
    )
    generated_at: datetime = Field(default_factory=datetime.now)






