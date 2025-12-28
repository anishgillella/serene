# Phase 1: Enhanced Onboarding

## Goal

Add repair-focused questions to onboarding so we have explicit data about what each partner needs after a conflict.

## Current Onboarding Structure

**5 Chapters, ~20 questions** (`frontend/src/pages/Onboarding.tsx`):

| Chapter | Fields |
|---------|--------|
| 1. The Basics | name, age, role |
| 2. Your Story | background, hobbies, favorites |
| 3. Inner World | communication_style, stress_triggers, soothing_mechanisms, traumatic_experiences |
| 4. Your Partner | partner_description, what_i_admire, what_frustrates_me |
| 5. Us | relationship_dynamic, recurring_arguments, shared_goals |

## New Questions (Add to Chapter 3: Inner World)

### Question 1: Apology Preferences

```
Field: apology_preferences
Label: "What makes an apology feel genuine to you?"
Sublabel: "What do you need to hear or see to feel like your partner truly understands?"
Placeholder: "I need them to acknowledge specifically what they did wrong..."
Type: multiline text
Icon: HeartIcon
```

**Why:** People have different apology languages:
- Some need "I was wrong" (admission)
- Some need "I'll never do it again" (commitment)
- Some need "I understand how that hurt you" (empathy)
- Some need actions, not words

### Question 2: Post-Conflict Need

```
Field: post_conflict_need
Label: "After a conflict, what do you need first?"
Sublabel: "Do you need time alone to process, or do you need connection right away?"
Type: choice (not free text)
Options:
  - "Space - I need time alone to cool down and process"
  - "Connection - I need to feel close again right away"
  - "It depends on the situation"
Icon: SparklesIcon
```

**Why:** This is the #1 mismatch in post-fight dynamics. One partner pursues ("let's talk now") while the other withdraws ("I need space"). Knowing this upfront prevents the repair attempt from backfiring.

### Question 3: Repair Gestures

```
Field: repair_gestures
Label: "What small gestures help you feel better after a fight?"
Sublabel: "Things your partner can do that help you calm down or feel cared for."
Placeholder: "Making me tea, a genuine hug, giving me space for 20 minutes..."
Type: list (comma-separated)
Icon: HeartIcon
```

**Why:** Highly personal. Could be:
- Physical: hug, hand-hold, back rub
- Acts of service: make tea, bring food, do a chore
- Space: leave me alone, don't text
- Words: sincere "I love you", acknowledgment
- Quality time: sit with me quietly

### Question 4: Escalation Triggers

```
Field: escalation_triggers
Label: "What does your partner do during fights that makes things worse?"
Sublabel: "Behaviors or phrases that escalate the conflict for you."
Placeholder: "Saying 'calm down', walking away mid-sentence, bringing up past issues..."
Type: list (comma-separated)
Icon: AlertCircleIcon
```

**Why:** Direct insight into anti-patterns. The repair plan can explicitly say "AVOID: saying 'calm down' - Sarah listed this as an escalation trigger."

---

## Data Model Changes

### Frontend (`frontend/src/pages/Onboarding.tsx`)

Update `PartnerProfile` interface:

```typescript
interface PartnerProfile {
    // Existing fields...
    name: string;
    role: 'partner_a' | 'partner_b';
    age: number | '';
    communication_style: string;
    stress_triggers: string[];
    soothing_mechanisms: string[];
    // ... other existing fields

    // NEW: Repair-specific fields
    apology_preferences: string;
    post_conflict_need: 'space' | 'connection' | 'depends';
    repair_gestures: string[];
    escalation_triggers: string[];
}
```

### Backend (`backend/app/models/schemas.py`)

Update Pydantic model:

```python
class PartnerProfile(BaseModel):
    # Existing fields...
    name: str
    role: Literal["partner_a", "partner_b"]
    age: int
    communication_style: str
    stress_triggers: list[str]
    soothing_mechanisms: list[str]
    # ... other existing fields

    # NEW: Repair-specific fields
    apology_preferences: str
    post_conflict_need: Literal["space", "connection", "depends"]
    repair_gestures: list[str]
    escalation_triggers: list[str]
```

---

## Steps Array Update

Add to the `steps` array in `Onboarding.tsx` (after `traumatic_experiences`, before Chapter 4):

```typescript
// NEW: Repair preferences section
{
    type: 'partner',
    field: 'apology_preferences',
    label: "What makes an apology feel genuine to you?",
    sublabel: "What do you need to hear or see to feel like your partner truly understands?",
    placeholder: "I need them to acknowledge specifically what they did wrong...",
    multiline: true,
    icon: HeartIcon,
    chapter: 3
},
{
    type: 'partner',
    field: 'post_conflict_need',
    label: "After a conflict, what do you need first?",
    sublabel: "Do you need time alone to process, or connection right away?",
    placeholder: "Space to cool down / Connection right away / Depends",
    icon: SparklesIcon,
    chapter: 3
},
{
    type: 'partner',
    field: 'repair_gestures',
    label: "What small gestures help you feel better after a fight?",
    sublabel: "Things your partner can do that help you calm down.",
    placeholder: "Making me tea, a genuine hug, 20 minutes of space...",
    isList: true,
    icon: HeartIcon,
    chapter: 3
},
{
    type: 'partner',
    field: 'escalation_triggers',
    label: "What makes fights worse for you?",
    sublabel: "Behaviors or phrases from your partner that escalate things.",
    placeholder: "Saying 'calm down', walking away, bringing up past issues...",
    isList: true,
    icon: AlertCircleIcon,
    chapter: 3
},
```

---

## Backend: Semantic Chunking Update

In `backend/app/routes/onboarding.py`, add a new semantic chunk for repair preferences:

```python
# Existing chunks...
chunks = [
    # ... identity, background, inner_world, interests, partner_view, relationship
]

# NEW: Add repair preferences chunk
repair_chunk = f"""
{name}'s Repair & Conflict Preferences:

What makes an apology genuine to {name}:
{profile.apology_preferences}

After a conflict, {name} needs: {profile.post_conflict_need}

Gestures that help {name} feel better:
{', '.join(profile.repair_gestures)}

Things that make fights WORSE for {name}:
{', '.join(profile.escalation_triggers)}

Soothing mechanisms:
{', '.join(profile.soothing_mechanisms)}

Stress triggers:
{', '.join(profile.stress_triggers)}
"""

chunks.append({
    "section": "repair_preferences",
    "content": repair_chunk,
    "metadata": {
        "relationship_id": relationship_id,
        "role": profile.role,
        "name": profile.name,
        "section": "repair_preferences"
    }
})
```

---

## Validation: Both Partners Required

Add validation before repair plan generation:

```python
# backend/app/routes/post_fight.py

async def generate_repair_plans(conflict_id: str, relationship_id: str, ...):
    # Check both profiles exist
    partner_a_profile = await get_partner_profile(relationship_id, "partner_a")
    partner_b_profile = await get_partner_profile(relationship_id, "partner_b")

    if not partner_a_profile or not partner_b_profile:
        missing = []
        if not partner_a_profile:
            missing.append("Partner A")
        if not partner_b_profile:
            missing.append("Partner B")

        return {
            "status": "incomplete_profiles",
            "missing_profiles": missing,
            "message": f"Personalized repair plans require both partners to complete onboarding. Missing: {', '.join(missing)}"
        }

    # Proceed with generation...
```

Frontend should handle this response and show an invite prompt.

---

## Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/pages/Onboarding.tsx` | Add 4 new questions, update PartnerProfile interface, update initial state |
| `backend/app/models/schemas.py` | Add new fields to PartnerProfile model |
| `backend/app/routes/onboarding.py` | Add repair_preferences chunk to semantic chunking |
| `backend/app/routes/post_fight.py` | Add both-partner validation before repair plan generation |

---

## Testing Checklist

- [ ] All 4 new questions render correctly in onboarding
- [ ] Voice input works for new questions
- [ ] Data saves correctly to backend
- [ ] New chunk appears in Pinecone with correct metadata
- [ ] Repair plan generation fails gracefully if one profile missing
- [ ] Frontend shows appropriate "invite partner" message when profile missing
