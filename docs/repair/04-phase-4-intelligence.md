# Phase 4: Cross-Fight Intelligence

## Goal

Aggregate learnings across ALL past fights to provide:
1. **Pattern detection** - What consistently works/fails
2. **Similar fight retrieval** - Past fights with similar dynamics
3. **Repair outcome inference** - Did previous repair plans work?

This is where the system gets smarter over time without user feedback.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    CROSS-FIGHT INTELLIGENCE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │  FIGHT DEBRIEFS  │───▶│  PATTERN         │                   │
│  │  (from Phase 3)  │    │  AGGREGATION     │                   │
│  └──────────────────┘    │  (LLM-driven)    │                   │
│                          └────────┬─────────┘                   │
│                                   │                              │
│                                   ▼                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                RELATIONSHIP PATTERNS                       │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ Escalation Triggers    │ "calm down" → escalated 4/4     │  │
│  │ De-escalation Wins     │ "I hear you" → helped 3/3       │  │
│  │ Recurring Topics       │ chores (5 fights), money (3)    │  │
│  │ Repair Success Rates   │ waiting 20 min → worked 4/5     │  │
│  │ Unresolved Issues      │ chores still unresolved         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │  CURRENT FIGHT   │───▶│  SIMILAR FIGHT   │                   │
│  │  TOPIC/DYNAMICS  │    │  RETRIEVAL       │                   │
│  └──────────────────┘    └────────┬─────────┘                   │
│                                   │                              │
│                                   ▼                              │
│  "Dec 15 fight was similar. Repair plan suggested waiting.      │
│   Outcome: No recurrence for 2 weeks → likely worked."          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Pattern Aggregation

### When to Run

After storing a new FightDebrief, trigger pattern re-aggregation:

```python
async def on_new_fight_debrief(relationship_id: str, new_debrief: FightDebrief):
    """Called after each new fight debrief is stored"""

    # Get all debriefs for this relationship
    all_debriefs = await get_all_fight_debriefs(relationship_id)

    if len(all_debriefs) >= 3:  # Need at least 3 fights for patterns
        # Re-aggregate patterns
        patterns = await aggregate_relationship_patterns(relationship_id, all_debriefs)
        await store_relationship_patterns(relationship_id, patterns)
```

### Pydantic Models

```python
class EscalationTrigger(BaseModel):
    """A phrase/behavior that consistently escalates"""
    trigger: str = Field(description="The phrase or behavior")
    occurrences: int = Field(description="How many fights this appeared in")
    escalation_rate: float = Field(description="% of times it escalated (0.0-1.0)")
    examples: list[str] = Field(
        description="Specific examples from transcripts",
        max_length=3
    )
    confidence: Literal["high", "medium", "low"]


class DeescalationTechnique(BaseModel):
    """A phrase/behavior that consistently helps"""
    technique: str = Field(description="The phrase or behavior")
    occurrences: int
    success_rate: float = Field(description="% of times it helped (0.0-1.0)")
    examples: list[str] = Field(max_length=3)
    who_uses_it: Literal["partner_a", "partner_b", "both"]


class RecurringTopic(BaseModel):
    """A topic that keeps coming up"""
    topic: str
    fight_count: int
    first_seen: str  # Date
    last_seen: str   # Date
    ever_resolved: bool
    resolution_attempts: int


class RepairStrategyOutcome(BaseModel):
    """Tracking if a repair strategy works"""
    strategy: str = Field(description="e.g., 'waiting 20 minutes', 'making tea'")
    times_tried: int
    times_worked: int
    success_rate: float
    evidence: list[str] = Field(
        description="What happened after using this strategy",
        max_length=3
    )


class RelationshipPatterns(BaseModel):
    """Aggregated patterns across all fights for a relationship"""
    relationship_id: str
    last_updated: datetime
    total_fights_analyzed: int

    # What to avoid
    escalation_triggers: list[EscalationTrigger] = Field(max_length=10)

    # What works
    deescalation_techniques: list[DeescalationTechnique] = Field(max_length=10)

    # Topics
    recurring_topics: list[RecurringTopic] = Field(max_length=10)
    unresolved_issues: list[str] = Field(max_length=5)

    # Repair strategy effectiveness
    repair_strategies: list[RepairStrategyOutcome] = Field(max_length=10)

    # Meta-patterns
    who_usually_initiates_repair: Literal["partner_a", "partner_b", "both", "neither"]
    who_usually_escalates: Literal["partner_a", "partner_b", "both", "neither"]
    average_fight_intensity: Literal["low", "medium", "high"]
    typical_resolution_time: str  # "same day", "next day", "days later", "often unresolved"
```

### LLM Prompt for Pattern Aggregation

```python
def aggregate_relationship_patterns(
    self,
    relationship_id: str,
    fight_debriefs: list[FightDebrief],
    partner_a_name: str,
    partner_b_name: str,
    response_model: Type[T] = RelationshipPatterns
) -> T:
    """Analyze all fights to find patterns"""

    debriefs_json = [d.model_dump() for d in fight_debriefs]

    prompt = f"""Analyze these {len(fight_debriefs)} fights to identify patterns for this couple.

=== FIGHT DEBRIEFS ===
{json.dumps(debriefs_json, indent=2, default=str)}

=== PATTERN DETECTION REQUIREMENTS ===

1. **ESCALATION TRIGGERS**: Find phrases/behaviors that CONSISTENTLY made things worse.
   - Only include if appeared in 2+ fights
   - Calculate escalation_rate = times_escalated / times_appeared
   - Confidence: high (3+ occurrences, >80% rate), medium (2+ occurrences, >60% rate), low (other)

2. **DE-ESCALATION TECHNIQUES**: Find what CONSISTENTLY helped.
   - Only include if worked in 2+ fights
   - Calculate success_rate = times_helped / times_tried
   - Note who uses this technique (partner_a, partner_b, both)

3. **RECURRING TOPICS**: Topics that keep coming up.
   - Note if ever resolved or still active
   - Track first/last seen

4. **REPAIR STRATEGIES**: Which repair approaches have worked?
   - "Waiting before talking" - what's the success rate?
   - "Physical affection" - does it help or hurt?
   - "Apologizing immediately" - effective or not?
   - Base on actual repair attempts from debriefs

5. **META-PATTERNS**:
   - Who usually tries to repair first?
   - Who usually escalates?
   - What's the typical intensity level?
   - How long do conflicts usually last?

=== OUTPUT REQUIREMENTS ===

- Only include patterns with 2+ data points
- Include specific examples/quotes where available
- Be concrete, not generic
- This data will be injected into future repair plans

Partner A = {partner_a_name}
Partner B = {partner_b_name}
"""

    return self.structured_output(
        messages=[{"role": "user", "content": prompt}],
        response_model=response_model,
        temperature=0.3,  # Low temp for analytical task
        max_tokens=3000
    )
```

---

## Part 2: Similar Fight Retrieval

When a new fight happens, find past fights with similar dynamics.

### Semantic Search

```python
async def find_similar_past_fights(
    relationship_id: str,
    current_fight_summary: str,
    current_topic: str,
    limit: int = 3
) -> list[FightDebrief]:
    """Find past fights similar to the current one"""

    # Embed current fight summary
    query_embedding = embeddings_service.embed(
        f"Topic: {current_topic}. Summary: {current_fight_summary}"
    )

    # Search past debriefs
    results = pinecone_service.query(
        query_vector=query_embedding,
        namespace="fight_debriefs",
        filter={"relationship_id": {"$eq": relationship_id}},
        top_k=limit + 1,  # +1 in case current fight is in results
        include_metadata=True
    )

    similar_fights = []
    for match in results:
        # Skip if it's the current fight
        if match.id == current_conflict_id:
            continue

        debrief_json = match.metadata.get("full_debrief_json")
        if debrief_json:
            debrief = FightDebrief.model_validate_json(debrief_json)
            similar_fights.append(debrief)

    return similar_fights[:limit]
```

### Formatting for Repair Plan

```python
def format_similar_fights_for_prompt(similar_fights: list[FightDebrief]) -> str:
    """Format similar past fights for repair plan prompt"""

    if not similar_fights:
        return ""

    sections = ["=== SIMILAR PAST FIGHTS ===\n"]

    for i, fight in enumerate(similar_fights, 1):
        section = f"""
Fight {i}: {fight.topic} ({fight.analyzed_at.strftime('%b %d')})
- Summary: {fight.summary}
- Intensity: {fight.intensity_peak}
- Resolution: {fight.resolution_status}
- What helped: {', '.join(fight.phrases_that_helped) or 'Nothing notable'}
- What made it worse: {', '.join(fight.phrases_to_avoid) or 'Nothing notable'}
- Most effective moment: {fight.most_effective_moment or 'N/A'}
"""
        sections.append(section)

    return "\n".join(sections)
```

---

## Part 3: Repair Outcome Inference

Determine if a past repair plan worked WITHOUT asking the user.

### Inference Logic

```python
class RepairPlanOutcomeInference(BaseModel):
    """Inferred outcome of a past repair plan"""
    conflict_id: str
    repair_plan_date: datetime

    outcome: Literal["worked", "partially_worked", "didnt_work", "unclear"]
    confidence: Literal["high", "medium", "low"]

    evidence: list[str]
    reasoning: str


async def infer_repair_plan_outcome(
    conflict_id: str,
    relationship_id: str,
    repair_plan: PersonalizedRepairPlan,
    days_to_look_ahead: int = 14
) -> RepairPlanOutcomeInference:
    """
    Infer if a repair plan worked based on what happened next.
    No user feedback required.
    """

    # Get the original fight
    original_fight = await get_fight_debrief(conflict_id)

    # Get subsequent fights
    subsequent_fights = await get_fights_after(
        relationship_id=relationship_id,
        after_conflict_id=conflict_id,
        days=days_to_look_ahead
    )

    # LLM inference
    return await llm_service.infer_repair_outcome(
        original_fight=original_fight,
        repair_plan=repair_plan,
        subsequent_fights=subsequent_fights
    )
```

### LLM Prompt for Outcome Inference

```python
def infer_repair_outcome(
    self,
    original_fight: FightDebrief,
    repair_plan: PersonalizedRepairPlan,
    subsequent_fights: list[FightDebrief],
    response_model: Type[T] = RepairPlanOutcomeInference
) -> T:
    """Infer if a repair plan worked"""

    subsequent_summaries = [
        f"- {f.analyzed_at.strftime('%b %d')}: {f.topic} ({f.resolution_status})"
        for f in subsequent_fights
    ]

    prompt = f"""Determine if this repair plan worked based on what happened afterward.

=== ORIGINAL CONFLICT ({original_fight.analyzed_at.strftime('%b %d')}) ===
Topic: {original_fight.topic}
Summary: {original_fight.summary}
Resolution at time: {original_fight.resolution_status}

=== REPAIR PLAN GIVEN ===
For: {repair_plan.requesting_partner} approaching {repair_plan.target_partner}
Timing advice: {repair_plan.when_to_approach}
Key steps: {chr(10).join(f'- {s.action}' for s in repair_plan.steps)}
Suggested gesture: {repair_plan.suggested_gesture}

=== WHAT HAPPENED IN NEXT 14 DAYS ===
Number of subsequent fights: {len(subsequent_fights)}
{chr(10).join(subsequent_summaries) if subsequent_summaries else 'No fights recorded'}

=== INFERENCE GUIDELINES ===

WORKED (high confidence):
- No fights on same topic for 10+ days
- Subsequent fights are on completely different topics
- If there was a follow-up, it was calm and constructive

PARTIALLY_WORKED (medium confidence):
- Same topic came back but less intense
- Some improvement but not fully resolved
- One partner mentioned improvement

DIDNT_WORK (high confidence):
- Same topic fight within 3 days
- Subsequent fight references "you said you would..." (broken promise)
- Escalation was similar or worse

UNCLEAR:
- Not enough subsequent data
- Topic is ambiguous
- Mixed signals

Provide your inference with specific evidence from the data.
"""

    return self.structured_output(
        messages=[{"role": "user", "content": prompt}],
        response_model=response_model,
        temperature=0.3,
        max_tokens=1000
    )
```

---

## Putting It All Together: Full Context for Repair Plan

```python
async def build_full_repair_context(
    conflict_id: str,
    relationship_id: str,
    partner_a_name: str,
    partner_b_name: str
) -> dict:
    """Build complete context for repair plan generation"""

    # Phase 2: Full profiles
    partner_a_profile = await get_full_partner_profile(relationship_id, "partner_a")
    partner_b_profile = await get_full_partner_profile(relationship_id, "partner_b")

    # Phase 3: Current fight debrief
    current_debrief = await get_fight_debrief(conflict_id)

    # Phase 4: Cross-fight intelligence
    relationship_patterns = await get_relationship_patterns(relationship_id)
    similar_fights = await find_similar_past_fights(
        relationship_id,
        current_debrief.summary,
        current_debrief.topic
    )

    # Format for prompt
    return {
        "partner_a_profile": format_profile_for_llm(partner_a_profile, partner_a_name),
        "partner_b_profile": format_profile_for_llm(partner_b_profile, partner_b_name),
        "current_fight_context": format_debrief_for_prompt(current_debrief),
        "relationship_patterns": format_patterns_for_prompt(relationship_patterns),
        "similar_fights": format_similar_fights_for_prompt(similar_fights)
    }
```

### Final Repair Plan Prompt Injection

```python
prompt = f"""Generate a personalized repair plan for {requesting_partner} to approach {target_partner}.

=== PARTNER PROFILES ===
{context["partner_a_profile"]}
{context["partner_b_profile"]}

=== CURRENT FIGHT ANALYSIS ===
{context["current_fight_context"]}

=== LEARNED PATTERNS FROM {patterns.total_fights_analyzed} PAST FIGHTS ===
{context["relationship_patterns"]}

=== SIMILAR PAST FIGHTS ===
{context["similar_fights"]}

=== REQUIREMENTS ===
...
"""
```

---

## Storage Summary

| Data | Storage | Purpose |
|------|---------|---------|
| FightDebrief | PostgreSQL + Pinecone | Per-fight analysis, semantic search |
| RelationshipPatterns | PostgreSQL | Aggregated patterns, quick lookup |
| RepairPlanOutcomeInference | PostgreSQL | Track what worked |

---

## Files to Create/Modify

| File | Changes |
|------|---------|
| `backend/app/models/schemas.py` | Add pattern models |
| `backend/app/services/llm_service.py` | Add `aggregate_relationship_patterns()`, `infer_repair_outcome()` |
| `backend/app/services/pattern_service.py` | NEW: Pattern aggregation and retrieval |
| `backend/app/services/similar_fight_service.py` | NEW: Similar fight retrieval |
| `backend/app/routes/post_fight.py` | Integrate pattern update after each fight |

---

## Testing Checklist

- [ ] Pattern aggregation runs after 3rd fight
- [ ] Escalation triggers identified with correct frequency
- [ ] De-escalation techniques identified with success rates
- [ ] Similar fight retrieval returns relevant results
- [ ] Repair outcome inference makes reasonable judgments
- [ ] Full context builds correctly for repair plan
- [ ] Repair plan references patterns and similar fights
