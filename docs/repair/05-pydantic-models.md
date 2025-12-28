# Pydantic Models Reference

All data models for the personalized repair plan system.

---

## Phase 1: Enhanced Partner Profile

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime


class PartnerProfile(BaseModel):
    """Complete partner profile including repair preferences"""

    # Identity
    name: str
    role: Literal["partner_a", "partner_b"]
    age: int

    # Background
    background_story: str
    key_life_experiences: str

    # Inner World
    communication_style: str
    stress_triggers: list[str]
    soothing_mechanisms: list[str]
    traumatic_experiences: Optional[str] = None

    # Repair Preferences (NEW - Phase 1)
    apology_preferences: str = Field(
        description="What makes an apology feel genuine to this person"
    )
    post_conflict_need: Literal["space", "connection", "depends"] = Field(
        description="What they need first after a conflict"
    )
    repair_gestures: list[str] = Field(
        description="Small gestures that help them feel better"
    )
    escalation_triggers: list[str] = Field(
        description="Things their partner does that make fights worse"
    )

    # Partner View
    partner_description: str
    what_i_admire: str
    what_frustrates_me: str

    # Interests
    hobbies: list[str]
    favorite_food: str
    favorite_cuisine: str
    favorite_sports: list[str]
    favorite_books: list[str]
    favorite_celebrities: list[str]
```

---

## Phase 2: Personalized Repair Plan

```python
class RepairStep(BaseModel):
    """A single repair step with mandatory citation"""
    action: str = Field(description="What to do")
    rationale: str = Field(description="Why this will help")
    citation_type: Literal["profile", "transcript", "pattern", "calendar"]
    citation_detail: str = Field(
        description="Specific reference, e.g., 'Sarah needs space after conflicts'"
    )


class AvoidanceItem(BaseModel):
    """Something to avoid with citation"""
    what_to_avoid: str
    why: str
    citation_type: Literal["profile", "transcript", "pattern"]
    citation_detail: str


class PersonalizedRepairPlan(BaseModel):
    """Repair plan with mandatory citations and personalization"""

    conflict_id: str
    requesting_partner: str = Field(description="Who is initiating repair")
    target_partner: str = Field(description="Who they are approaching")
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    # Timing
    when_to_approach: str = Field(
        description="Specific timing recommendation"
    )
    timing_rationale: str = Field(
        description="Why this timing, referencing profile/patterns"
    )
    timing_citation: str = Field(
        description="Reference to profile post_conflict_need"
    )

    # Steps (3-6 required)
    steps: list[RepairStep] = Field(
        min_length=3,
        max_length=6,
        description="Actionable steps with citations"
    )

    # Apology
    apology_script: str = Field(
        description="Personalized apology script"
    )
    apology_rationale: str = Field(
        description="How this aligns with their apology_preferences"
    )

    # Gesture
    suggested_gesture: str = Field(
        description="Specific gesture from their repair_gestures list"
    )
    gesture_citation: str = Field(
        description="Reference to their profile"
    )

    # Avoidances (minimum 2)
    things_to_avoid: list[AvoidanceItem] = Field(
        min_length=2,
        description="Things to avoid with citations"
    )

    # Historical references (if available)
    lessons_from_past: list[str] = Field(
        default=[],
        description="References to past fights and what worked/didn't"
    )

    # Meta
    personalization_score: Literal["high", "medium", "low"] = Field(
        description="Self-assessment of citation coverage"
    )
    missing_data: list[str] = Field(
        default=[],
        description="Profile fields that were empty/missing"
    )
```

---

## Phase 3: Fight Debrief

```python
class RepairAttemptOutcome(BaseModel):
    """A single repair attempt and its outcome within a fight"""

    timestamp: str = Field(
        description="Approximate time in transcript, e.g., '3:42'"
    )
    speaker: Literal["partner_a", "partner_b"]
    speaker_name: str

    # What they did
    action_type: Literal[
        "apologized",
        "validated_feelings",
        "took_responsibility",
        "offered_solution",
        "used_humor",
        "physical_affection",
        "asked_for_break",
        "redirected_topic",
        "expressed_love",
        "other"
    ]
    what_they_said_or_did: str = Field(
        description="Quote or description of the attempt"
    )

    # What happened next
    outcome: Literal["helped", "hurt", "neutral"]
    outcome_evidence: str = Field(
        description="What happened in the next 30-60 seconds"
    )

    # Learnings
    why_it_worked_or_failed: str = Field(
        description="Analysis of why this attempt had this outcome"
    )


class FightDebrief(BaseModel):
    """Comprehensive post-fight analysis - generated once per fight"""

    conflict_id: str
    relationship_id: str
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

    # === WHAT HAPPENED ===
    topic: str = Field(
        description="Main topic/issue, 2-5 words"
    )
    summary: str = Field(
        description="What happened in 2-3 sentences"
    )
    duration_estimate: str = Field(
        description="e.g., '15 minutes', '1 hour'"
    )
    intensity_peak: Literal["low", "medium", "high", "explosive"]

    key_moments: list[str] = Field(
        description="3-5 pivotal moments with timestamps",
        min_length=1,
        max_length=5
    )

    # === REPAIR DYNAMICS ===
    repair_attempts: list[RepairAttemptOutcome] = Field(default=[])
    who_initiated_repairs: Literal["partner_a", "partner_b", "both", "neither"]
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
    resolution_status: Literal["resolved", "unresolved", "temporary_truce"]
    what_resolved_it: Optional[str] = Field(
        default=None,
        description="If resolved, what worked"
    )
    what_remains_unresolved: Optional[str] = Field(
        default=None,
        description="Issues still open"
    )

    # === LEARNINGS ===
    phrases_to_avoid: list[str] = Field(
        default=[],
        description="Things said that made it worse",
        max_length=5
    )
    phrases_that_helped: list[str] = Field(
        default=[],
        description="Things said that helped",
        max_length=5
    )
    unmet_needs_partner_a: list[str] = Field(
        default=[],
        max_length=3
    )
    unmet_needs_partner_b: list[str] = Field(
        default=[],
        max_length=3
    )

    what_would_have_helped: str = Field(
        description="What could have prevented escalation or resolved faster"
    )

    # === CONNECTION TO PAST ===
    similar_to_past_topics: list[str] = Field(
        default=[],
        description="Topics from past fights this resembles"
    )
    recurring_pattern_detected: Optional[str] = Field(
        default=None,
        description="If this fight follows a pattern seen before"
    )
```

---

## Phase 4: Cross-Fight Intelligence

```python
class EscalationTrigger(BaseModel):
    """A phrase/behavior that consistently escalates fights"""

    trigger: str = Field(description="The phrase or behavior")
    occurrences: int = Field(description="How many fights this appeared in")
    escalation_rate: float = Field(
        ge=0.0, le=1.0,
        description="Percentage of times it escalated"
    )
    examples: list[str] = Field(
        max_length=3,
        description="Specific examples from transcripts"
    )
    confidence: Literal["high", "medium", "low"]


class DeescalationTechnique(BaseModel):
    """A phrase/behavior that consistently helps"""

    technique: str = Field(description="The phrase or behavior")
    occurrences: int
    success_rate: float = Field(
        ge=0.0, le=1.0,
        description="Percentage of times it helped"
    )
    examples: list[str] = Field(max_length=3)
    who_uses_it: Literal["partner_a", "partner_b", "both"]


class RecurringTopic(BaseModel):
    """A topic that keeps coming up across fights"""

    topic: str
    fight_count: int
    first_seen: str  # Date string
    last_seen: str   # Date string
    ever_resolved: bool
    resolution_attempts: int = 0


class RepairStrategyOutcome(BaseModel):
    """Tracking if a repair strategy works across fights"""

    strategy: str = Field(
        description="e.g., 'waiting 20 minutes', 'making tea'"
    )
    times_tried: int
    times_worked: int
    success_rate: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(
        max_length=3,
        description="What happened after using this strategy"
    )


class RelationshipPatterns(BaseModel):
    """Aggregated patterns across all fights for a relationship"""

    relationship_id: str
    last_updated: datetime
    total_fights_analyzed: int

    # What to avoid
    escalation_triggers: list[EscalationTrigger] = Field(
        default=[],
        max_length=10
    )

    # What works
    deescalation_techniques: list[DeescalationTechnique] = Field(
        default=[],
        max_length=10
    )

    # Topics
    recurring_topics: list[RecurringTopic] = Field(
        default=[],
        max_length=10
    )
    unresolved_issues: list[str] = Field(
        default=[],
        max_length=5
    )

    # Repair strategy effectiveness
    repair_strategies: list[RepairStrategyOutcome] = Field(
        default=[],
        max_length=10
    )

    # Meta-patterns
    who_usually_initiates_repair: Literal["partner_a", "partner_b", "both", "neither"]
    who_usually_escalates: Literal["partner_a", "partner_b", "both", "neither"]
    average_fight_intensity: Literal["low", "medium", "high"]
    typical_resolution_time: str = Field(
        description="'same day', 'next day', 'days later', 'often unresolved'"
    )


class RepairPlanOutcomeInference(BaseModel):
    """Inferred outcome of a past repair plan (no user feedback needed)"""

    conflict_id: str
    repair_plan_date: datetime

    outcome: Literal["worked", "partially_worked", "didnt_work", "unclear"]
    confidence: Literal["high", "medium", "low"]

    evidence: list[str] = Field(
        description="Data points that led to this conclusion"
    )
    reasoning: str = Field(
        description="Explanation of the inference"
    )
```

---

## Helper Models

```python
class ProfileCompleteness(BaseModel):
    """Track how complete a partner's profile is"""

    partner_id: str
    total_fields: int
    completed_fields: int
    completeness_percentage: float

    missing_critical: list[str] = Field(
        description="Critical fields for repair plans that are missing"
    )
    missing_optional: list[str] = Field(
        description="Optional fields that are missing"
    )


class RepairPlanContext(BaseModel):
    """Full context bundle for repair plan generation"""

    # Profiles
    partner_a_profile: PartnerProfile
    partner_b_profile: PartnerProfile

    # Current fight
    current_fight: FightDebrief

    # Historical
    relationship_patterns: Optional[RelationshipPatterns] = None
    similar_past_fights: list[FightDebrief] = Field(default=[])

    # Calendar (if available)
    calendar_context: Optional[str] = None
```

---

## Validation Helpers

```python
def validate_repair_plan_citations(plan: PersonalizedRepairPlan) -> list[str]:
    """Check that repair plan has required citations"""

    issues = []

    # Check timing citation
    if not plan.timing_citation:
        issues.append("Missing timing citation")

    # Check step citations
    for i, step in enumerate(plan.steps):
        if not step.citation_detail:
            issues.append(f"Step {i+1} missing citation")

    # Check avoidance citations
    for i, item in enumerate(plan.things_to_avoid):
        if not item.citation_detail:
            issues.append(f"Avoidance {i+1} missing citation")

    # Check gesture citation
    if not plan.gesture_citation:
        issues.append("Missing gesture citation")

    return issues


def calculate_personalization_score(plan: PersonalizedRepairPlan) -> Literal["high", "medium", "low"]:
    """Calculate personalization score based on citations"""

    issues = validate_repair_plan_citations(plan)

    if len(issues) == 0:
        return "high"
    elif len(issues) <= 2:
        return "medium"
    else:
        return "low"
```

---

## Database Schema Mapping

| Pydantic Model | PostgreSQL Table | Pinecone Namespace |
|----------------|------------------|-------------------|
| PartnerProfile | partners | profiles |
| PersonalizedRepairPlan | repair_plans | repair_plans |
| FightDebrief | fight_debriefs | fight_debriefs |
| RelationshipPatterns | relationship_patterns | - |
| RepairPlanOutcomeInference | repair_outcomes | - |
