# Phase 1: Data Capture & Enrichment

**Goal**: Capture richer conflict metadata to enable trigger and escalation analysis

**Timeline**: 1-2 weeks

**Deliverables**:
- Database schema updates
- Enhanced LLM analysis prompts
- Trigger phrase extraction logic

---

## 1.1 Database Schema Changes

### Add to `conflicts` table

```sql
ALTER TABLE conflicts ADD COLUMN (
  -- Conflict Relationships
  parent_conflict_id UUID REFERENCES conflicts(id),
  is_continuation BOOLEAN DEFAULT FALSE,
  days_since_related_conflict INT,

  -- Emotional Context
  resentment_level INT CHECK (resentment_level >= 1 AND resentment_level <= 10),
  unmet_needs TEXT[], -- e.g., ['feeling_heard', 'trust', 'appreciation']

  -- Analysis Flags
  has_past_references BOOLEAN DEFAULT FALSE,
  conflict_chain_id UUID -- groups related conflicts together
);

-- Index for fast lookups
CREATE INDEX idx_parent_conflict_id ON conflicts(parent_conflict_id);
CREATE INDEX idx_conflict_chain_id ON conflicts(conflict_chain_id);
```

### Create `trigger_phrases` table

```sql
CREATE TABLE trigger_phrases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  relationship_id UUID NOT NULL REFERENCES relationships(id),

  -- Phrase Content
  phrase TEXT NOT NULL,
  phrase_category VARCHAR(50), -- 'temporal_reference', 'passive_aggressive', 'blame', 'dismissal', etc.

  -- Context
  conflict_id UUID NOT NULL REFERENCES conflicts(id),
  speaker VARCHAR(50), -- 'partner_a' or 'partner_b'
  timestamp INT, -- seconds into transcript where phrase appears
  full_sentence TEXT, -- full sentence context

  -- Analysis
  emotional_intensity INT CHECK (emotional_intensity >= 1 AND emotional_intensity <= 10),
  references_past_conflict BOOLEAN DEFAULT FALSE,
  past_conflict_id UUID REFERENCES conflicts(id),

  -- Tracking
  frequency INT DEFAULT 1, -- how many times used across all conflicts
  last_used_at TIMESTAMP,
  is_pattern_trigger BOOLEAN DEFAULT FALSE, -- does this lead to escalation?
  escalation_correlation DECIMAL(3,2), -- 0.0-1.0, how often does this trigger big fights?

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_trigger_relationship ON trigger_phrases(relationship_id);
CREATE INDEX idx_trigger_conflict ON trigger_phrases(conflict_id);
CREATE INDEX idx_trigger_phrase ON trigger_phrases(phrase);
CREATE INDEX idx_is_pattern_trigger ON trigger_phrases(is_pattern_trigger);
```

### Create `unmet_needs` table

```sql
CREATE TABLE unmet_needs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  relationship_id UUID NOT NULL REFERENCES relationships(id),
  conflict_id UUID NOT NULL REFERENCES conflicts(id),

  need VARCHAR(100), -- 'feeling_heard', 'trust', 'appreciation', 'respect', 'autonomy', etc.
  identified_by VARCHAR(50), -- 'gpt_analysis' or 'manual'
  confidence DECIMAL(3,2), -- 0.0-1.0

  -- Track recurrence
  first_identified_at TIMESTAMP,
  times_identified INT DEFAULT 1,
  is_chronic BOOLEAN DEFAULT FALSE, -- shows up in 3+ conflicts

  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_unmet_needs_relationship ON unmet_needs(relationship_id);
CREATE INDEX idx_unmet_needs_chronic ON unmet_needs(is_chronic);
```

---

## 1.2 LLM Analysis Enhancement

### New Prompts for Conflict Analysis

When analyzing a conflict, add these questions to GPT-4o-mini:

**Conflict Linking Analysis**

```
Analyze if this conflict is related to previous conflicts:

1. Does the transcript contain explicit references to past events/conflicts?
   - List any phrases like: "You didn't do that yesterday", "Like last time", "This always happens"
   - Confidence: high/medium/low

2. What underlying unmet needs are expressed?
   - Beyond the surface topic (e.g., beyond "the door")
   - List needs from: [feeling_heard, trust, appreciation, respect, autonomy, security, intimacy]
   - Confidence score for each: 0.0-1.0

3. What is the resentment level in this conflict?
   - Scale: 1-10
   - Based on: accumulated frustration, past failures to resolve, tone escalation
   - Evidence from transcript

4. Is this likely a continuation of an unresolved conflict?
   - Yes/No
   - What was the original issue?
   - Why wasn't it resolved?
```

**Trigger Phrase Extraction**

```
Extract all phrases that could be escalation triggers:

For each phrase:
1. Exact quote from transcript
2. Category: temporal_reference | passive_aggressive | blame | dismissal | threat | dismissal_of_feelings
3. Emotional intensity: 1-10
4. Does it reference a past event? (yes/no)
5. Could this phrase trigger escalation? (yes/no)

Format as JSON:
{
  "trigger_phrases": [
    {
      "phrase": "...",
      "category": "...",
      "emotional_intensity": 5,
      "references_past": true,
      "is_escalation_trigger": true
    }
  ]
}
```

---

## 1.3 Backend Implementation

### Update `conflict_analysis.py`

Add a new function to extract and store structured conflict data:

```python
async def extract_conflict_relationships(
    conflict_id: UUID,
    transcript: str,
    previous_conflicts: List[Conflict]
) -> ConflictEnrichment:
    """
    Use LLM to identify:
    - Related past conflicts
    - Trigger phrases
    - Unmet needs
    - Resentment level
    """

    # Build context of previous conflicts
    conflict_history = "\n".join([
        f"- {c.created_at}: {c.topic}"
        for c in previous_conflicts[-5:]  # last 5 conflicts
    ])

    prompt = f"""
    Analyze this conflict transcript for relationships and triggers:

    Current Conflict Transcript:
    {transcript}

    Previous Conflicts (last 5):
    {conflict_history}

    Provide analysis in JSON format with:
    1. parent_conflict_id (if related to previous)
    2. trigger_phrases (array with analysis)
    3. unmet_needs (array of needs)
    4. resentment_level (1-10)
    5. has_past_references (boolean)
    """

    response = await llm_service.analyze(prompt)
    return parse_enrichment(response)
```

### Update Conflict Storage

When storing a new conflict, call enrichment:

```python
async def store_transcript(conflict_data: ConflictCreateRequest):
    # ... existing code ...

    # NEW: Enrich with relationship data
    enrichment = await extract_conflict_relationships(
        conflict_id=conflict.id,
        transcript=transcript_text,
        previous_conflicts=await db_service.get_previous_conflicts(
            relationship_id=relationship_id,
            limit=10
        )
    )

    # Store enriched data
    await db_service.save_trigger_phrases(conflict.id, enrichment.trigger_phrases)
    await db_service.save_unmet_needs(conflict.id, enrichment.unmet_needs)
    await db_service.update_conflict(
        conflict.id,
        parent_conflict_id=enrichment.parent_conflict_id,
        resentment_level=enrichment.resentment_level,
        has_past_references=enrichment.has_past_references
    )
```

---

## 1.4 Data Models (Pydantic)

Add to `schemas.py`:

```python
class TriggerPhrase(BaseModel):
    phrase: str
    category: str  # 'temporal_reference', 'passive_aggressive', etc.
    emotional_intensity: int
    references_past: bool
    speaker: Optional[str]
    is_escalation_trigger: bool

class UnmetNeed(BaseModel):
    need: str  # 'feeling_heard', 'trust', etc.
    confidence: float
    first_identified_at: datetime

class ConflictEnrichment(BaseModel):
    parent_conflict_id: Optional[UUID]
    trigger_phrases: List[TriggerPhrase]
    unmet_needs: List[UnmetNeed]
    resentment_level: int
    has_past_references: bool
    conflict_chain_id: Optional[UUID]
```

---

## 1.5 Implementation Checklist

- [ ] Create migration file with schema changes
- [ ] Add Pydantic models for new data structures
- [ ] Write `extract_conflict_relationships()` function
- [ ] Update LLM prompts with enrichment questions
- [ ] Update conflict storage endpoint to call enrichment
- [ ] Add database helper functions for storing phrases/needs
- [ ] Test with sample transcripts
- [ ] Verify data is being captured correctly
- [ ] Document new database fields

---

## 1.6 Testing Strategy

### Unit Tests

```python
# Test trigger phrase extraction
def test_extract_temporal_references():
    transcript = "You didn't do that yesterday. You didn't wash the dishes yesterday."
    enrichment = extract_conflict_relationships(...)
    assert len(enrichment.trigger_phrases) > 0
    assert "temporal_reference" in [p.category for p in enrichment.trigger_phrases]

# Test resentment scoring
def test_resentment_level_with_multiple_unresolved():
    # Conflict with many unmet needs should have higher resentment
    assert enrichment.resentment_level >= 7
```

### Integration Tests

1. Store a conflict with no previous conflicts → should have empty parent_conflict_id
2. Store a conflict that references previous → should link correctly
3. Store trigger phrases → verify they're queryable
4. Retrieve conflict with enrichment → all fields present

### Manual Testing

1. Upload a real transcript with explicit past references
2. Verify trigger phrases are extracted accurately
3. Check unmet needs are identified
4. Confirm resentment level makes sense

---

## 1.7 Success Criteria

- All new conflicts capture: parent_conflict_id, resentment_level, trigger_phrases, unmet_needs
- Trigger phrases are extracted with >80% accuracy (manual verification)
- LLM correctly identifies temporal references (e.g., "yesterday", "last time")
- Unmet needs are identified with reasonable confidence scores
- No breaking changes to existing conflict storage

---

## Next Steps

Once Phase 1 is complete, proceed to **Phase 2: Intelligence & Pattern Detection** to build analytics on top of this enriched data.
