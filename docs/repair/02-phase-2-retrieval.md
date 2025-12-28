# Phase 2: Profile Retrieval & Prompt Rewrite

## Goal

1. Fix profile retrieval to get ALL profile data (not just semantically similar chunks)
2. Rewrite the LLM prompt to enforce explicit personalization with citations

---

## Problem: Current RAG Approach

**Current flow:**
```python
# Embed the fight transcript
query_embedding = embed(transcript)

# Query Pinecone for similar profile chunks
profile_results = pinecone_service.query(
    query_embedding,
    namespace="profiles",
    filter={"relationship_id": id, "pdf_type": "boyfriend_profile"}
)
```

**Why this fails:**

| Fight Topic | What RAG Returns | What We Actually Need |
|-------------|------------------|----------------------|
| Dishes | "frustrations about chores" | "needs space after fights", "apology preferences" |
| Feeling unheard | "communication style" | "repair gestures", "escalation triggers" |

Semantic similarity finds what's **topically related** to the fight, not what's **useful for repair**.

---

## Solution: Fetch ALL Profile Data

Profile data is small (~2-3KB per partner). No need to filter - just fetch everything.

### New Retrieval Function

```python
# backend/app/services/profile_service.py

async def get_full_partner_profile(
    relationship_id: str,
    role: Literal["partner_a", "partner_b"]
) -> Optional[dict]:
    """
    Fetch ALL profile chunks for a partner, not just semantically similar ones.
    Returns structured profile data ready for LLM consumption.
    """
    try:
        # Fetch all chunks for this partner
        results = pinecone_service.query(
            query_vector=None,  # No semantic search
            namespace="profiles",
            filter={
                "relationship_id": {"$eq": relationship_id},
                "role": {"$eq": role}
            },
            top_k=100,  # Get everything
            include_metadata=True
        )

        if not results:
            return None

        # Organize by section
        profile = {
            "identity": "",
            "background": "",
            "inner_world": "",
            "interests": "",
            "partner_view": "",
            "relationship": "",
            "repair_preferences": ""  # NEW section from Phase 1
        }

        for match in results:
            section = match.metadata.get("section", "unknown")
            if section in profile:
                profile[section] = match.metadata.get("content", "")

        return profile

    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        return None
```

### Alternative: Direct Pinecone Fetch by ID

If profiles are stored with predictable IDs:

```python
async def get_full_partner_profile(relationship_id: str, role: str) -> dict:
    """Fetch profile directly by ID pattern"""

    sections = [
        "identity", "background", "inner_world",
        "interests", "partner_view", "relationship", "repair_preferences"
    ]

    profile = {}
    ids_to_fetch = [
        f"{relationship_id}_{role}_{section}"
        for section in sections
    ]

    results = pinecone_service.fetch(ids=ids_to_fetch, namespace="profiles")

    for id, vector in results.vectors.items():
        section = id.split("_")[-1]
        profile[section] = vector.metadata.get("content", "")

    return profile
```

---

## Update Repair Plan Generation

### Current Call Site (`backend/app/routes/post_fight.py`)

```python
# BEFORE: RAG-based retrieval
query_embedding = embeddings_service.embed(transcript_text)
bf_results = pinecone_service.query(query_embedding, filter={"pdf_type": "boyfriend_profile"})
boyfriend_profile = "\n\n".join([chunk for chunk, score in reranked_bf])
```

### Updated Call Site

```python
# AFTER: Fetch ALL profile data
from app.services.profile_service import get_full_partner_profile

partner_a_profile = await get_full_partner_profile(relationship_id, "partner_a")
partner_b_profile = await get_full_partner_profile(relationship_id, "partner_b")

if not partner_a_profile or not partner_b_profile:
    return {"error": "incomplete_profiles", "missing": ...}

# Format for LLM
partner_a_formatted = format_profile_for_llm(partner_a_profile, partner_a_name)
partner_b_formatted = format_profile_for_llm(partner_b_profile, partner_b_name)
```

### Profile Formatting Function

```python
def format_profile_for_llm(profile: dict, name: str) -> str:
    """Format profile sections into LLM-ready text"""

    return f"""
=== {name.upper()}'S COMPLETE PROFILE ===

REPAIR & CONFLICT PREFERENCES (CRITICAL FOR REPAIR PLAN):
{profile.get('repair_preferences', 'Not provided')}

INNER WORLD (Communication & Triggers):
{profile.get('inner_world', 'Not provided')}

VIEW ON PARTNER:
{profile.get('partner_view', 'Not provided')}

BACKGROUND & IDENTITY:
{profile.get('identity', '')}
{profile.get('background', '')}

INTERESTS:
{profile.get('interests', 'Not provided')}
"""
```

---

## Rewrite LLM Prompt

### Current Prompt Issues (`backend/app/services/llm_service.py:367-393`)

1. Says "SPECIFIC actions" but doesn't enforce it
2. Profile data is optional context, not required input
3. No validation that output references profile data

### New Prompt Structure

```python
def generate_repair_plan(
    self,
    transcript_text: str,
    conflict_id: str,
    requesting_partner: str,  # Who wants to repair
    target_partner: str,      # Who they're approaching
    requesting_partner_profile: str,
    target_partner_profile: str,
    analysis_summary: str,
    calendar_context: Optional[str] = None,
    past_fight_context: Optional[str] = None,  # NEW: From Phase 3/4
    response_model: Type[T] = PersonalizedRepairPlan
) -> T:
    """Generate repair plan with mandatory personalization"""

    prompt = f"""Generate a PERSONALIZED repair plan for {requesting_partner} to approach {target_partner}.

=== CRITICAL: YOU MUST USE THIS PROFILE DATA ===

{target_partner_profile}

{requesting_partner_profile}

=== CURRENT CONFLICT ===

Summary: {analysis_summary}

Transcript:
{transcript_text}

{"=== CALENDAR CONTEXT ===" + chr(10) + calendar_context if calendar_context else ""}

{"=== PAST FIGHT INTELLIGENCE ===" + chr(10) + past_fight_context if past_fight_context else ""}

=== REQUIREMENTS (MANDATORY) ===

Your repair plan MUST:

1. **TIMING**: Base timing on {target_partner}'s stated post_conflict_need.
   - If they need "space": suggest waiting, specify how long
   - If they need "connection": suggest approaching soon
   - CITE their preference in your reasoning

2. **STEPS**: Each step must reference EITHER:
   - A specific detail from {target_partner}'s profile, OR
   - A specific quote/moment from the transcript, OR
   - A learned pattern from past fights (if provided)
   - NO generic advice allowed

3. **APOLOGY SCRIPT**: Must align with {target_partner}'s apology_preferences.
   - What makes apologies feel genuine TO THEM?
   - Include their language/needs in the script

4. **SUGGESTED GESTURE**: Pick from {target_partner}'s repair_gestures list.
   - If they listed "making tea", suggest that specifically
   - Don't invent gestures they didn't mention

5. **THINGS TO AVOID**: Must include items from {target_partner}'s escalation_triggers.
   - What makes things WORSE for them?
   - Also include phrases that escalated THIS specific fight

6. **CITATIONS**: For every suggestion, include a brief citation:
   - "[Profile]" for profile-based suggestions
   - "[Transcript 3:42]" for transcript references
   - "[Pattern: worked 3/3 times]" for historical patterns

=== VALIDATION CHECKLIST ===

Before finalizing, verify your response includes:
[ ] Reference to {target_partner}'s post_conflict_need (space/connection)
[ ] Reference to {target_partner}'s apology_preferences
[ ] At least one gesture from {target_partner}'s repair_gestures
[ ] At least two items from {target_partner}'s escalation_triggers
[ ] At least one specific transcript quote
[ ] Citations on all major recommendations

DO NOT give generic relationship advice. Every suggestion must be traceable to profile data, transcript, or past patterns.
"""

    return self.structured_output(
        messages=[{"role": "user", "content": prompt}],
        response_model=response_model,
        temperature=0.7,
        max_tokens=2500
    )
```

---

## Updated Pydantic Response Model

```python
class RepairStep(BaseModel):
    """A single repair step with citation"""
    action: str = Field(description="What to do")
    rationale: str = Field(description="Why this will help")
    citation_type: Literal["profile", "transcript", "pattern", "calendar"]
    citation_detail: str = Field(description="e.g., 'Sarah needs space after conflicts'")

class AvoidanceItem(BaseModel):
    """Something to avoid with citation"""
    what_to_avoid: str
    why: str
    citation_type: Literal["profile", "transcript", "pattern"]
    citation_detail: str

class PersonalizedRepairPlan(BaseModel):
    """Repair plan with mandatory citations"""
    conflict_id: str
    requesting_partner: str = Field(description="Who is initiating repair")
    target_partner: str = Field(description="Who they are approaching")

    # Timing with citation
    when_to_approach: str
    timing_rationale: str
    timing_citation: str = Field(description="Reference to profile post_conflict_need")

    # Steps with citations
    steps: list[RepairStep] = Field(min_length=3, max_length=6)

    # Apology with citation
    apology_script: str
    apology_rationale: str = Field(description="How this aligns with their apology_preferences")

    # Gesture with citation
    suggested_gesture: str
    gesture_citation: str = Field(description="From their repair_gestures list")

    # Avoidances with citations
    things_to_avoid: list[AvoidanceItem] = Field(min_length=2)

    # Meta
    personalization_score: Literal["high", "medium", "low"] = Field(
        description="Self-assessment: high if all citations present, medium if some missing"
    )
    missing_data: list[str] = Field(
        default=[],
        description="Profile fields that were empty/missing"
    )
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `backend/app/services/profile_service.py` | NEW: Create `get_full_partner_profile()` |
| `backend/app/routes/post_fight.py` | Replace RAG query with full profile fetch |
| `backend/app/services/llm_service.py` | Rewrite `generate_repair_plan()` prompt |
| `backend/app/models/schemas.py` | Add `PersonalizedRepairPlan`, `RepairStep`, `AvoidanceItem` |

---

## Testing Checklist

- [ ] Full profile fetch returns all sections (not just similar ones)
- [ ] Repair plan fails gracefully if profile incomplete
- [ ] LLM output includes citations for all major recommendations
- [ ] PersonalizedRepairPlan validates successfully
- [ ] `personalization_score` reflects actual citation coverage
- [ ] No generic advice appears in output
