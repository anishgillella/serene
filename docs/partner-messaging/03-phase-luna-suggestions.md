# Phase 3: Luna Suggestions & Active Intervention

Core AI phase - Luna helps partners communicate better by suggesting message improvements before sending.

## Goals

- Luna analyzes draft messages and suggests improvements
- Multiple suggestion alternatives with different tones
- Active intervention for high-risk messages
- All suggestions are **private to the typing partner**
- Configurable sensitivity levels

## Key Principle: Privacy

**The receiving partner NEVER sees Luna's suggestions.** When Partner A types a message:
1. Luna may suggest a rewrite
2. Only Partner A sees the suggestion
3. Partner A chooses: original, suggested, or modified
4. Partner B receives the final message - no indication of Luna's involvement

This preserves authenticity while enabling growth.

## Prerequisites

- Phase 1 complete (basic messaging)
- Phase 2 complete (preferences for sensitivity settings)

---

## Tech Stack & Dependencies

### Backend Dependencies

No new dependencies required - uses existing LLM infrastructure:

```txt
# Already in requirements.txt
openai>=1.0.0          # OpenRouter uses OpenAI-compatible API
pydantic>=2.0.0        # For structured LLM output parsing
```

### Frontend Dependencies

No new dependencies required.

### Configuration Required

**Backend** - Uses existing LLM configuration in `backend/app/config.py`:
```python
# Already configured
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
```

**LLM Model**: Uses `google/gemini-2.5-flash-preview` via OpenRouter (configured in `llm_service.py`)

### New Files to Create

| File | Type | Description |
|------|------|-------------|
| `message_suggestion_service.py` | Python | Core suggestion logic with LLM |
| `LunaSuggestionOverlay.tsx` | React | Side-by-side comparison UI |
| `LunaInterventionBanner.tsx` | React | Warning banner component |

### Services Integration

This phase integrates with existing services:

| Service | Purpose |
|---------|---------|
| `llm_service.py` | LLM calls with structured output |
| `db_service.py` | Get relationship triggers, partner profiles |
| `conflict_enrichment_service.py` | Pattern: trigger phrase detection |
| `gottman_analysis_service.py` | Pattern: Four Horsemen detection |

---

## Backend Implementation

### 1. Database Migration Addition

**File**: `backend/app/models/migrations/009_partner_messaging.sql` (add to existing)

```sql
-- ============================================
-- MESSAGE SUGGESTIONS
-- Luna's pre-send suggestions (private to sender)
-- ============================================
CREATE TABLE IF NOT EXISTS message_suggestions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES partner_conversations(id) ON DELETE CASCADE,
    sender_id TEXT NOT NULL CHECK (sender_id IN ('partner_a', 'partner_b')),

    -- Original message they were typing
    original_message TEXT NOT NULL,

    -- Luna's analysis
    risk_assessment TEXT NOT NULL CHECK (risk_assessment IN ('safe', 'risky', 'high_risk')),
    detected_issues JSONB DEFAULT '[]'::jsonb,
    -- e.g., ['accusatory_language', 'known_trigger', 'escalation_pattern']

    -- Suggestions
    primary_suggestion TEXT NOT NULL,
    suggestion_rationale TEXT NOT NULL,
    alternatives JSONB DEFAULT '[]'::jsonb,
    -- e.g., [{"text": "...", "tone": "gentle", "rationale": "..."}]

    -- User response
    user_action TEXT CHECK (user_action IN ('accepted', 'rejected', 'modified', 'ignored')),
    final_message_id UUID REFERENCES partner_messages(id),
    selected_alternative_index INTEGER,  -- which alternative was chosen (0 = primary)

    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    responded_at TIMESTAMP WITH TIME ZONE,

    -- Context used for suggestion
    context_message_count INTEGER,  -- how many prior messages were considered
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_message_suggestions_conversation
    ON message_suggestions(conversation_id);
CREATE INDEX IF NOT EXISTS idx_message_suggestions_sender
    ON message_suggestions(sender_id);
CREATE INDEX IF NOT EXISTS idx_message_suggestions_action
    ON message_suggestions(user_action);
CREATE INDEX IF NOT EXISTS idx_message_suggestions_created
    ON message_suggestions(created_at DESC);

ALTER TABLE message_suggestions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public access to message_suggestions"
    ON message_suggestions FOR ALL USING (true);
```

### 2. Suggestion Service

**File**: `backend/app/services/message_suggestion_service.py` (create new)

```python
"""
Message Suggestion Service

Analyzes draft messages and generates Luna's suggestions for better communication.
Uses relationship context (triggers, patterns, profiles) to personalize suggestions.
"""

import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.services.db_service import db_service
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


# ============================================
# PYDANTIC MODELS FOR STRUCTURED OUTPUT
# ============================================

class SuggestionAlternative(BaseModel):
    """An alternative way to phrase the message."""
    text: str = Field(..., description="The suggested message text")
    tone: str = Field(..., description="The tone of this alternative: gentle, direct, curious, empathetic, playful")
    rationale: str = Field(..., description="Why this phrasing might work better")


class MessageAnalysisResult(BaseModel):
    """LLM's analysis of the draft message."""
    risk_assessment: str = Field(..., description="Risk level: safe, risky, or high_risk")
    detected_issues: List[str] = Field(default=[], description="List of issues detected")
    primary_suggestion: str = Field(..., description="The recommended rewrite")
    suggestion_rationale: str = Field(..., description="Why Luna suggests this change")
    alternatives: List[SuggestionAlternative] = Field(
        default=[],
        description="2-3 alternative phrasings with different tones"
    )
    underlying_need: Optional[str] = Field(
        None,
        description="The underlying emotional need behind the message"
    )


# ============================================
# INTERVENTION THRESHOLDS
# ============================================

INTERVENTION_THRESHOLDS = {
    'low': {
        'min_escalation_score': 0.8,
        'min_consecutive_negative': 4,
        'trigger_severity': 'severe'  # Only known severe triggers
    },
    'medium': {
        'min_escalation_score': 0.6,
        'min_consecutive_negative': 3,
        'trigger_severity': 'moderate'  # All known triggers
    },
    'high': {
        'min_escalation_score': 0.4,
        'min_consecutive_negative': 2,
        'trigger_severity': 'any'  # Triggers + predicted patterns
    }
}


class MessageSuggestionService:
    """
    Generates pre-send suggestions using LLM with relationship context.
    """

    def __init__(self):
        self.llm = llm_service

    async def analyze_and_suggest(
        self,
        draft_message: str,
        conversation_id: str,
        sender_id: str,
        relationship_id: str,
        sensitivity: str = 'medium'
    ) -> Dict[str, Any]:
        """
        Analyze a draft message and generate suggestions if needed.

        Args:
            draft_message: The message the user is about to send
            conversation_id: The conversation UUID
            sender_id: 'partner_a' or 'partner_b'
            relationship_id: The relationship UUID
            sensitivity: 'low', 'medium', or 'high'

        Returns:
            Suggestion object with risk assessment and alternatives
        """
        try:
            # 1. Get conversation context
            recent_messages = db_service.get_partner_messages(
                conversation_id=conversation_id,
                limit=10
            )

            # 2. Get known triggers for this relationship
            triggers = self._get_relationship_triggers(relationship_id)

            # 3. Get partner profiles for personalization
            profiles = self._get_partner_profiles(relationship_id)

            # 4. Check for quick risk indicators
            quick_risk = self._quick_risk_check(
                draft_message,
                recent_messages,
                triggers,
                sensitivity
            )

            # 5. If message seems safe and mode is 'high_risk_only', skip LLM
            if quick_risk == 'safe':
                return self._create_safe_response(draft_message)

            # 6. Full LLM analysis
            result = await self._analyze_with_llm(
                draft_message=draft_message,
                recent_messages=recent_messages,
                triggers=triggers,
                profiles=profiles,
                sender_id=sender_id
            )

            # 7. Store suggestion in database
            suggestion_id = self._store_suggestion(
                conversation_id=conversation_id,
                sender_id=sender_id,
                original_message=draft_message,
                result=result,
                context_count=len(recent_messages)
            )

            return {
                "suggestion_id": suggestion_id,
                "original_message": draft_message,
                "risk_assessment": result.risk_assessment,
                "detected_issues": result.detected_issues,
                "primary_suggestion": result.primary_suggestion,
                "suggestion_rationale": result.suggestion_rationale,
                "alternatives": [alt.dict() for alt in result.alternatives],
                "underlying_need": result.underlying_need
            }

        except Exception as e:
            logger.error(f"Error in analyze_and_suggest: {e}")
            # On error, return safe response (don't block sending)
            return self._create_safe_response(draft_message)

    def _quick_risk_check(
        self,
        message: str,
        recent_messages: List[dict],
        triggers: List[dict],
        sensitivity: str
    ) -> str:
        """
        Quick heuristic check before expensive LLM call.
        Returns 'safe', 'risky', or 'needs_analysis'.
        """
        message_lower = message.lower()
        thresholds = INTERVENTION_THRESHOLDS[sensitivity]

        # Check for known trigger phrases
        for trigger in triggers:
            if trigger.get('severity', 'moderate') == 'any' or \
               trigger.get('severity') == thresholds['trigger_severity']:
                if trigger['phrase'].lower() in message_lower:
                    return 'risky'

        # Check for accusatory language patterns
        accusatory_patterns = [
            'you always', 'you never', "you don't",
            "you can't", 'your fault', 'you should',
            'you make me', 'because of you'
        ]
        for pattern in accusatory_patterns:
            if pattern in message_lower:
                return 'needs_analysis'

        # Check for negative message streak
        if recent_messages:
            negative_count = 0
            for msg in recent_messages[-thresholds['min_consecutive_negative']:]:
                if msg.get('sentiment_label') == 'negative':
                    negative_count += 1
            if negative_count >= thresholds['min_consecutive_negative'] - 1:
                return 'needs_analysis'

        # Check for escalation keywords
        escalation_words = [
            'hate', 'sick of', 'done with', 'leave',
            'divorce', 'break up', 'can\'t stand'
        ]
        for word in escalation_words:
            if word in message_lower:
                return 'needs_analysis'

        return 'safe'

    async def _analyze_with_llm(
        self,
        draft_message: str,
        recent_messages: List[dict],
        triggers: List[dict],
        profiles: dict,
        sender_id: str
    ) -> MessageAnalysisResult:
        """
        Full LLM analysis of the message with relationship context.
        """
        # Build conversation context
        conversation_context = "\n".join([
            f"{msg['sender_id']}: {msg['content']}"
            for msg in recent_messages[-5:]  # Last 5 messages
        ])

        # Build trigger context
        trigger_context = ""
        if triggers:
            trigger_phrases = [t['phrase'] for t in triggers[:10]]
            trigger_context = f"""
Known trigger phrases for this couple (avoid these):
{', '.join(trigger_phrases)}
"""

        # Build profile context
        other_partner = 'partner_b' if sender_id == 'partner_a' else 'partner_a'
        partner_profile = profiles.get(other_partner, {})
        profile_context = ""
        if partner_profile:
            profile_context = f"""
About the recipient:
- Communication style: {partner_profile.get('communication_style', 'unknown')}
- Attachment style: {partner_profile.get('attachment_style', 'unknown')}
- Values: {', '.join(partner_profile.get('core_values', [])[:3])}
"""

        prompt = f"""You are Luna, an AI relationship coach. Analyze this draft message that someone is about to send to their partner.

RECENT CONVERSATION:
{conversation_context}

DRAFT MESSAGE TO SEND:
"{draft_message}"

{trigger_context}
{profile_context}

Analyze the message for:
1. Potential to escalate conflict
2. Accusatory or blaming language ("you always", "you never")
3. Known trigger phrases
4. Gottman's Four Horsemen (criticism, contempt, defensiveness, stonewalling)
5. The underlying emotional need behind the message

If the message could be improved, suggest alternatives that:
- Express the same underlying need
- Use "I" statements instead of "you" accusations
- Are specific rather than generalizing
- Invite dialogue rather than shutting it down

Provide:
- A risk assessment (safe, risky, or high_risk)
- The primary suggested rewrite
- 2-3 alternatives with different tones (gentle, direct, curious, empathetic)
- The underlying need the sender is trying to express

If the message is already well-phrased, mark it as 'safe' and return the original as the suggestion.
"""

        try:
            result = self.llm.structured_output(
                messages=[{"role": "user", "content": prompt}],
                response_model=MessageAnalysisResult,
                temperature=0.7
            )
            return result
        except Exception as e:
            logger.error(f"LLM analysis error: {e}")
            # Return safe default
            return MessageAnalysisResult(
                risk_assessment="safe",
                detected_issues=[],
                primary_suggestion=draft_message,
                suggestion_rationale="Unable to analyze at this time.",
                alternatives=[]
            )

    def _get_relationship_triggers(self, relationship_id: str) -> List[dict]:
        """Get known trigger phrases for this relationship."""
        try:
            # Use existing db_service method if available
            return db_service.get_trigger_phrases_for_relationship(relationship_id) or []
        except Exception:
            return []

    def _get_partner_profiles(self, relationship_id: str) -> dict:
        """Get partner profiles for context."""
        try:
            # Use existing profile service
            return db_service.get_partner_profiles(relationship_id) or {}
        except Exception:
            return {}

    def _create_safe_response(self, original_message: str) -> dict:
        """Create a 'safe' response when no suggestion is needed."""
        return {
            "suggestion_id": None,
            "original_message": original_message,
            "risk_assessment": "safe",
            "detected_issues": [],
            "primary_suggestion": original_message,
            "suggestion_rationale": "Your message looks good!",
            "alternatives": [],
            "underlying_need": None
        }

    def _store_suggestion(
        self,
        conversation_id: str,
        sender_id: str,
        original_message: str,
        result: MessageAnalysisResult,
        context_count: int
    ) -> str:
        """Store suggestion in database for tracking."""
        try:
            return db_service.save_message_suggestion(
                conversation_id=conversation_id,
                sender_id=sender_id,
                original_message=original_message,
                risk_assessment=result.risk_assessment,
                detected_issues=result.detected_issues,
                primary_suggestion=result.primary_suggestion,
                suggestion_rationale=result.suggestion_rationale,
                alternatives=[alt.dict() for alt in result.alternatives],
                context_message_count=context_count
            )
        except Exception as e:
            logger.error(f"Error storing suggestion: {e}")
            return None

    def record_suggestion_response(
        self,
        suggestion_id: str,
        action: str,
        final_message_id: str = None,
        selected_index: int = None
    ):
        """Record how the user responded to a suggestion."""
        try:
            db_service.update_message_suggestion_response(
                suggestion_id=suggestion_id,
                user_action=action,
                final_message_id=final_message_id,
                selected_alternative_index=selected_index
            )
        except Exception as e:
            logger.error(f"Error recording suggestion response: {e}")


# Singleton instance
message_suggestion_service = MessageSuggestionService()
```

### 3. Database Service Methods for Suggestions

**File**: `backend/app/services/db_service.py` (add these methods)

```python
# ============================================
# MESSAGE SUGGESTION METHODS
# ============================================

def save_message_suggestion(
    self,
    conversation_id: str,
    sender_id: str,
    original_message: str,
    risk_assessment: str,
    detected_issues: list,
    primary_suggestion: str,
    suggestion_rationale: str,
    alternatives: list,
    context_message_count: int
) -> str:
    """Save a Luna suggestion for a draft message."""
    import json

    with self.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO message_suggestions
                    (conversation_id, sender_id, original_message,
                     risk_assessment, detected_issues,
                     primary_suggestion, suggestion_rationale, alternatives,
                     context_message_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                conversation_id, sender_id, original_message,
                risk_assessment, json.dumps(detected_issues),
                primary_suggestion, suggestion_rationale, json.dumps(alternatives),
                context_message_count
            ))

            row = cur.fetchone()
            conn.commit()
            return str(row[0])


def update_message_suggestion_response(
    self,
    suggestion_id: str,
    user_action: str,
    final_message_id: str = None,
    selected_alternative_index: int = None
) -> bool:
    """Update a suggestion with the user's response."""
    with self.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE message_suggestions
                SET user_action = %s,
                    final_message_id = %s,
                    selected_alternative_index = %s,
                    responded_at = NOW()
                WHERE id = %s
            """, (user_action, final_message_id, selected_alternative_index, suggestion_id))

            conn.commit()
            return cur.rowcount > 0


def get_suggestion_acceptance_rate(
    self,
    relationship_id: str,
    days: int = 30
) -> dict:
    """Get suggestion acceptance statistics for analytics."""
    with self.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE user_action = 'accepted') as accepted,
                    COUNT(*) FILTER (WHERE user_action = 'rejected') as rejected,
                    COUNT(*) FILTER (WHERE user_action = 'modified') as modified,
                    COUNT(*) FILTER (WHERE user_action = 'ignored') as ignored
                FROM message_suggestions ms
                JOIN partner_conversations pc ON ms.conversation_id = pc.id
                WHERE pc.relationship_id = %s
                  AND ms.created_at > NOW() - INTERVAL '%s days'
                  AND ms.risk_assessment != 'safe'
            """, (relationship_id, days))

            row = cur.fetchone()
            total = row[0] or 0

            return {
                "total_suggestions": total,
                "accepted": row[1] or 0,
                "rejected": row[2] or 0,
                "modified": row[3] or 0,
                "ignored": row[4] or 0,
                "acceptance_rate": (row[1] or 0) / total if total > 0 else 0
            }
```

### 4. API Routes for Suggestions

**File**: `backend/app/routes/partner_messaging_routes.py` (add these endpoints)

```python
from app.services.message_suggestion_service import message_suggestion_service

class LunaSuggestionRequest(BaseModel):
    conversation_id: str
    sender_id: str = Field(..., pattern='^(partner_a|partner_b)$')
    draft_message: str = Field(..., min_length=1, max_length=5000)


class LunaSuggestionResponse(BaseModel):
    suggestion_id: Optional[str]
    original_message: str
    risk_assessment: str
    detected_issues: List[str]
    primary_suggestion: str
    suggestion_rationale: str
    alternatives: List[dict]
    underlying_need: Optional[str]


class SuggestionResponseRequest(BaseModel):
    action: str = Field(..., pattern='^(accepted|rejected|modified|ignored)$')
    final_message_id: Optional[str] = None
    selected_alternative_index: Optional[int] = None


@router.post("/suggest", response_model=LunaSuggestionResponse)
async def get_luna_suggestion(request: LunaSuggestionRequest):
    """
    Get Luna's suggestion for a draft message before sending.

    Luna analyzes the message for:
    - Potential escalation triggers
    - Accusatory language
    - Known trigger phrases for this relationship
    - Gottman's Four Horsemen markers

    Returns the original message if it's safe, or suggestions for improvement.
    """
    try:
        # Get user's sensitivity preference
        conversation = db_service.get_conversation_by_id(request.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        preferences = db_service.get_messaging_preferences(
            relationship_id=conversation['relationship_id'],
            partner_id=request.sender_id
        )
        sensitivity = preferences.get('intervention_sensitivity', 'medium')

        result = await message_suggestion_service.analyze_and_suggest(
            draft_message=request.draft_message,
            conversation_id=request.conversation_id,
            sender_id=request.sender_id,
            relationship_id=conversation['relationship_id'],
            sensitivity=sensitivity
        )

        return LunaSuggestionResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggestion/{suggestion_id}/respond")
async def respond_to_suggestion(
    suggestion_id: str,
    request: SuggestionResponseRequest
):
    """
    Record how the user responded to a Luna suggestion.

    Actions:
    - accepted: User sent Luna's suggestion
    - rejected: User sent their original message
    - modified: User edited the suggestion before sending
    - ignored: User cancelled/didn't send anything
    """
    try:
        message_suggestion_service.record_suggestion_response(
            suggestion_id=suggestion_id,
            action=request.action,
            final_message_id=request.final_message_id,
            selected_index=request.selected_alternative_index
        )
        return {"success": True}
    except Exception as e:
        logger.error(f"Error recording response: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Frontend Implementation

### 1. Luna Suggestion Overlay

**File**: `frontend/src/components/partner-chat/LunaSuggestionOverlay.tsx`

```tsx
import React, { useState } from 'react';
import { Bot, AlertTriangle, X, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Alternative {
    text: string;
    tone: string;
    rationale: string;
}

interface LunaSuggestion {
    suggestion_id: string | null;
    original_message: string;
    risk_assessment: 'safe' | 'risky' | 'high_risk';
    detected_issues: string[];
    primary_suggestion: string;
    suggestion_rationale: string;
    alternatives: Alternative[];
    underlying_need?: string;
}

interface LunaSuggestionOverlayProps {
    suggestion: LunaSuggestion;
    onAccept: (text: string, alternativeIndex: number) => void;
    onReject: () => void;
    onCancel: () => void;
}

const LunaSuggestionOverlay: React.FC<LunaSuggestionOverlayProps> = ({
    suggestion,
    onAccept,
    onReject,
    onCancel
}) => {
    const [selectedIndex, setSelectedIndex] = useState(0);
    const [showAlternatives, setShowAlternatives] = useState(false);

    const allOptions = [
        { text: suggestion.primary_suggestion, tone: 'recommended', rationale: suggestion.suggestion_rationale },
        ...suggestion.alternatives
    ];

    const selectedOption = allOptions[selectedIndex];

    const getRiskColor = (risk: string) => {
        switch (risk) {
            case 'high_risk': return 'text-red-500 bg-red-50';
            case 'risky': return 'text-amber-500 bg-amber-50';
            default: return 'text-green-500 bg-green-50';
        }
    };

    const getRiskLabel = (risk: string) => {
        switch (risk) {
            case 'high_risk': return 'High Risk';
            case 'risky': return 'Could Be Better';
            default: return 'Looks Good';
        }
    };

    const getToneEmoji = (tone: string) => {
        switch (tone) {
            case 'gentle': return '🕊️';
            case 'direct': return '🎯';
            case 'curious': return '🤔';
            case 'empathetic': return '💗';
            case 'playful': return '😊';
            case 'recommended': return '⭐';
            default: return '💬';
        }
    };

    return (
        <div className="absolute bottom-full left-0 right-0 mb-2 z-50">
            <div className="bg-surface-card rounded-2xl border border-accent/30 shadow-xl overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-border-subtle bg-accent/5">
                    <div className="flex items-center gap-2">
                        <Bot size={20} className="text-accent" />
                        <span className="font-medium">Luna's Suggestion</span>
                    </div>
                    <button
                        onClick={onCancel}
                        className="p-1 hover:bg-surface-hover rounded-full"
                    >
                        <X size={18} />
                    </button>
                </div>

                {/* Risk Assessment */}
                <div className="px-4 pt-4">
                    <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm ${getRiskColor(suggestion.risk_assessment)}`}>
                        {suggestion.risk_assessment !== 'safe' && <AlertTriangle size={14} />}
                        {getRiskLabel(suggestion.risk_assessment)}
                    </div>

                    {suggestion.detected_issues.length > 0 && (
                        <p className="text-xs text-text-tertiary mt-2">
                            Detected: {suggestion.detected_issues.join(', ')}
                        </p>
                    )}
                </div>

                {/* Side-by-side comparison */}
                <div className="p-4 grid grid-cols-2 gap-4">
                    {/* Original */}
                    <div className="p-3 bg-red-50 rounded-xl">
                        <p className="text-xs font-medium text-red-600 mb-2">Your message</p>
                        <p className="text-sm text-red-900">{suggestion.original_message}</p>
                    </div>

                    {/* Suggested */}
                    <div className="p-3 bg-green-50 rounded-xl">
                        <p className="text-xs font-medium text-green-600 mb-2 flex items-center gap-1">
                            {getToneEmoji(selectedOption.tone)}
                            {selectedOption.tone === 'recommended' ? 'Recommended' : selectedOption.tone}
                        </p>
                        <p className="text-sm text-green-900">{selectedOption.text}</p>
                    </div>
                </div>

                {/* Rationale */}
                <div className="px-4 pb-2">
                    <p className="text-xs text-text-secondary italic">
                        "{selectedOption.rationale}"
                    </p>
                </div>

                {/* Underlying Need */}
                {suggestion.underlying_need && (
                    <div className="px-4 pb-4">
                        <div className="p-3 bg-accent/10 rounded-xl">
                            <p className="text-xs font-medium text-accent mb-1">Underlying need</p>
                            <p className="text-sm text-text-secondary">{suggestion.underlying_need}</p>
                        </div>
                    </div>
                )}

                {/* Alternatives Toggle */}
                {suggestion.alternatives.length > 0 && (
                    <div className="px-4 pb-4">
                        <button
                            onClick={() => setShowAlternatives(!showAlternatives)}
                            className="flex items-center gap-2 text-sm text-accent hover:underline"
                        >
                            <ChevronRight
                                size={16}
                                className={`transition-transform ${showAlternatives ? 'rotate-90' : ''}`}
                            />
                            {showAlternatives ? 'Hide' : 'Show'} {suggestion.alternatives.length} alternative{suggestion.alternatives.length > 1 ? 's' : ''}
                        </button>

                        {showAlternatives && (
                            <div className="mt-3 space-y-2">
                                {allOptions.map((alt, idx) => (
                                    <button
                                        key={idx}
                                        onClick={() => setSelectedIndex(idx)}
                                        className={`
                                            w-full p-3 rounded-xl text-left transition-all
                                            ${selectedIndex === idx
                                                ? 'bg-accent/10 border-2 border-accent'
                                                : 'bg-surface-input border-2 border-transparent hover:border-accent/30'
                                            }
                                        `}
                                    >
                                        <div className="flex items-center gap-2 mb-1">
                                            <span>{getToneEmoji(alt.tone)}</span>
                                            <span className="text-xs font-medium capitalize">{alt.tone}</span>
                                        </div>
                                        <p className="text-sm">{alt.text}</p>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 p-4 border-t border-border-subtle bg-surface-base">
                    <Button
                        onClick={() => onAccept(selectedOption.text, selectedIndex)}
                        className="flex-1 bg-accent hover:bg-accent-hover"
                    >
                        Use This
                    </Button>
                    <Button
                        onClick={onReject}
                        variant="outline"
                        className="flex-1"
                    >
                        Send Original
                    </Button>
                </div>
            </div>
        </div>
    );
};

export default LunaSuggestionOverlay;
```

### 2. Updated MessageInput with Luna Integration

**File**: `frontend/src/components/partner-chat/MessageInput.tsx` (update)

```tsx
import React, { useState, useCallback, useRef } from 'react';
import { Send, Bot, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import LunaSuggestionOverlay from './LunaSuggestionOverlay';

interface LunaSuggestion {
    suggestion_id: string | null;
    original_message: string;
    risk_assessment: 'safe' | 'risky' | 'high_risk';
    detected_issues: string[];
    primary_suggestion: string;
    suggestion_rationale: string;
    alternatives: any[];
    underlying_need?: string;
}

interface MessageInputProps {
    conversationId: string;
    senderId: string;
    onSend: (content: string, originalContent?: string, suggestionId?: string) => void;
    onTyping: (isTyping: boolean) => void;
    disabled?: boolean;
    lunaEnabled?: boolean;
    suggestionMode?: 'always' | 'on_request' | 'high_risk_only' | 'off';
}

const MessageInput: React.FC<MessageInputProps> = ({
    conversationId,
    senderId,
    onSend,
    onTyping,
    disabled = false,
    lunaEnabled = true,
    suggestionMode = 'on_request'
}) => {
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [suggestion, setSuggestion] = useState<LunaSuggestion | null>(null);
    const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setInput(e.target.value);

        // Typing indicator with debounce
        onTyping(true);
        if (typingTimeoutRef.current) {
            clearTimeout(typingTimeoutRef.current);
        }
        typingTimeoutRef.current = setTimeout(() => {
            onTyping(false);
        }, 2000);
    };

    const requestLunaReview = async (): Promise<LunaSuggestion | null> => {
        if (!input.trim() || !lunaEnabled) return null;

        try {
            const response = await fetch(`${apiUrl}/api/partner-messages/suggest`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    conversation_id: conversationId,
                    sender_id: senderId,
                    draft_message: input.trim()
                })
            });

            if (!response.ok) throw new Error('Failed to get suggestion');

            return await response.json();
        } catch (err) {
            console.error('Luna review error:', err);
            return null;
        }
    };

    const handleSend = async () => {
        if (!input.trim() || disabled || isLoading) return;

        const messageContent = input.trim();
        setIsLoading(true);

        try {
            // Determine if we need Luna review
            if (lunaEnabled && suggestionMode !== 'off') {
                if (suggestionMode === 'always') {
                    // Always get suggestion
                    const result = await requestLunaReview();
                    if (result && result.risk_assessment !== 'safe') {
                        setSuggestion(result);
                        setIsLoading(false);
                        return; // Wait for user decision
                    }
                } else if (suggestionMode === 'high_risk_only') {
                    // Quick check, show only for high risk
                    const result = await requestLunaReview();
                    if (result && result.risk_assessment === 'high_risk') {
                        setSuggestion(result);
                        setIsLoading(false);
                        return;
                    }
                }
                // 'on_request' mode: don't auto-check, user clicks Luna button
            }

            // Send message directly
            onSend(messageContent);
            setInput('');
            onTyping(false);
        } finally {
            setIsLoading(false);
        }
    };

    const handleLunaButtonClick = async () => {
        if (!input.trim() || isLoading) return;

        setIsLoading(true);
        try {
            const result = await requestLunaReview();
            if (result) {
                if (result.risk_assessment === 'safe') {
                    // Message is fine, send it
                    onSend(input.trim());
                    setInput('');
                } else {
                    // Show suggestion
                    setSuggestion(result);
                }
            }
        } finally {
            setIsLoading(false);
        }
    };

    const handleAcceptSuggestion = async (text: string, alternativeIndex: number) => {
        if (!suggestion) return;

        // Record the response
        if (suggestion.suggestion_id) {
            try {
                await fetch(`${apiUrl}/api/partner-messages/suggestion/${suggestion.suggestion_id}/respond`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        action: 'accepted',
                        selected_alternative_index: alternativeIndex
                    })
                });
            } catch (err) {
                console.error('Error recording suggestion response:', err);
            }
        }

        // Send the accepted suggestion, storing original
        onSend(text, suggestion.original_message, suggestion.suggestion_id || undefined);
        setInput('');
        setSuggestion(null);
        onTyping(false);
    };

    const handleRejectSuggestion = async () => {
        if (!suggestion) return;

        // Record the rejection
        if (suggestion.suggestion_id) {
            try {
                await fetch(`${apiUrl}/api/partner-messages/suggestion/${suggestion.suggestion_id}/respond`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'rejected' })
                });
            } catch (err) {
                console.error('Error recording suggestion response:', err);
            }
        }

        // Send original message
        onSend(suggestion.original_message);
        setInput('');
        setSuggestion(null);
        onTyping(false);
    };

    const handleCancelSuggestion = async () => {
        if (suggestion?.suggestion_id) {
            try {
                await fetch(`${apiUrl}/api/partner-messages/suggestion/${suggestion.suggestion_id}/respond`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'ignored' })
                });
            } catch (err) {
                console.error('Error recording suggestion response:', err);
            }
        }
        setSuggestion(null);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="relative p-4 border-t border-border-subtle bg-surface-base">
            {/* Luna Suggestion Overlay */}
            {suggestion && (
                <LunaSuggestionOverlay
                    suggestion={suggestion}
                    onAccept={handleAcceptSuggestion}
                    onReject={handleRejectSuggestion}
                    onCancel={handleCancelSuggestion}
                />
            )}

            <div className="flex gap-2">
                <textarea
                    value={input}
                    onChange={handleInputChange}
                    onKeyDown={handleKeyDown}
                    placeholder="Message your partner..."
                    disabled={disabled || isLoading}
                    className="flex-1 bg-surface-input border border-border-input rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent resize-none h-[50px] max-h-[120px] disabled:opacity-50"
                />

                {/* Luna Review Button (on_request mode) */}
                {lunaEnabled && suggestionMode === 'on_request' && (
                    <Button
                        onClick={handleLunaButtonClick}
                        disabled={!input.trim() || isLoading || disabled}
                        variant="ghost"
                        className="h-[50px] w-[50px] p-0 text-accent hover:bg-accent/10"
                        title="Ask Luna to review"
                    >
                        {isLoading ? (
                            <Loader2 className="animate-spin" size={20} />
                        ) : (
                            <Bot size={20} />
                        )}
                    </Button>
                )}

                {/* Send Button */}
                <Button
                    onClick={handleSend}
                    disabled={!input.trim() || isLoading || disabled}
                    className="h-[50px] w-[50px] rounded-xl p-0 bg-accent hover:bg-accent-hover"
                >
                    {isLoading && suggestionMode !== 'on_request' ? (
                        <Loader2 className="animate-spin" size={20} />
                    ) : (
                        <Send size={20} />
                    )}
                </Button>
            </div>

            <p className="text-[10px] text-text-tertiary text-center mt-2">
                {lunaEnabled
                    ? "Luna can help you communicate better"
                    : "Press Enter to send"
                }
            </p>
        </div>
    );
};

export default MessageInput;
```

---

## Testing Checklist

### Backend Tests
- [ ] Suggestion service detects accusatory language
- [ ] Suggestion service detects known triggers
- [ ] Suggestion service generates alternatives
- [ ] Safe messages return quickly (no LLM call in high_risk_only mode)
- [ ] Suggestions stored in database
- [ ] Response recording works
- [ ] Acceptance rate calculation correct

### Frontend Tests
- [ ] Suggestion overlay appears for risky messages
- [ ] Side-by-side comparison displays correctly
- [ ] Alternatives can be selected
- [ ] Accept sends Luna's suggestion
- [ ] Reject sends original message
- [ ] Cancel closes overlay without sending
- [ ] Luna button works in on_request mode

### Integration Tests
- [ ] Full flow: type → review → accept → partner receives
- [ ] Full flow: type → review → reject → partner receives original
- [ ] Sensitivity settings affect intervention threshold
- [ ] Suggestion mode settings respected

### Privacy Tests
- [ ] Partner B never sees suggestion data
- [ ] Partner B message shows no indication of Luna involvement
- [ ] Suggestion overlay only visible to typing partner
