# Phase 4: Passive Analysis & Dashboard Integration

Intelligence phase - all messages are analyzed asynchronously to feed relationship insights.

## Goals

- Every sent message analyzed for sentiment, emotions, triggers
- Analysis runs asynchronously (doesn't block sending)
- Results stored on message records
- Analytics endpoint for dashboard integration
- Integration with existing Gottman and conflict services

## How It Differs from Phase 3

| Aspect | Phase 3 (Suggestions) | Phase 4 (Analysis) |
|--------|----------------------|-------------------|
| Timing | Before sending | After sending |
| Purpose | Help user communicate better | Track relationship patterns |
| Blocking | User waits for suggestion | Non-blocking, async |
| Visibility | Private to sender | Feeds dashboard (both see trends) |

## Prerequisites

- Phase 1 complete (messages being sent/received)
- Phase 3 helpful but not required

---

## Tech Stack & Dependencies

### Backend Dependencies

No new dependencies required - uses existing infrastructure:

```txt
# Already in requirements.txt
fastapi>=0.104.0       # BackgroundTasks for async processing
openai>=1.0.0          # LLM for analysis
pydantic>=2.0.0        # Structured output
```

### Frontend Dependencies

No new dependencies required - uses existing charting:

```json
// Already in package.json
{
  "recharts": "^2.12.7"  // For analytics visualizations
}
```

### Configuration Required

**No additional configuration needed** - uses existing LLM and database setup.

### New Files to Create

| File | Type | Description |
|------|------|-------------|
| `message_analysis_service.py` | Python | Async analysis pipeline |
| `MessagingInsights.tsx` | React | Analytics dashboard component |

### Background Task Pattern

Uses FastAPI's built-in `BackgroundTasks`:

```python
from fastapi import BackgroundTasks

@router.post("/send")
async def send_message(request: Request, background_tasks: BackgroundTasks):
    # Save message (sync - immediate)
    message = save_message(...)

    # Queue analysis (async - doesn't block response)
    background_tasks.add_task(analyze_message, message.id)

    return message
```

### Services Integration

| Service | Purpose |
|---------|---------|
| `llm_service.py` | Sentiment/emotion analysis |
| `conflict_enrichment_service.py` | Trigger detection patterns |
| `gottman_analysis_service.py` | Four Horsemen detection |
| `db_service.py` | Store analysis results |

---

## Backend Implementation

### 1. Message Analysis Service

**File**: `backend/app/services/message_analysis_service.py` (create new)

```python
"""
Message Analysis Service

Asynchronously analyzes sent messages for:
- Sentiment (positive, negative, neutral, mixed)
- Emotions (happy, sad, angry, anxious, etc.)
- Trigger phrases
- Gottman markers (Four Horsemen)
- Escalation risk

Results are stored on the message record for dashboard analytics.
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.services.db_service import db_service
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


# ============================================
# PYDANTIC MODELS FOR STRUCTURED OUTPUT
# ============================================

class MessageAnalysisResult(BaseModel):
    """LLM's analysis of a sent message."""
    sentiment_score: float = Field(..., ge=-1.0, le=1.0, description="Sentiment from -1 (negative) to 1 (positive)")
    sentiment_label: str = Field(..., description="One of: positive, negative, neutral, mixed")
    emotions: List[str] = Field(default=[], description="Detected emotions: happy, sad, angry, frustrated, anxious, hurt, hopeful, loving, etc.")
    detected_triggers: List[str] = Field(default=[], description="Trigger phrases found in message")
    escalation_risk: str = Field(..., description="One of: low, medium, high, critical")
    gottman_markers: Dict[str, bool] = Field(
        default={},
        description="Gottman Four Horsemen: criticism, contempt, defensiveness, stonewalling"
    )
    repair_attempt: bool = Field(default=False, description="Is this a repair attempt?")
    bid_for_connection: bool = Field(default=False, description="Is this a bid for connection/attention?")


class MessageAnalysisService:
    """
    Analyzes sent messages asynchronously.
    Called as a background task after message is stored.
    """

    def __init__(self):
        self.llm = llm_service

    async def analyze_message(
        self,
        message_id: str,
        content: str,
        conversation_id: str,
        relationship_id: str,
        sender_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Full analysis of a sent message.
        Updates the message record with analysis results.

        Args:
            message_id: The message UUID
            content: Message text content
            conversation_id: The conversation UUID
            relationship_id: The relationship UUID
            sender_id: 'partner_a' or 'partner_b'

        Returns:
            Analysis results dict, or None on error
        """
        try:
            # 1. Get conversation context for better analysis
            recent_messages = db_service.get_partner_messages(
                conversation_id=conversation_id,
                limit=5
            )

            # 2. Get known triggers for this relationship
            triggers = self._get_relationship_triggers(relationship_id)

            # 3. Analyze with LLM
            result = await self._analyze_with_llm(
                content=content,
                recent_messages=recent_messages,
                triggers=triggers,
                sender_id=sender_id
            )

            # 4. Update message record
            db_service.update_partner_message_analysis(
                message_id=message_id,
                sentiment_score=result.sentiment_score,
                sentiment_label=result.sentiment_label,
                emotions=result.emotions,
                detected_triggers=result.detected_triggers,
                escalation_risk=result.escalation_risk,
                gottman_markers=result.gottman_markers
            )

            # 5. If high escalation or triggers detected, update relationship intelligence
            if result.escalation_risk in ['high', 'critical'] or result.detected_triggers:
                await self._update_relationship_intelligence(
                    relationship_id=relationship_id,
                    sender_id=sender_id,
                    result=result,
                    message_content=content
                )

            logger.info(f"✅ Analyzed message {message_id}: {result.sentiment_label}, risk={result.escalation_risk}")

            return result.dict()

        except Exception as e:
            logger.error(f"Error analyzing message {message_id}: {e}")
            return None

    async def _analyze_with_llm(
        self,
        content: str,
        recent_messages: List[dict],
        triggers: List[dict],
        sender_id: str
    ) -> MessageAnalysisResult:
        """
        LLM-based message analysis.
        """
        # Build conversation context
        conversation_context = ""
        if recent_messages:
            conversation_context = "Recent conversation:\n" + "\n".join([
                f"{msg['sender_id']}: {msg['content']}"
                for msg in recent_messages[-3:]
            ])

        # Build trigger context
        trigger_phrases = [t['phrase'] for t in triggers[:20]] if triggers else []
        trigger_context = ""
        if trigger_phrases:
            trigger_context = f"Known trigger phrases for this couple: {', '.join(trigger_phrases)}"

        prompt = f"""Analyze this message sent between partners in a relationship.

{conversation_context}

MESSAGE TO ANALYZE (from {sender_id}):
"{content}"

{trigger_context}

Analyze for:
1. Sentiment: Overall tone from -1 (very negative) to 1 (very positive)
2. Emotions: What emotions are expressed or implied?
3. Triggers: Does it contain any known trigger phrases or potentially triggering language?
4. Escalation Risk: Could this message escalate conflict?
5. Gottman's Four Horsemen:
   - Criticism: Attack on character rather than specific behavior
   - Contempt: Disrespect, mockery, sarcasm, eye-rolling
   - Defensiveness: Denying responsibility, making excuses
   - Stonewalling: Withdrawing, shutting down
6. Repair Attempt: Is this trying to de-escalate or repair the connection?
7. Bid for Connection: Is this reaching out for attention, affection, or engagement?

Be accurate and nuanced. Not every message is negative - many are positive or neutral.
"""

        try:
            result = self.llm.structured_output(
                messages=[{"role": "user", "content": prompt}],
                response_model=MessageAnalysisResult,
                temperature=0.3  # Lower temperature for consistent analysis
            )
            return result
        except Exception as e:
            logger.error(f"LLM analysis error: {e}")
            # Return neutral default
            return MessageAnalysisResult(
                sentiment_score=0.0,
                sentiment_label="neutral",
                emotions=[],
                detected_triggers=[],
                escalation_risk="low",
                gottman_markers={},
                repair_attempt=False,
                bid_for_connection=False
            )

    def _get_relationship_triggers(self, relationship_id: str) -> List[dict]:
        """Get known trigger phrases for this relationship."""
        try:
            return db_service.get_trigger_phrases_for_relationship(relationship_id) or []
        except Exception:
            return []

    async def _update_relationship_intelligence(
        self,
        relationship_id: str,
        sender_id: str,
        result: MessageAnalysisResult,
        message_content: str
    ):
        """
        Update relationship-level intelligence when significant patterns detected.
        This feeds into the cross-fight intelligence system.
        """
        try:
            # Add new trigger phrases if detected
            for trigger in result.detected_triggers:
                db_service.add_detected_trigger(
                    relationship_id=relationship_id,
                    trigger_phrase=trigger,
                    source='partner_messaging',
                    detected_by=sender_id
                )

            # Track escalation patterns
            if result.escalation_risk in ['high', 'critical']:
                db_service.record_escalation_event(
                    relationship_id=relationship_id,
                    source='partner_messaging',
                    severity=result.escalation_risk,
                    context=message_content[:200]  # Truncate for storage
                )

        except Exception as e:
            logger.error(f"Error updating relationship intelligence: {e}")


# Singleton instance
message_analysis_service = MessageAnalysisService()
```

### 2. Database Service Methods for Analysis

**File**: `backend/app/services/db_service.py` (add these methods)

```python
# ============================================
# MESSAGE ANALYSIS METHODS
# ============================================

def update_partner_message_analysis(
    self,
    message_id: str,
    sentiment_score: float,
    sentiment_label: str,
    emotions: list,
    detected_triggers: list,
    escalation_risk: str,
    gottman_markers: dict
) -> bool:
    """Update a message with analysis results."""
    import json

    with self.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE partner_messages
                SET sentiment_score = %s,
                    sentiment_label = %s,
                    emotions = %s,
                    detected_triggers = %s,
                    escalation_risk = %s,
                    gottman_markers = %s
                WHERE id = %s
            """, (
                sentiment_score,
                sentiment_label,
                json.dumps(emotions),
                json.dumps(detected_triggers),
                escalation_risk,
                json.dumps(gottman_markers),
                message_id
            ))

            conn.commit()
            return cur.rowcount > 0


def get_messaging_analytics(
    self,
    relationship_id: str,
    days: int = 30
) -> dict:
    """Get messaging analytics for dashboard."""
    with self.get_connection() as conn:
        with conn.cursor() as cur:
            # Get conversation ID
            cur.execute("""
                SELECT id FROM partner_conversations
                WHERE relationship_id = %s
            """, (relationship_id,))
            row = cur.fetchone()
            if not row:
                return self._empty_analytics()

            conversation_id = row[0]

            # Message counts and sentiment distribution
            cur.execute("""
                SELECT
                    COUNT(*) as total_messages,
                    COUNT(*) FILTER (WHERE sender_id = 'partner_a') as partner_a_count,
                    COUNT(*) FILTER (WHERE sender_id = 'partner_b') as partner_b_count,
                    COUNT(*) FILTER (WHERE sentiment_label = 'positive') as positive_count,
                    COUNT(*) FILTER (WHERE sentiment_label = 'negative') as negative_count,
                    COUNT(*) FILTER (WHERE sentiment_label = 'neutral') as neutral_count,
                    COUNT(*) FILTER (WHERE escalation_risk IN ('high', 'critical')) as high_risk_count,
                    COUNT(*) FILTER (WHERE luna_intervened = true) as luna_intervened_count,
                    AVG(sentiment_score) FILTER (WHERE sentiment_score IS NOT NULL) as avg_sentiment
                FROM partner_messages
                WHERE conversation_id = %s
                  AND sent_at > NOW() - INTERVAL '%s days'
                  AND deleted_at IS NULL
            """, (conversation_id, days))

            stats = cur.fetchone()

            # Daily message trend
            cur.execute("""
                SELECT
                    DATE(sent_at) as date,
                    COUNT(*) as message_count,
                    AVG(sentiment_score) as avg_sentiment
                FROM partner_messages
                WHERE conversation_id = %s
                  AND sent_at > NOW() - INTERVAL '%s days'
                  AND deleted_at IS NULL
                GROUP BY DATE(sent_at)
                ORDER BY date
            """, (conversation_id, days))

            daily_trend = [
                {
                    "date": row[0].isoformat(),
                    "count": row[1],
                    "avg_sentiment": float(row[2]) if row[2] else 0
                }
                for row in cur.fetchall()
            ]

            # Most common emotions
            cur.execute("""
                SELECT emotion, COUNT(*) as count
                FROM partner_messages,
                     jsonb_array_elements_text(emotions) as emotion
                WHERE conversation_id = %s
                  AND sent_at > NOW() - INTERVAL '%s days'
                  AND deleted_at IS NULL
                GROUP BY emotion
                ORDER BY count DESC
                LIMIT 10
            """, (conversation_id, days))

            top_emotions = [
                {"emotion": row[0], "count": row[1]}
                for row in cur.fetchall()
            ]

            # Detected triggers
            cur.execute("""
                SELECT trigger_phrase, COUNT(*) as count
                FROM partner_messages,
                     jsonb_array_elements_text(detected_triggers) as trigger_phrase
                WHERE conversation_id = %s
                  AND sent_at > NOW() - INTERVAL '%s days'
                  AND deleted_at IS NULL
                GROUP BY trigger_phrase
                ORDER BY count DESC
                LIMIT 10
            """, (conversation_id, days))

            top_triggers = [
                {"trigger": row[0], "count": row[1]}
                for row in cur.fetchall()
            ]

            # Gottman markers
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE gottman_markers->>'criticism' = 'true') as criticism,
                    COUNT(*) FILTER (WHERE gottman_markers->>'contempt' = 'true') as contempt,
                    COUNT(*) FILTER (WHERE gottman_markers->>'defensiveness' = 'true') as defensiveness,
                    COUNT(*) FILTER (WHERE gottman_markers->>'stonewalling' = 'true') as stonewalling
                FROM partner_messages
                WHERE conversation_id = %s
                  AND sent_at > NOW() - INTERVAL '%s days'
                  AND deleted_at IS NULL
            """, (conversation_id, days))

            gottman = cur.fetchone()

            total = stats[0] or 0

            return {
                "period_days": days,
                "total_messages": total,
                "messages_by_partner": {
                    "partner_a": stats[1] or 0,
                    "partner_b": stats[2] or 0
                },
                "sentiment_distribution": {
                    "positive": stats[3] or 0,
                    "negative": stats[4] or 0,
                    "neutral": stats[5] or 0,
                    "positive_ratio": (stats[3] or 0) / total if total > 0 else 0
                },
                "average_sentiment": float(stats[8]) if stats[8] else 0,
                "high_risk_messages": stats[6] or 0,
                "luna_interventions": stats[7] or 0,
                "daily_trend": daily_trend,
                "top_emotions": top_emotions,
                "top_triggers": top_triggers,
                "gottman_markers": {
                    "criticism": gottman[0] or 0,
                    "contempt": gottman[1] or 0,
                    "defensiveness": gottman[2] or 0,
                    "stonewalling": gottman[3] or 0
                }
            }

    def _empty_analytics(self) -> dict:
        """Return empty analytics structure."""
        return {
            "period_days": 0,
            "total_messages": 0,
            "messages_by_partner": {"partner_a": 0, "partner_b": 0},
            "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0, "positive_ratio": 0},
            "average_sentiment": 0,
            "high_risk_messages": 0,
            "luna_interventions": 0,
            "daily_trend": [],
            "top_emotions": [],
            "top_triggers": [],
            "gottman_markers": {"criticism": 0, "contempt": 0, "defensiveness": 0, "stonewalling": 0}
        }


def add_detected_trigger(
    self,
    relationship_id: str,
    trigger_phrase: str,
    source: str,
    detected_by: str
) -> None:
    """Add a newly detected trigger phrase."""
    # This integrates with the existing trigger_phrases table
    # or creates a new entry if the table doesn't exist
    try:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Upsert trigger phrase
                cur.execute("""
                    INSERT INTO trigger_phrases
                        (relationship_id, phrase, source, detected_by, occurrence_count)
                    VALUES (%s, %s, %s, %s, 1)
                    ON CONFLICT (relationship_id, phrase)
                    DO UPDATE SET
                        occurrence_count = trigger_phrases.occurrence_count + 1,
                        last_detected_at = NOW()
                """, (relationship_id, trigger_phrase, source, detected_by))
                conn.commit()
    except Exception as e:
        logger.warning(f"Could not add trigger phrase: {e}")


def record_escalation_event(
    self,
    relationship_id: str,
    source: str,
    severity: str,
    context: str
) -> None:
    """Record an escalation event for pattern tracking."""
    try:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO escalation_events
                        (relationship_id, source, severity, context)
                    VALUES (%s, %s, %s, %s)
                """, (relationship_id, source, severity, context))
                conn.commit()
    except Exception as e:
        logger.warning(f"Could not record escalation event: {e}")
```

### 3. Background Task Integration

**File**: `backend/app/routes/partner_messaging_routes.py` (update send endpoint)

```python
from fastapi import BackgroundTasks
from app.services.message_analysis_service import message_analysis_service

@router.post("/send", response_model=SendMessageResponse)
async def send_message(
    request: SendMessageRequest,
    background_tasks: BackgroundTasks
):
    """
    Send a message to the partner.
    Message analysis runs asynchronously after sending.
    """
    try:
        # Get conversation for relationship_id
        conversation = db_service.get_conversation_by_id(request.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Save message
        message = db_service.save_partner_message(
            conversation_id=request.conversation_id,
            sender_id=request.sender_id,
            content=request.content,
            original_content=request.original_content if hasattr(request, 'original_content') else None,
            luna_intervened=request.luna_intervened if hasattr(request, 'luna_intervened') else False
        )

        # Queue async analysis
        background_tasks.add_task(
            message_analysis_service.analyze_message,
            message_id=message['id'],
            content=request.content,
            conversation_id=request.conversation_id,
            relationship_id=conversation['relationship_id'],
            sender_id=request.sender_id
        )

        return SendMessageResponse(
            message=PartnerMessage(**message),
            luna_suggestion=None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### 4. Analytics API Endpoint

**File**: `backend/app/routes/partner_messaging_routes.py` (add endpoint)

```python
@router.get("/analytics")
async def get_messaging_analytics(
    relationship_id: str = Query(...),
    days: int = Query(default=30, ge=1, le=365)
):
    """
    Get messaging analytics for dashboard.

    Returns:
    - Message counts and distribution
    - Sentiment trends
    - Top emotions expressed
    - Detected triggers
    - Gottman marker counts
    - Luna intervention statistics
    """
    try:
        analytics = db_service.get_messaging_analytics(
            relationship_id=relationship_id,
            days=days
        )
        return analytics
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Frontend Implementation

### 1. Messaging Analytics Component

**File**: `frontend/src/components/analytics/MessagingInsights.tsx`

```tsx
import React, { useState, useEffect } from 'react';
import { useRelationship } from '@/contexts/RelationshipContext';
import {
    MessageCircle, TrendingUp, TrendingDown, AlertTriangle,
    Heart, Frown, Smile, Meh, Bot
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

interface MessagingAnalytics {
    period_days: number;
    total_messages: number;
    messages_by_partner: { partner_a: number; partner_b: number };
    sentiment_distribution: {
        positive: number;
        negative: number;
        neutral: number;
        positive_ratio: number;
    };
    average_sentiment: number;
    high_risk_messages: number;
    luna_interventions: number;
    daily_trend: { date: string; count: number; avg_sentiment: number }[];
    top_emotions: { emotion: string; count: number }[];
    top_triggers: { trigger: string; count: number }[];
    gottman_markers: {
        criticism: number;
        contempt: number;
        defensiveness: number;
        stonewalling: number;
    };
}

const MessagingInsights: React.FC = () => {
    const { relationshipId, partnerNames } = useRelationship();
    const [analytics, setAnalytics] = useState<MessagingAnalytics | null>(null);
    const [loading, setLoading] = useState(true);
    const [period, setPeriod] = useState(30);

    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    useEffect(() => {
        const loadAnalytics = async () => {
            if (!relationshipId) return;

            try {
                const response = await fetch(
                    `${apiUrl}/api/partner-messages/analytics?relationship_id=${relationshipId}&days=${period}`
                );
                const data = await response.json();
                setAnalytics(data);
            } catch (err) {
                console.error('Failed to load messaging analytics:', err);
            } finally {
                setLoading(false);
            }
        };

        loadAnalytics();
    }, [relationshipId, period, apiUrl]);

    if (loading || !analytics) {
        return <div className="animate-pulse h-48 bg-surface-card rounded-xl" />;
    }

    const getSentimentIcon = (score: number) => {
        if (score > 0.3) return <Smile className="text-green-500" />;
        if (score < -0.3) return <Frown className="text-red-500" />;
        return <Meh className="text-amber-500" />;
    };

    const getEmotionEmoji = (emotion: string) => {
        const emojis: Record<string, string> = {
            happy: '😊', loving: '❤️', hopeful: '🌟', grateful: '🙏',
            sad: '😢', hurt: '💔', frustrated: '😤', angry: '😠',
            anxious: '😰', worried: '😟', confused: '😕', tired: '😴'
        };
        return emojis[emotion.toLowerCase()] || '💬';
    };

    return (
        <div className="space-y-6">
            {/* Period Selector */}
            <div className="flex gap-2">
                {[7, 30, 90].map((days) => (
                    <button
                        key={days}
                        onClick={() => setPeriod(days)}
                        className={`
                            px-4 py-2 rounded-full text-sm
                            ${period === days
                                ? 'bg-accent text-white'
                                : 'bg-surface-card hover:bg-surface-hover'
                            }
                        `}
                    >
                        {days} days
                    </button>
                ))}
            </div>

            {/* Overview Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card>
                    <CardContent className="p-4">
                        <div className="flex items-center gap-2 mb-2">
                            <MessageCircle size={18} className="text-accent" />
                            <span className="text-sm text-text-secondary">Messages</span>
                        </div>
                        <p className="text-2xl font-bold">{analytics.total_messages}</p>
                        <p className="text-xs text-text-tertiary">
                            {partnerNames?.partner_a}: {analytics.messages_by_partner.partner_a} |
                            {partnerNames?.partner_b}: {analytics.messages_by_partner.partner_b}
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardContent className="p-4">
                        <div className="flex items-center gap-2 mb-2">
                            {getSentimentIcon(analytics.average_sentiment)}
                            <span className="text-sm text-text-secondary">Avg Sentiment</span>
                        </div>
                        <p className="text-2xl font-bold">
                            {analytics.average_sentiment > 0 ? '+' : ''}
                            {(analytics.average_sentiment * 100).toFixed(0)}%
                        </p>
                        <p className="text-xs text-text-tertiary">
                            {analytics.sentiment_distribution.positive} positive,
                            {analytics.sentiment_distribution.negative} negative
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardContent className="p-4">
                        <div className="flex items-center gap-2 mb-2">
                            <AlertTriangle size={18} className="text-amber-500" />
                            <span className="text-sm text-text-secondary">High Risk</span>
                        </div>
                        <p className="text-2xl font-bold">{analytics.high_risk_messages}</p>
                        <p className="text-xs text-text-tertiary">
                            messages flagged
                        </p>
                    </CardContent>
                </Card>

                <Card>
                    <CardContent className="p-4">
                        <div className="flex items-center gap-2 mb-2">
                            <Bot size={18} className="text-accent" />
                            <span className="text-sm text-text-secondary">Luna Helped</span>
                        </div>
                        <p className="text-2xl font-bold">{analytics.luna_interventions}</p>
                        <p className="text-xs text-text-tertiary">
                            times
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Emotions & Triggers */}
            <div className="grid md:grid-cols-2 gap-4">
                {/* Top Emotions */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">Top Emotions</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {analytics.top_emotions.length > 0 ? (
                            <div className="flex flex-wrap gap-2">
                                {analytics.top_emotions.map((item) => (
                                    <div
                                        key={item.emotion}
                                        className="flex items-center gap-1 px-3 py-1 bg-surface-input rounded-full text-sm"
                                    >
                                        <span>{getEmotionEmoji(item.emotion)}</span>
                                        <span className="capitalize">{item.emotion}</span>
                                        <span className="text-text-tertiary">({item.count})</span>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-text-tertiary text-sm">No emotions detected yet</p>
                        )}
                    </CardContent>
                </Card>

                {/* Top Triggers */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-base flex items-center gap-2">
                            <AlertTriangle size={16} className="text-amber-500" />
                            Trigger Phrases
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        {analytics.top_triggers.length > 0 ? (
                            <div className="space-y-2">
                                {analytics.top_triggers.slice(0, 5).map((item) => (
                                    <div
                                        key={item.trigger}
                                        className="flex items-center justify-between p-2 bg-red-50 rounded-lg"
                                    >
                                        <span className="text-sm text-red-700">"{item.trigger}"</span>
                                        <span className="text-xs text-red-500">{item.count}x</span>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-text-tertiary text-sm">No triggers detected</p>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Gottman Markers */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Communication Patterns (Gottman)</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {Object.entries(analytics.gottman_markers).map(([marker, count]) => (
                            <div
                                key={marker}
                                className={`
                                    p-3 rounded-lg text-center
                                    ${count > 0 ? 'bg-red-50' : 'bg-green-50'}
                                `}
                            >
                                <p className={`text-2xl font-bold ${count > 0 ? 'text-red-600' : 'text-green-600'}`}>
                                    {count}
                                </p>
                                <p className="text-xs capitalize text-text-secondary">{marker}</p>
                            </div>
                        ))}
                    </div>
                    <p className="text-xs text-text-tertiary mt-3">
                        The "Four Horsemen" are communication patterns that predict relationship problems.
                        Lower numbers are better.
                    </p>
                </CardContent>
            </Card>
        </div>
    );
};

export default MessagingInsights;
```

### 2. Integration with Analytics Page

**File**: `frontend/src/pages/Analytics.tsx` (add MessagingInsights)

```tsx
// Add import
import MessagingInsights from '@/components/analytics/MessagingInsights';

// Add section in the Analytics page
<section className="mb-8">
    <h2 className="text-xl font-semibold mb-4">Messaging Insights</h2>
    <MessagingInsights />
</section>
```

---

## Testing Checklist

### Backend Tests
- [ ] Analysis runs asynchronously (doesn't block send)
- [ ] Message records updated with analysis
- [ ] Sentiment scores calculated correctly
- [ ] Gottman markers detected accurately
- [ ] Analytics aggregation correct
- [ ] Daily trends calculated properly
- [ ] Trigger phrases aggregated

### Frontend Tests
- [ ] Analytics component loads data
- [ ] Period selector works
- [ ] Numbers match backend data
- [ ] Empty states handled gracefully
- [ ] Emotions display correctly
- [ ] Gottman markers visualized

### Integration Tests
- [ ] Send message → analysis runs → analytics updated
- [ ] High-risk message triggers intelligence update
- [ ] Dashboard reflects recent messaging data
