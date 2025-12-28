# Phase 3: Fight Debrief System

## Goal

After every fight, run a comprehensive LLM analysis that extracts:
1. Repair attempts and whether they worked
2. Escalation triggers specific to this fight
3. What would have helped
4. Resolution status

Store this as a `FightDebrief` - a structured record that future repair plans can reference.

---

## Core Concept: Fight Debrief

Instead of storing raw transcripts and re-analyzing them, we extract insights ONCE and store structured data.

```
┌─────────────────────────────────────────────────────────────────┐
│                         FIGHT DEBRIEF                            │
│                   (Generated after each fight)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  WHAT HAPPENED                                                   │
│  ├── Topic, summary, duration, intensity                        │
│  └── Key quotes and moments                                      │
│                                                                  │
│  REPAIR DYNAMICS                                                 │
│  ├── Repair attempts (who, what, when)                          │
│  ├── Outcome of each attempt (helped/hurt/neutral)              │
│  └── Most effective / most damaging moments                     │
│                                                                  │
│  LEARNINGS                                                       │
│  ├── Phrases that escalated                                     │
│  ├── Phrases that helped                                        │
│  ├── Unmet needs identified                                     │
│  └── What would have helped (LLM assessment)                    │
│                                                                  │
│  RESOLUTION                                                      │
│  ├── Status: resolved / unresolved / temporary_truce            │
│  ├── What resolved it (if applicable)                           │
│  └── What remains unresolved                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Pydantic Models

### RepairAttemptOutcome

```python
class RepairAttemptOutcome(BaseModel):
    """A single repair attempt and its outcome"""
    timestamp: str = Field(description="Approximate time in transcript, e.g., '3:42'")
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
    what_they_said_or_did: str = Field(description="Quote or description")

    # What happened next
    outcome: Literal["helped", "hurt", "neutral"]
    outcome_evidence: str = Field(
        description="What happened in the next 30-60 seconds that tells us the outcome"
    )

    # Learnings
    why_it_worked_or_failed: str = Field(
        description="LLM's assessment of why this attempt had this outcome"
    )
```

### FightDebrief

```python
class FightDebrief(BaseModel):
    """Comprehensive post-fight analysis - generated once per fight"""
    conflict_id: str
    relationship_id: str
    analyzed_at: datetime

    # === WHAT HAPPENED ===
    topic: str = Field(description="Main topic/issue, 2-5 words")
    summary: str = Field(description="What happened in 2-3 sentences")
    duration_estimate: str = Field(description="e.g., '15 minutes', '1 hour'")
    intensity_peak: Literal["low", "medium", "high", "explosive"]

    key_moments: list[str] = Field(
        description="3-5 pivotal moments with timestamps",
        min_length=1,
        max_length=5
    )

    # === REPAIR DYNAMICS ===
    repair_attempts: list[RepairAttemptOutcome]
    who_initiated_repairs: Literal["partner_a", "partner_b", "both", "neither"]
    total_repair_attempts: int
    successful_repairs: int
    failed_repairs: int

    most_effective_moment: Optional[str] = Field(
        description="The moment that helped most, with quote"
    )
    most_damaging_moment: Optional[str] = Field(
        description="The moment that hurt most, with quote"
    )

    # === RESOLUTION ===
    resolution_status: Literal["resolved", "unresolved", "temporary_truce"]
    what_resolved_it: Optional[str] = Field(
        description="If resolved, what worked"
    )
    what_remains_unresolved: Optional[str] = Field(
        description="Issues still open"
    )

    # === LEARNINGS (for future repair plans) ===
    phrases_to_avoid: list[str] = Field(
        description="Things said that made it worse",
        max_length=5
    )
    phrases_that_helped: list[str] = Field(
        description="Things said that helped",
        max_length=5
    )
    unmet_needs_partner_a: list[str] = Field(max_length=3)
    unmet_needs_partner_b: list[str] = Field(max_length=3)

    what_would_have_helped: str = Field(
        description="LLM's assessment: what could have prevented escalation or resolved it faster"
    )

    # === CONNECTION TO PAST ===
    similar_to_past_topics: list[str] = Field(
        default=[],
        description="Topics from past fights this resembles"
    )
    recurring_pattern_detected: Optional[str] = Field(
        description="If this fight follows a pattern seen before"
    )
```

---

## LLM Prompt for Fight Debrief

```python
def generate_fight_debrief(
    self,
    transcript_text: str,
    conflict_id: str,
    relationship_id: str,
    partner_a_name: str,
    partner_b_name: str,
    partner_a_profile: str,
    partner_b_profile: str,
    past_fight_summaries: Optional[list[str]] = None,
    response_model: Type[T] = FightDebrief
) -> T:
    """Generate comprehensive fight debrief"""

    past_context = ""
    if past_fight_summaries:
        past_context = f"""
=== PAST FIGHT SUMMARIES (for pattern detection) ===
{chr(10).join(past_fight_summaries)}
"""

    prompt = f"""Analyze this conflict comprehensively to create a Fight Debrief.

=== PARTNER PROFILES ===

{partner_a_name} (Partner A):
{partner_a_profile}

{partner_b_name} (Partner B):
{partner_b_profile}

{past_context}

=== CURRENT FIGHT TRANSCRIPT ===
{transcript_text}

=== ANALYSIS REQUIREMENTS ===

1. **REPAIR ATTEMPTS**: Identify EVERY moment where someone tried to:
   - Apologize or take responsibility
   - Validate the other's feelings
   - De-escalate with humor or affection
   - Suggest a break or redirect
   - Offer a solution

   For EACH attempt, analyze:
   - What did they say/do? (quote if possible)
   - What happened in the next 30-60 seconds?
   - Did it HELP (things calmed), HURT (things escalated), or have NO EFFECT?
   - WHY did it have that outcome? (consider their profiles)

2. **ESCALATION TRIGGERS**: What phrases or moments made things WORSE?
   - Quote specific phrases
   - Note who said them and when
   - These will be added to "things to avoid" in future repair plans

3. **DE-ESCALATION SUCCESSES**: What helped?
   - Quote specific phrases or actions
   - Note who did them and when
   - These will be recommended in future repair plans

4. **UNMET NEEDS**: What did each partner need but not get?
   - Reference their profile (communication style, stress triggers)
   - Be specific to THIS conflict

5. **RESOLUTION STATUS**:
   - RESOLVED: Issue was genuinely addressed, both partners satisfied
   - TEMPORARY_TRUCE: Conflict stopped but issue not addressed
   - UNRESOLVED: Still actively upset or issue explicitly open

6. **PATTERN DETECTION**: If past fight summaries provided:
   - Is this topic recurring?
   - Is the dynamic similar to past fights?
   - Are the same triggers appearing?

Be specific. Use quotes. Reference profiles. This analysis will inform future repair plans.
"""

    return self.structured_output(
        messages=[{"role": "user", "content": prompt}],
        response_model=response_model,
        temperature=0.5,  # Lower temp for analysis
        max_tokens=3000
    )
```

---

## When to Generate Fight Debrief

Add to the post-fight analysis pipeline:

```python
# backend/app/routes/post_fight.py

async def analyze_conflict(conflict_id: str, relationship_id: str, transcript: str):
    """Main post-fight analysis endpoint"""

    # Existing: Conflict analysis, Gottman analysis
    # ...

    # NEW: Generate Fight Debrief
    fight_debrief = await llm_service.generate_fight_debrief(
        transcript_text=transcript,
        conflict_id=conflict_id,
        relationship_id=relationship_id,
        partner_a_name=partner_a_name,
        partner_b_name=partner_b_name,
        partner_a_profile=partner_a_formatted,
        partner_b_profile=partner_b_formatted,
        past_fight_summaries=get_past_fight_summaries(relationship_id, limit=5)
    )

    # Store the debrief
    await store_fight_debrief(fight_debrief)

    # Continue with repair plan generation...
    # Now repair plan can reference this debrief
```

---

## Storage

### Option A: PostgreSQL (Recommended for structured queries)

```sql
CREATE TABLE fight_debriefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conflict_id UUID REFERENCES conflicts(id),
    relationship_id UUID REFERENCES relationships(id),
    analyzed_at TIMESTAMP DEFAULT NOW(),

    -- Core data
    topic VARCHAR(100),
    summary TEXT,
    duration_estimate VARCHAR(50),
    intensity_peak VARCHAR(20),
    resolution_status VARCHAR(20),

    -- JSON fields for complex data
    repair_attempts JSONB,  -- Array of RepairAttemptOutcome
    key_moments JSONB,      -- Array of strings
    phrases_to_avoid JSONB,
    phrases_that_helped JSONB,
    unmet_needs_partner_a JSONB,
    unmet_needs_partner_b JSONB,

    -- Text fields
    most_effective_moment TEXT,
    most_damaging_moment TEXT,
    what_resolved_it TEXT,
    what_remains_unresolved TEXT,
    what_would_have_helped TEXT,
    recurring_pattern_detected TEXT,

    -- Indexing
    CONSTRAINT fk_conflict FOREIGN KEY (conflict_id) REFERENCES conflicts(id)
);

CREATE INDEX idx_debriefs_relationship ON fight_debriefs(relationship_id);
CREATE INDEX idx_debriefs_topic ON fight_debriefs(topic);
```

### Option B: Pinecone (For semantic search across debriefs)

Store the full debrief as a vector for semantic retrieval:

```python
async def store_fight_debrief(debrief: FightDebrief):
    # Create embedding from summary + learnings
    embedding_text = f"""
    Topic: {debrief.topic}
    Summary: {debrief.summary}
    Phrases to avoid: {', '.join(debrief.phrases_to_avoid)}
    Phrases that helped: {', '.join(debrief.phrases_that_helped)}
    Unmet needs: {', '.join(debrief.unmet_needs_partner_a + debrief.unmet_needs_partner_b)}
    """

    embedding = embeddings_service.embed(embedding_text)

    pinecone_service.upsert(
        vectors=[{
            "id": debrief.conflict_id,
            "values": embedding,
            "metadata": {
                "relationship_id": debrief.relationship_id,
                "topic": debrief.topic,
                "resolution_status": debrief.resolution_status,
                "intensity_peak": debrief.intensity_peak,
                "full_debrief_json": debrief.model_dump_json()
            }
        }],
        namespace="fight_debriefs"
    )
```

### Recommendation: Use Both

- PostgreSQL for structured queries ("all unresolved fights", "fights about chores")
- Pinecone for semantic search ("fights similar to this one")

---

## Retrieval for Repair Plans

When generating a repair plan, fetch the current fight's debrief:

```python
async def get_fight_context_for_repair(conflict_id: str) -> str:
    """Get debrief context formatted for repair plan prompt"""

    debrief = await get_fight_debrief(conflict_id)
    if not debrief:
        return ""

    return f"""
=== CURRENT FIGHT ANALYSIS ===

Topic: {debrief.topic}
Intensity: {debrief.intensity_peak}
Resolution: {debrief.resolution_status}

Repair attempts in this fight:
{format_repair_attempts(debrief.repair_attempts)}

What helped:
{chr(10).join(f'- {p}' for p in debrief.phrases_that_helped)}

What made it worse:
{chr(10).join(f'- {p}' for p in debrief.phrases_to_avoid)}

Most effective moment: {debrief.most_effective_moment}
Most damaging moment: {debrief.most_damaging_moment}

Unmet needs:
- {partner_a_name}: {', '.join(debrief.unmet_needs_partner_a)}
- {partner_b_name}: {', '.join(debrief.unmet_needs_partner_b)}

What would have helped: {debrief.what_would_have_helped}
"""
```

---

## Files to Create/Modify

| File | Changes |
|------|---------|
| `backend/app/models/schemas.py` | Add `RepairAttemptOutcome`, `FightDebrief` |
| `backend/app/services/llm_service.py` | Add `generate_fight_debrief()` method |
| `backend/app/services/debrief_service.py` | NEW: Store/retrieve debriefs |
| `backend/app/routes/post_fight.py` | Call debrief generation after analysis |
| `backend/migrations/` | Add `fight_debriefs` table |

---

## Testing Checklist

- [ ] FightDebrief generates successfully for sample transcript
- [ ] Repair attempts are identified with correct outcomes
- [ ] Phrases to avoid/that helped are specific (not generic)
- [ ] Resolution status is accurate
- [ ] Debrief stores correctly in PostgreSQL
- [ ] Debrief retrieval works for repair plan generation
- [ ] Pattern detection works when past fights provided
