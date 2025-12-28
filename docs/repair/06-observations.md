# Additional Observations & Recommendations

Issues and opportunities discovered while analyzing the codebase.

---

## Code Quality Issues

### 1. Gender Terminology Inconsistency

**Problem:** Frontend uses gender-neutral terms (`partner_a`, `partner_b`), but backend uses gendered terms (`boyfriend_profile`, `girlfriend_profile`).

**Files affected:**
- `backend/app/routes/post_fight.py` (30+ occurrences)
- `backend/app/services/llm_service.py`
- Pinecone metadata: `pdf_type: "boyfriend_profile"`

**Recommendation:** Migrate to `partner_a_profile` / `partner_b_profile` consistently.

```python
# Before
filter={"pdf_type": {"$eq": "boyfriend_profile"}}

# After
filter={"role": {"$eq": "partner_a"}}
```

### 2. Hardcoded Names in Prompts

**Problem:** LLM prompts contain hardcoded names "Adrian" and "Elara":

```python
# llm_service.py:255-258
"Profile information about Adrian and Elara..."
```

**Fix:** Use dynamic names from relationship record.

### 3. Dead Code

**Problem:** `llm_service.py` has duplicate return statement:

```python
# Lines 405-421
result = self.structured_output(...)
elapsed = __import__('time').time() - start_time
logger.info(f"✅ Repair plan complete in {elapsed:.2f}s")
return result  # First return

return self.structured_output(...)  # Dead code - never reached
```

**Fix:** Remove lines 416-421.

### 4. No Profile Existence Validation

**Problem:** Repair plan generation proceeds even with empty profiles.

```python
# Current
if reranked_bf:
    boyfriend_profile = "\n\n".join([...])
# boyfriend_profile is None if no results - no warning, generic plan generated
```

**Fix:** Add explicit validation and fallback messaging.

---

## Architecture Recommendations

### 1. Separate Profile Storage from RAG

**Current:** Profiles stored in Pinecone, retrieved via semantic search.

**Problem:** Semantic search by transcript misses repair-relevant data.

**Recommendation:**
- Store complete profiles in PostgreSQL (structured)
- Use Pinecone only for semantic search over transcripts/debriefs
- Fetch ALL profile data for repair plans (no RAG)

### 2. Add Profile Versioning

**Problem:** If a user updates their profile, old repair plans reference outdated data.

**Recommendation:** Store profile snapshot with each repair plan:

```python
class PersonalizedRepairPlan(BaseModel):
    # ...
    profile_snapshot: dict = Field(
        description="Copy of profiles at generation time"
    )
```

### 3. Decouple Analysis from Repair Plans

**Current:** Repair plans generated immediately after fight analysis.

**Problem:**
- User might not want repair plan right away
- Both partners get repair plans simultaneously (awkward)

**Recommendation:**
- Generate FightDebrief automatically
- Repair plan generation is on-demand per partner
- "Generate my repair plan" button for each partner

---

## UX Recommendations

### 1. Show Data Sources

**Problem:** Users don't know what data influenced suggestions.

**Recommendation:** Add "Why this suggestion?" expandable:

```
Step 2: Wait 20 minutes before approaching

[Why?]
- Sarah's profile says she needs space after conflicts
- In this fight, she said "I need to think" at 3:42
- Waiting worked in 3 of your last 4 fights
```

### 2. Profile Completeness Indicator

Show users what's missing:

```
Profile Completeness: 75%
━━━━━━━━━━━━━━━━░░░░

Missing for better repair plans:
• What makes apologies genuine to you
• What small gestures help after fights
```

### 3. Invite Partner Flow

When repair plan is blocked due to missing partner profile:

```
┌─────────────────────────────────────────┐
│  Personalized repair plans need both    │
│  partners' profiles.                    │
│                                         │
│  Sarah hasn't completed hers yet.       │
│                                         │
│  [Send Invite Link]  [Remind Later]     │
└─────────────────────────────────────────┘
```

### 4. Pattern Insights Dashboard

Show learned patterns to users:

```
What We've Learned (8 fights analyzed)

Things that help:
✓ "I hear you" - worked 3/3 times
✓ Waiting 20 min - worked 4/5 times
✓ Making tea - worked 2/2 times

Things to avoid:
✗ "Calm down" - escalated 4/4 times
✗ Bringing up past issues - escalated 3/3 times

Recurring topics (still unresolved):
• Division of chores (5 fights)
• Feeling unappreciated (3 fights)
```

---

## Performance Considerations

### 1. Pattern Aggregation Caching

Don't re-aggregate patterns on every repair plan request:

```python
async def get_relationship_patterns(relationship_id: str) -> RelationshipPatterns:
    # Check cache first
    cached = await cache.get(f"patterns:{relationship_id}")
    if cached and cached.last_updated > (now - timedelta(hours=1)):
        return cached

    # Re-aggregate if stale or missing
    patterns = await aggregate_patterns(relationship_id)
    await cache.set(f"patterns:{relationship_id}", patterns, ttl=3600)
    return patterns
```

### 2. Lazy Pattern Aggregation

Only re-aggregate when new fight is added, not on every request:

```python
async def on_new_fight_debrief(relationship_id: str):
    # Invalidate cache
    await cache.delete(f"patterns:{relationship_id}")

    # Optionally pre-warm in background
    asyncio.create_task(aggregate_patterns(relationship_id))
```

### 3. Limit Historical Context

Don't pass 50 fight debriefs to the LLM. Use:
- Last 5-10 debriefs for pattern aggregation
- Top 3 similar fights for repair plan context
- Aggregated patterns (already compressed)

---

## Testing Strategy

### Unit Tests Needed

```python
def test_repair_plan_has_citations():
    """Every repair plan step must have a citation"""
    plan = generate_repair_plan(...)
    issues = validate_repair_plan_citations(plan)
    assert len(issues) == 0

def test_fight_debrief_detects_repair_attempts():
    """Debrief should identify repair attempts in transcript"""
    transcript = "... I'm sorry, I didn't mean that ..."
    debrief = generate_fight_debrief(transcript, ...)
    assert len(debrief.repair_attempts) > 0

def test_pattern_aggregation_requires_minimum_fights():
    """Need at least 3 fights to detect patterns"""
    patterns = aggregate_patterns(relationship_with_2_fights)
    assert patterns.total_fights_analyzed == 2
    assert len(patterns.escalation_triggers) == 0  # Not enough data

def test_similar_fight_retrieval_excludes_current():
    """Don't return the current fight as 'similar'"""
    similar = find_similar_past_fights(current_conflict_id, ...)
    assert current_conflict_id not in [f.conflict_id for f in similar]
```

### Integration Tests Needed

```python
def test_full_repair_plan_pipeline():
    """End-to-end test: onboarding → fight → debrief → repair plan"""
    # 1. Complete onboarding for both partners
    # 2. Record a fight
    # 3. Generate debrief
    # 4. Generate repair plan
    # 5. Verify repair plan references profile data

def test_pattern_learning_over_multiple_fights():
    """Patterns should emerge after 3+ fights"""
    # 1. Record 3 fights with same escalation trigger
    # 2. Aggregate patterns
    # 3. Verify trigger appears with correct frequency
    # 4. Generate repair plan
    # 5. Verify "things to avoid" includes the trigger
```

---

## Migration Path

If implementing on existing data:

### 1. Backfill Fight Debriefs

```python
async def backfill_debriefs():
    """Generate debriefs for existing conflicts"""
    conflicts = await get_all_conflicts_without_debriefs()

    for conflict in conflicts:
        transcript = await get_transcript(conflict.id)
        debrief = await generate_fight_debrief(transcript, ...)
        await store_fight_debrief(debrief)
```

### 2. Migrate Profile Storage

```python
async def migrate_profiles():
    """Move profiles from Pinecone-only to PostgreSQL + Pinecone"""
    relationships = await get_all_relationships()

    for rel in relationships:
        # Fetch from Pinecone
        profile_chunks = await fetch_all_profile_chunks(rel.id)

        # Reconstruct and store in PostgreSQL
        profile = reconstruct_profile(profile_chunks)
        await store_profile_postgres(profile)
```

### 3. Initial Pattern Aggregation

```python
async def initial_pattern_aggregation():
    """Generate initial patterns for all relationships with 3+ fights"""
    relationships = await get_relationships_with_min_fights(3)

    for rel in relationships:
        debriefs = await get_all_debriefs(rel.id)
        patterns = await aggregate_patterns(rel.id, debriefs)
        await store_patterns(patterns)
```
