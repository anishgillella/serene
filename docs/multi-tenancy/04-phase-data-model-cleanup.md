# Phase 4: Data Model Cleanup (Gender-Neutral)

## Goal

Remove all gender-specific assumptions from the data model and UI. Replace "boyfriend/girlfriend" terminology with generic "partner" references, allowing any type of couple to use the application.

## Duration Estimate

~2 days of implementation

## Prerequisites

- Phases 1-3 completed
- Partner invitation flow working
- Dynamic user context available

---

## Why This Matters

The current codebase assumes heterosexual relationships:
- `boyfriend_profile` / `girlfriend_profile` in database
- `unmet_needs_boyfriend` / `unmet_needs_girlfriend` in analysis
- Hardcoded "Adrian Malhotra" / "Elara Voss" references
- Gender-specific language in prompts

A gender-neutral approach:
- Supports all relationship types (same-sex, non-binary, etc.)
- Uses "Partner 1" / "Partner 2" or custom display names
- Focuses on the relationship, not gender roles

---

## Database Migration

```sql
-- File: backend/app/models/migrations/004_gender_neutral_schema.sql

-- Update profile types to be gender-neutral
-- Keep old types for backward compatibility during migration

-- First, add new valid values
ALTER TABLE profiles
DROP CONSTRAINT IF EXISTS profiles_pdf_type_check;

ALTER TABLE profiles
ADD CONSTRAINT profiles_pdf_type_check
CHECK (pdf_type IN (
    'partner_profile',           -- New generic type
    'partner_a_profile',         -- New specific types
    'partner_b_profile',
    'relationship_handbook',
    'boyfriend_profile',         -- Legacy (deprecated)
    'girlfriend_profile'         -- Legacy (deprecated)
));

-- Create a migration view to map old types to new
-- This is for gradual migration, not immediate replacement

-- Update existing profiles to use user_id instead of gender
ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS owner_user_id UUID REFERENCES users(id);

-- Add index for user-based profile queries
CREATE INDEX IF NOT EXISTS idx_profiles_owner
    ON profiles(owner_user_id)
    WHERE owner_user_id IS NOT NULL;
```

---

## Backend Changes

### 1. Update Profile PDF Types

**File: `backend/app/routes/pdf_upload.py`**

```python
# Before:
VALID_PDF_TYPES = ["boyfriend_profile", "girlfriend_profile", "relationship_handbook"]

# After:
VALID_PDF_TYPES = [
    "partner_profile",       # Generic partner profile
    "relationship_handbook", # Shared relationship docs
    # Legacy types (for backward compatibility)
    "boyfriend_profile",
    "girlfriend_profile",
]


@router.post("/upload")
async def upload_pdf(
    file: UploadFile,
    pdf_type: str = Form(...),
    current_user: UserContext = Depends(get_current_user)
):
    # Map legacy types to new types
    type_mapping = {
        "boyfriend_profile": "partner_profile",
        "girlfriend_profile": "partner_profile",
    }
    normalized_type = type_mapping.get(pdf_type, pdf_type)

    # Store with owner_user_id for per-partner profiles
    profile_id = db_service.create_profile(
        relationship_id=current_user.relationship_id,
        pdf_type=normalized_type,
        owner_user_id=current_user.user_id,  # New field
        file_path=s3_path
    )

    return {"profile_id": profile_id}
```

### 2. Update Conflict Analysis Schema

**File: `backend/app/models/schemas.py`**

```python
# Before:
class ConflictAnalysis(BaseModel):
    root_cause: str
    escalation_points: List[str]
    unmet_needs_boyfriend: List[str]  # Gender-specific
    unmet_needs_girlfriend: List[str]  # Gender-specific
    summary: str

# After:
class ConflictAnalysis(BaseModel):
    root_cause: str
    escalation_points: List[str]
    unmet_needs_partner_a: List[str]  # Generic
    unmet_needs_partner_b: List[str]  # Generic
    # For display, these map to actual partner names
    summary: str

    # Optional: Include partner names for context
    partner_a_name: Optional[str] = None
    partner_b_name: Optional[str] = None

    class Config:
        # Allow both old and new field names during migration
        extra = "allow"


class RepairPlan(BaseModel):
    requesting_partner: str  # "partner_a" or "partner_b" (not "Boyfriend")
    requesting_partner_name: Optional[str] = None  # Actual name for display
    steps: List[RepairStep]
    apology_script: str
    timing_recommendation: str
```

### 3. Update Conflict Analysis Tool

**File: `backend/app/tools/conflict_analysis.py`**

```python
async def analyze_conflict_transcript(
    transcript: str,
    relationship_context: dict  # New parameter
) -> ConflictAnalysis:
    """
    Analyze a conflict transcript with relationship context.

    Args:
        transcript: The conflict transcript text
        relationship_context: {
            "partner_a_name": "Adrian",
            "partner_b_name": "Elara",
            "partner_a_profile": "...",
            "partner_b_profile": "..."
        }
    """
    partner_a = relationship_context.get("partner_a_name", "Partner A")
    partner_b = relationship_context.get("partner_b_name", "Partner B")

    prompt = f"""Analyze this relationship conflict between {partner_a} and {partner_b}.

Transcript:
{transcript}

Provide analysis in JSON format:
{{
    "root_cause": "The underlying issue causing this conflict",
    "escalation_points": ["Moment 1 where tension increased", "Moment 2..."],
    "unmet_needs_partner_a": ["{partner_a}'s unmet needs"],
    "unmet_needs_partner_b": ["{partner_b}'s unmet needs"],
    "summary": "Brief summary of the conflict"
}}

Use {partner_a} and {partner_b} by name in your analysis.
Focus on the relationship dynamics, not gender roles.
"""

    response = await llm_service.complete(prompt)
    analysis = json.loads(response)

    return ConflictAnalysis(
        **analysis,
        partner_a_name=partner_a,
        partner_b_name=partner_b
    )
```

### 4. Update Repair Coaching Tool

**File: `backend/app/tools/repair_coaching.py`**

```python
async def generate_repair_plan(
    conflict_id: str,
    requesting_partner: str,  # "partner_a" or "partner_b"
    relationship_context: dict
) -> RepairPlan:
    """Generate repair plan for the requesting partner."""
    partner_a = relationship_context.get("partner_a_name", "Partner A")
    partner_b = relationship_context.get("partner_b_name", "Partner B")

    # Determine names based on who's requesting
    if requesting_partner == "partner_a":
        requester_name = partner_a
        other_name = partner_b
    else:
        requester_name = partner_b
        other_name = partner_a

    prompt = f"""Create a repair plan for {requester_name} to reconnect with {other_name}
after their recent conflict.

The plan should help {requester_name}:
1. Take responsibility for their part
2. Understand {other_name}'s perspective
3. Offer a genuine apology
4. Suggest concrete repair actions

Format as JSON:
{{
    "steps": [
        {{"action": "...", "why": "...", "timing": "..."}}
    ],
    "apology_script": "A heartfelt apology {requester_name} could say...",
    "timing_recommendation": "When and how to approach {other_name}"
}}
"""

    response = await llm_service.complete(prompt)
    plan = json.loads(response)

    return RepairPlan(
        requesting_partner=requesting_partner,
        requesting_partner_name=requester_name,
        **plan
    )
```

### 5. Update DB Service Speaker Labels

**File: `backend/app/services/db_service.py`**

```python
def get_conflict_transcript(self, conflict_id: str) -> dict:
    """Get conflict transcript with dynamic speaker names."""
    conflict = self.get_conflict(conflict_id)
    relationship_id = conflict.get("relationship_id")

    # Get speaker labels from relationship_members
    speaker_labels = self.get_speaker_labels(relationship_id)
    partner_a_name = speaker_labels.get("partner_a", "Partner A")
    partner_b_name = speaker_labels.get("partner_b", "Partner B")

    # Get raw transcript
    transcript = self._get_raw_transcript(conflict_id)

    # Replace speaker IDs with actual names
    formatted_segments = []
    for segment in transcript.get("segments", []):
        speaker_id = segment.get("speaker", "partner_a")
        speaker_name = partner_a_name if speaker_id == "partner_a" else partner_b_name

        formatted_segments.append({
            "speaker": speaker_name,
            "speaker_id": speaker_id,
            "text": segment.get("text", "")
        })

    return {
        "conflict_id": conflict_id,
        "segments": formatted_segments,
        "speaker_labels": {
            "partner_a": partner_a_name,
            "partner_b": partner_b_name
        }
    }
```

### 6. Update Luna Agent Prompts

**File: `backend/app/agents/luna/agent.py`**

```python
def build_system_prompt(self, user_name: str, partner_name: str) -> str:
    """Build dynamic system prompt with actual names."""
    return f"""You are Luna, a warm and empathetic relationship coach.

You're currently speaking with {user_name}, who is in a relationship with {partner_name}.

Your role:
- Listen actively and validate feelings
- Help {user_name} understand {partner_name}'s perspective
- Suggest healthy communication strategies
- Provide actionable repair steps when appropriate

Guidelines:
- Use {user_name} and {partner_name}'s names naturally
- Avoid assumptions about gender or relationship roles
- Focus on the relationship dynamics and communication patterns
- Be supportive but also gently challenge unhelpful patterns

Remember: You're {user_name}'s supportive friend, helping them navigate
their relationship with {partner_name}. Be warm, understanding, and practical.
"""
```

### 7. Update RAG Profile Queries

**File: `backend/app/services/transcript_rag.py`**

```python
async def fetch_partner_profiles(
    self,
    query_embedding: list,
    relationship_id: str,
    current_user_id: str
) -> dict:
    """Fetch both partners' profiles with proper identification."""

    # Query profiles by relationship, grouped by owner
    results = await asyncio.to_thread(
        self.pinecone_index.query,
        vector=query_embedding,
        top_k=10,
        namespace="profiles",
        filter={
            "relationship_id": {"$eq": relationship_id},
            "pdf_type": {"$in": ["partner_profile", "boyfriend_profile", "girlfriend_profile"]}
        },
        include_metadata=True
    )

    # Separate by owner
    current_user_profiles = []
    partner_profiles = []

    for match in results.get("matches", []):
        metadata = match.get("metadata", {})
        owner_id = metadata.get("owner_user_id")

        if owner_id == current_user_id:
            current_user_profiles.append(metadata.get("text", ""))
        else:
            partner_profiles.append(metadata.get("text", ""))

    return {
        "current_user_profile": "\n".join(current_user_profiles),
        "partner_profile": "\n".join(partner_profiles)
    }
```

---

## Frontend Changes

### 1. Update Analysis Display

**File: `frontend/src/pages/PostFightSession.tsx`**

```tsx
import { useUserContext } from '../hooks/useUserContext';

export default function PostFightSession() {
  const { displayName, partnerName } = useUserContext();
  const [analysis, setAnalysis] = useState<ConflictAnalysis | null>(null);

  // Map generic field names to display names
  const getPartnerAName = () => analysis?.partner_a_name || displayName;
  const getPartnerBName = () => analysis?.partner_b_name || partnerName;

  return (
    <div className="analysis-section">
      {/* Unmet Needs */}
      <div className="needs-section">
        <h3>{getPartnerAName()}'s Unmet Needs</h3>
        <ul>
          {analysis?.unmet_needs_partner_a.map((need, i) => (
            <li key={i}>{need}</li>
          ))}
        </ul>
      </div>

      <div className="needs-section">
        <h3>{getPartnerBName()}'s Unmet Needs</h3>
        <ul>
          {analysis?.unmet_needs_partner_b.map((need, i) => (
            <li key={i}>{need}</li>
          ))}
        </ul>
      </div>

      {/* Repair Plan */}
      {repairPlan && (
        <div className="repair-section">
          <h3>Repair Plan for {repairPlan.requesting_partner_name}</h3>
          {/* ... */}
        </div>
      )}
    </div>
  );
}
```

### 2. Update Onboarding

**File: `frontend/src/pages/Onboarding.tsx`**

```tsx
// Before:
const ROLE_OPTIONS = [
  { value: 'boyfriend', label: 'Boyfriend' },
  { value: 'girlfriend', label: 'Girlfriend' },
];

// After:
// Remove role selection entirely - just ask for display name

export default function Onboarding() {
  const [displayName, setDisplayName] = useState('');

  return (
    <div className="onboarding">
      <h1>Welcome to Serene</h1>
      <p>Let's set up your profile</p>

      <div className="form-group">
        <label>What should we call you?</label>
        <input
          type="text"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          placeholder="Your name or nickname"
        />
        <p className="hint">
          This is how Luna and your partner will see you
        </p>
      </div>

      <button onClick={handleContinue}>
        Continue
      </button>
    </div>
  );
}
```

### 3. Update Profile Upload

**File: `frontend/src/pages/Upload.tsx`**

```tsx
// Before:
const PDF_TYPES = [
  { value: 'boyfriend_profile', label: 'Boyfriend Profile' },
  { value: 'girlfriend_profile', label: 'Girlfriend Profile' },
];

// After:
const PDF_TYPES = [
  { value: 'partner_profile', label: 'My Profile' },
  { value: 'relationship_handbook', label: 'Relationship Handbook' },
];

export default function Upload() {
  const { displayName } = useUserContext();

  return (
    <div>
      <h2>Upload Profile Documents</h2>
      <p>
        Share documents about yourself to help Luna understand you better.
      </p>

      <select value={pdfType} onChange={(e) => setPdfType(e.target.value)}>
        <option value="partner_profile">{displayName}'s Profile</option>
        <option value="relationship_handbook">Relationship Handbook</option>
      </select>

      {/* File upload UI */}
    </div>
  );
}
```

### 4. Update FightCapture Labels

**File: `frontend/src/pages/FightCapture.tsx`**

```tsx
import { useUserContext } from '../hooks/useUserContext';

export default function FightCapture() {
  const { displayName, partnerName } = useUserContext();

  // Dynamic speaker identification
  const speakers = [
    { id: 'partner_a', name: displayName, color: 'blue' },
    { id: 'partner_b', name: partnerName, color: 'purple' },
  ];

  return (
    <div>
      <div className="speaker-legend">
        {speakers.map(speaker => (
          <div key={speaker.id} className="speaker-badge" style={{ color: speaker.color }}>
            {speaker.name}
          </div>
        ))}
      </div>

      {/* Transcript display */}
      {transcript.map((segment, i) => {
        const speaker = speakers.find(s => s.id === segment.speaker_id);
        return (
          <TranscriptBubble
            key={i}
            speaker={speaker?.name || 'Unknown'}
            text={segment.text}
            color={speaker?.color}
          />
        );
      })}
    </div>
  );
}
```

### 5. Update Analytics Page

**File: `frontend/src/pages/Analytics.tsx`**

```tsx
import { useUserContext } from '../hooks/useUserContext';

export default function Analytics() {
  const { displayName, partnerName } = useUserContext();

  return (
    <div>
      <h2>Relationship Analytics</h2>

      {/* Communication Patterns */}
      <div className="chart-section">
        <h3>Communication Patterns</h3>
        <div className="legend">
          <span className="legend-item blue">{displayName}</span>
          <span className="legend-item purple">{partnerName}</span>
        </div>
        {/* Chart component */}
      </div>

      {/* Conflict Initiation */}
      <div className="stat-card">
        <h4>Conflict Initiation</h4>
        <p>{displayName}: {stats.partner_a_initiated}%</p>
        <p>{partnerName}: {stats.partner_b_initiated}%</p>
      </div>
    </div>
  );
}
```

---

## Data Migration Script

**File: `backend/scripts/migrate_gender_neutral.py`**

```python
"""
Migration script to update existing data to gender-neutral format.
Run once after deploying Phase 4 changes.
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.db_service import db_service


def migrate_profiles():
    """Update profile pdf_type from gendered to neutral."""
    print("Migrating profiles...")

    # Get all relationships with their members
    query = """
        SELECT
            p.id as profile_id,
            p.pdf_type,
            p.relationship_id,
            rm.user_id as owner_user_id
        FROM profiles p
        LEFT JOIN relationship_members rm
            ON rm.relationship_id = p.relationship_id
        WHERE p.pdf_type IN ('boyfriend_profile', 'girlfriend_profile')
          AND p.owner_user_id IS NULL
    """

    with db_service.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

            for row in rows:
                profile_id, pdf_type, relationship_id, owner_user_id = row

                # Update to neutral type and set owner
                cur.execute("""
                    UPDATE profiles
                    SET pdf_type = 'partner_profile',
                        owner_user_id = %s
                    WHERE id = %s
                """, (owner_user_id, profile_id))

            conn.commit()

    print(f"Migrated {len(rows)} profiles")


def migrate_analysis_fields():
    """Update analysis JSON in S3 to use neutral field names."""
    print("Migrating analysis fields...")

    # This would update S3 JSON files
    # For MVP, we handle this in code by accepting both field names

    print("Analysis migration: handled in code (backward compatible)")


def migrate_pinecone_metadata():
    """Update Pinecone vector metadata."""
    print("Migrating Pinecone metadata...")

    # For MVP, we add new metadata while keeping old
    # Old queries still work, new queries use neutral terms

    print("Pinecone migration: handled in code (backward compatible)")


if __name__ == "__main__":
    migrate_profiles()
    migrate_analysis_fields()
    migrate_pinecone_metadata()
    print("Migration complete!")
```

---

## Testing Checklist

- [ ] Create new relationship with custom display names
- [ ] Upload profile as "partner_profile" type
- [ ] Conflict analysis uses actual partner names
- [ ] Repair plan addresses correct partner
- [ ] Luna uses dynamic names in conversation
- [ ] Analytics show partner names (not "boyfriend/girlfriend")
- [ ] Existing Adrian/Elara data still works
- [ ] Legacy profile types still accessible

---

## Files Modified

| File | Changes |
|------|---------|
| `backend/app/routes/pdf_upload.py` | Gender-neutral PDF types |
| `backend/app/models/schemas.py` | Neutral field names |
| `backend/app/tools/conflict_analysis.py` | Dynamic partner names |
| `backend/app/tools/repair_coaching.py` | Dynamic partner names |
| `backend/app/services/db_service.py` | Dynamic speaker labels |
| `backend/app/agents/luna/agent.py` | Neutral prompts |
| `backend/app/services/transcript_rag.py` | Owner-based profile queries |
| `frontend/src/pages/PostFightSession.tsx` | Dynamic names |
| `frontend/src/pages/Onboarding.tsx` | Remove role selection |
| `frontend/src/pages/Upload.tsx` | Neutral PDF types |
| `frontend/src/pages/FightCapture.tsx` | Dynamic speaker labels |
| `frontend/src/pages/Analytics.tsx` | Dynamic partner names |

---

## Next Phase

Proceed to [Phase 5: Security Hardening](./05-phase-security-hardening.md) to implement proper RLS policies and access control.
