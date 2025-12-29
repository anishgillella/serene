# Phase 2: Read Receipts, Typing Indicators & Preferences

Polish phase - adds standard chat UX features and user preferences.

## Goals

- Typing indicators visible to partner
- Read/delivered status on messages (checkmarks)
- User preferences for Luna assistance and notifications
- Settings page for messaging preferences

## Prerequisites

- Phase 1 complete (basic messaging working)

---

## Tech Stack & Dependencies

### Backend Dependencies

No new dependencies required - uses existing packages.

### Frontend Dependencies

No new dependencies required - uses existing packages.

### Configuration Required

**No additional configuration needed** - this phase extends Phase 1 infrastructure.

### New Files to Create

| File | Type | Description |
|------|------|-------------|
| - | SQL | Add to existing migration file |
| - | Python | Add methods to `db_service.py` |
| - | Python | Add endpoints to `partner_messaging_routes.py` |
| `TypingIndicator.tsx` | React | Typing dots animation |
| `MessageStatus.tsx` | React | Checkmark status icons |
| `MessagingSettings.tsx` | React | Preferences page |

---

## Backend Implementation

### 1. Database Migration Addition

**File**: `backend/app/models/migrations/009_partner_messaging.sql` (add to existing)

```sql
-- ============================================
-- PARTNER MESSAGING PREFERENCES
-- Per-user settings for Luna assistance
-- ============================================
CREATE TABLE IF NOT EXISTS partner_messaging_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,
    partner_id TEXT NOT NULL CHECK (partner_id IN ('partner_a', 'partner_b')),

    -- Luna assistance settings
    luna_assistance_enabled BOOLEAN DEFAULT true,
    suggestion_mode TEXT DEFAULT 'on_request'
        CHECK (suggestion_mode IN ('always', 'on_request', 'high_risk_only', 'off')),

    -- Active intervention settings
    intervention_enabled BOOLEAN DEFAULT true,
    intervention_sensitivity TEXT DEFAULT 'medium'
        CHECK (intervention_sensitivity IN ('low', 'medium', 'high')),

    -- Notification preferences
    push_notifications_enabled BOOLEAN DEFAULT true,
    notification_sound BOOLEAN DEFAULT true,

    -- UI preferences
    show_sentiment_indicators BOOLEAN DEFAULT false,  -- Show emoji based on sentiment
    show_read_receipts BOOLEAN DEFAULT true,
    show_typing_indicators BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- One preferences record per partner per relationship
    CONSTRAINT uq_messaging_prefs_partner UNIQUE (relationship_id, partner_id)
);

CREATE INDEX IF NOT EXISTS idx_messaging_prefs_relationship
    ON partner_messaging_preferences(relationship_id);

ALTER TABLE partner_messaging_preferences ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public access to partner_messaging_preferences"
    ON partner_messaging_preferences FOR ALL USING (true);


-- ============================================
-- FUNCTION: Update preferences timestamp
-- ============================================
CREATE OR REPLACE FUNCTION update_messaging_prefs_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_messaging_prefs_timestamp
    BEFORE UPDATE ON partner_messaging_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_messaging_prefs_timestamp();
```

### 2. Database Service Methods

**File**: `backend/app/services/db_service.py` (add these methods)

```python
# ============================================
# MESSAGING PREFERENCES METHODS
# ============================================

def get_messaging_preferences(
    self,
    relationship_id: str,
    partner_id: str
) -> dict:
    """Get messaging preferences for a partner, creating defaults if none exist."""
    with self.get_connection() as conn:
        with conn.cursor() as cur:
            # Try to get existing
            cur.execute("""
                SELECT id, relationship_id, partner_id,
                       luna_assistance_enabled, suggestion_mode,
                       intervention_enabled, intervention_sensitivity,
                       push_notifications_enabled, notification_sound,
                       show_sentiment_indicators, show_read_receipts,
                       show_typing_indicators, created_at, updated_at
                FROM partner_messaging_preferences
                WHERE relationship_id = %s AND partner_id = %s
            """, (relationship_id, partner_id))

            row = cur.fetchone()
            if row:
                return {
                    "id": str(row[0]),
                    "relationship_id": str(row[1]),
                    "partner_id": row[2],
                    "luna_assistance_enabled": row[3],
                    "suggestion_mode": row[4],
                    "intervention_enabled": row[5],
                    "intervention_sensitivity": row[6],
                    "push_notifications_enabled": row[7],
                    "notification_sound": row[8],
                    "show_sentiment_indicators": row[9],
                    "show_read_receipts": row[10],
                    "show_typing_indicators": row[11],
                    "created_at": row[12].isoformat() if row[12] else None,
                    "updated_at": row[13].isoformat() if row[13] else None
                }

            # Create defaults
            cur.execute("""
                INSERT INTO partner_messaging_preferences
                    (relationship_id, partner_id)
                VALUES (%s, %s)
                RETURNING id, relationship_id, partner_id,
                          luna_assistance_enabled, suggestion_mode,
                          intervention_enabled, intervention_sensitivity,
                          push_notifications_enabled, notification_sound,
                          show_sentiment_indicators, show_read_receipts,
                          show_typing_indicators
            """, (relationship_id, partner_id))

            row = cur.fetchone()
            conn.commit()

            return {
                "id": str(row[0]),
                "relationship_id": str(row[1]),
                "partner_id": row[2],
                "luna_assistance_enabled": row[3],
                "suggestion_mode": row[4],
                "intervention_enabled": row[5],
                "intervention_sensitivity": row[6],
                "push_notifications_enabled": row[7],
                "notification_sound": row[8],
                "show_sentiment_indicators": row[9],
                "show_read_receipts": row[10],
                "show_typing_indicators": row[11],
                "created_at": None,
                "updated_at": None
            }


def update_messaging_preferences(
    self,
    relationship_id: str,
    partner_id: str,
    updates: dict
) -> dict:
    """Update messaging preferences for a partner."""
    # Build dynamic update query
    allowed_fields = [
        'luna_assistance_enabled', 'suggestion_mode',
        'intervention_enabled', 'intervention_sensitivity',
        'push_notifications_enabled', 'notification_sound',
        'show_sentiment_indicators', 'show_read_receipts',
        'show_typing_indicators'
    ]

    set_clauses = []
    values = []
    for field in allowed_fields:
        if field in updates:
            set_clauses.append(f"{field} = %s")
            values.append(updates[field])

    if not set_clauses:
        return self.get_messaging_preferences(relationship_id, partner_id)

    values.extend([relationship_id, partner_id])

    with self.get_connection() as conn:
        with conn.cursor() as cur:
            # Upsert preferences
            cur.execute(f"""
                INSERT INTO partner_messaging_preferences
                    (relationship_id, partner_id, {', '.join(updates.keys())})
                VALUES (%s, %s, {', '.join(['%s'] * len(updates))})
                ON CONFLICT (relationship_id, partner_id)
                DO UPDATE SET {', '.join(set_clauses)}
                RETURNING id
            """, (relationship_id, partner_id, *updates.values(), *values[:-2]))

            conn.commit()

    return self.get_messaging_preferences(relationship_id, partner_id)


def get_unread_message_count(
    self,
    conversation_id: str,
    partner_id: str
) -> int:
    """Get count of unread messages for a partner."""
    with self.get_connection() as conn:
        with conn.cursor() as cur:
            # Unread = messages from other partner that haven't been read
            other_partner = 'partner_b' if partner_id == 'partner_a' else 'partner_a'
            cur.execute("""
                SELECT COUNT(*)
                FROM partner_messages
                WHERE conversation_id = %s
                  AND sender_id = %s
                  AND read_at IS NULL
                  AND deleted_at IS NULL
            """, (conversation_id, other_partner))

            return cur.fetchone()[0]


def mark_messages_as_read(
    self,
    conversation_id: str,
    reader_partner_id: str
) -> list:
    """Mark all messages from other partner as read. Returns list of updated message IDs."""
    with self.get_connection() as conn:
        with conn.cursor() as cur:
            other_partner = 'partner_b' if reader_partner_id == 'partner_a' else 'partner_a'
            cur.execute("""
                UPDATE partner_messages
                SET status = 'read', read_at = NOW()
                WHERE conversation_id = %s
                  AND sender_id = %s
                  AND read_at IS NULL
                  AND deleted_at IS NULL
                RETURNING id
            """, (conversation_id, other_partner))

            rows = cur.fetchall()
            conn.commit()

            return [str(row[0]) for row in rows]
```

### 3. Pydantic Models for Preferences

**File**: `backend/app/models/schemas.py` (add these models)

```python
# ============================================
# MESSAGING PREFERENCES MODELS
# ============================================

class MessagingPreferences(BaseModel):
    id: str
    relationship_id: str
    partner_id: str

    # Luna assistance
    luna_assistance_enabled: bool = True
    suggestion_mode: str = 'on_request'  # 'always', 'on_request', 'high_risk_only', 'off'

    # Intervention
    intervention_enabled: bool = True
    intervention_sensitivity: str = 'medium'  # 'low', 'medium', 'high'

    # Notifications
    push_notifications_enabled: bool = True
    notification_sound: bool = True

    # UI
    show_sentiment_indicators: bool = False
    show_read_receipts: bool = True
    show_typing_indicators: bool = True

    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UpdatePreferencesRequest(BaseModel):
    luna_assistance_enabled: Optional[bool] = None
    suggestion_mode: Optional[str] = Field(
        default=None,
        pattern='^(always|on_request|high_risk_only|off)$'
    )
    intervention_enabled: Optional[bool] = None
    intervention_sensitivity: Optional[str] = Field(
        default=None,
        pattern='^(low|medium|high)$'
    )
    push_notifications_enabled: Optional[bool] = None
    notification_sound: Optional[bool] = None
    show_sentiment_indicators: Optional[bool] = None
    show_read_receipts: Optional[bool] = None
    show_typing_indicators: Optional[bool] = None
```

### 4. API Routes for Preferences

**File**: `backend/app/routes/partner_messaging_routes.py` (add these endpoints)

```python
from app.models.schemas import MessagingPreferences, UpdatePreferencesRequest

@router.get("/preferences", response_model=MessagingPreferences)
async def get_preferences(
    relationship_id: str = Query(...),
    partner_id: str = Query(..., pattern='^(partner_a|partner_b)$')
):
    """Get messaging preferences for a partner."""
    try:
        prefs = db_service.get_messaging_preferences(relationship_id, partner_id)
        return MessagingPreferences(**prefs)
    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/preferences", response_model=MessagingPreferences)
async def update_preferences(
    relationship_id: str = Query(...),
    partner_id: str = Query(..., pattern='^(partner_a|partner_b)$'),
    updates: UpdatePreferencesRequest = None
):
    """Update messaging preferences for a partner."""
    try:
        # Convert to dict, excluding None values
        update_dict = {k: v for k, v in updates.dict().items() if v is not None}

        prefs = db_service.update_messaging_preferences(
            relationship_id=relationship_id,
            partner_id=partner_id,
            updates=update_dict
        )
        return MessagingPreferences(**prefs)
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unread-count")
async def get_unread_count(
    conversation_id: str = Query(...),
    partner_id: str = Query(..., pattern='^(partner_a|partner_b)$')
):
    """Get count of unread messages for a partner."""
    try:
        count = db_service.get_unread_message_count(conversation_id, partner_id)
        return {"unread_count": count}
    except Exception as e:
        logger.error(f"Error getting unread count: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mark-all-read")
async def mark_all_read(
    conversation_id: str = Query(...),
    partner_id: str = Query(..., pattern='^(partner_a|partner_b)$')
):
    """Mark all messages from partner as read."""
    try:
        message_ids = db_service.mark_messages_as_read(conversation_id, partner_id)
        return {
            "success": True,
            "messages_marked": len(message_ids),
            "message_ids": message_ids
        }
    except Exception as e:
        logger.error(f"Error marking as read: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Frontend Implementation

### 1. Typing Indicator Component

**File**: `frontend/src/components/partner-chat/TypingIndicator.tsx`

```tsx
import React from 'react';

interface TypingIndicatorProps {
    partnerName?: string;
}

const TypingIndicator: React.FC<TypingIndicatorProps> = ({ partnerName = 'Partner' }) => {
    return (
        <div className="flex items-center gap-2 px-4 py-2">
            <div className="flex gap-1">
                <span
                    className="w-2 h-2 bg-text-tertiary rounded-full animate-bounce"
                    style={{ animationDelay: '0ms' }}
                />
                <span
                    className="w-2 h-2 bg-text-tertiary rounded-full animate-bounce"
                    style={{ animationDelay: '150ms' }}
                />
                <span
                    className="w-2 h-2 bg-text-tertiary rounded-full animate-bounce"
                    style={{ animationDelay: '300ms' }}
                />
            </div>
            <span className="text-xs text-text-tertiary">
                {partnerName} is typing...
            </span>
        </div>
    );
};

export default TypingIndicator;
```

### 2. Message Status Component

**File**: `frontend/src/components/partner-chat/MessageStatus.tsx`

```tsx
import React from 'react';
import { Check, CheckCheck } from 'lucide-react';

interface MessageStatusProps {
    status: 'sent' | 'delivered' | 'read';
    showReadReceipts?: boolean;
}

const MessageStatus: React.FC<MessageStatusProps> = ({
    status,
    showReadReceipts = true
}) => {
    if (!showReadReceipts) return null;

    switch (status) {
        case 'sent':
            return (
                <Check
                    size={14}
                    className="text-text-tertiary"
                    aria-label="Sent"
                />
            );
        case 'delivered':
            return (
                <CheckCheck
                    size={14}
                    className="text-text-tertiary"
                    aria-label="Delivered"
                />
            );
        case 'read':
            return (
                <CheckCheck
                    size={14}
                    className="text-accent"
                    aria-label="Read"
                />
            );
        default:
            return null;
    }
};

export default MessageStatus;
```

### 3. Updated MessageBubble with Status

**File**: `frontend/src/components/partner-chat/MessageBubble.tsx`

```tsx
import React from 'react';
import MessageStatus from './MessageStatus';

interface Message {
    id: string;
    sender_id: string;
    content: string;
    status: string;
    sent_at: string;
}

interface MessageBubbleProps {
    message: Message;
    isOwnMessage: boolean;
    showReadReceipts?: boolean;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({
    message,
    isOwnMessage,
    showReadReceipts = true
}) => {
    const formatTime = (timestamp: string) => {
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    return (
        <div className={`flex ${isOwnMessage ? 'justify-end' : 'justify-start'} mb-2`}>
            <div
                className={`
                    max-w-[75%] rounded-2xl px-4 py-2
                    ${isOwnMessage
                        ? 'bg-accent text-white rounded-br-sm'
                        : 'bg-surface-card border border-border-subtle rounded-bl-sm'
                    }
                `}
            >
                <p className="text-sm leading-relaxed">{message.content}</p>

                <div className={`
                    flex items-center gap-1 mt-1
                    ${isOwnMessage ? 'justify-end' : 'justify-start'}
                `}>
                    <span className={`
                        text-[10px]
                        ${isOwnMessage ? 'text-white/70' : 'text-text-tertiary'}
                    `}>
                        {formatTime(message.sent_at)}
                    </span>

                    {isOwnMessage && (
                        <MessageStatus
                            status={message.status as 'sent' | 'delivered' | 'read'}
                            showReadReceipts={showReadReceipts}
                        />
                    )}
                </div>
            </div>
        </div>
    );
};

export default MessageBubble;
```

### 4. Messaging Settings Page

**File**: `frontend/src/pages/MessagingSettings.tsx`

```tsx
import React, { useState, useEffect } from 'react';
import { useRelationship } from '@/contexts/RelationshipContext';
import { ArrowLeft, Bot, Bell, Eye, Loader2 } from 'lucide-react';
import { Link } from 'react-router-dom';

interface Preferences {
    luna_assistance_enabled: boolean;
    suggestion_mode: string;
    intervention_enabled: boolean;
    intervention_sensitivity: string;
    push_notifications_enabled: boolean;
    notification_sound: boolean;
    show_sentiment_indicators: boolean;
    show_read_receipts: boolean;
    show_typing_indicators: boolean;
}

const MessagingSettings: React.FC = () => {
    const { relationshipId, partnerId } = useRelationship();
    const [preferences, setPreferences] = useState<Preferences | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    useEffect(() => {
        const loadPreferences = async () => {
            if (!relationshipId || !partnerId) return;

            try {
                const response = await fetch(
                    `${apiUrl}/api/partner-messages/preferences?relationship_id=${relationshipId}&partner_id=${partnerId}`
                );
                const data = await response.json();
                setPreferences(data);
            } catch (err) {
                console.error('Failed to load preferences:', err);
            } finally {
                setLoading(false);
            }
        };

        loadPreferences();
    }, [relationshipId, partnerId, apiUrl]);

    const updatePreference = async (key: keyof Preferences, value: any) => {
        if (!preferences) return;

        setSaving(true);
        const newPrefs = { ...preferences, [key]: value };
        setPreferences(newPrefs);

        try {
            await fetch(
                `${apiUrl}/api/partner-messages/preferences?relationship_id=${relationshipId}&partner_id=${partnerId}`,
                {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ [key]: value })
                }
            );
        } catch (err) {
            console.error('Failed to save preference:', err);
            // Revert on error
            setPreferences(preferences);
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <Loader2 className="animate-spin" size={32} />
            </div>
        );
    }

    if (!preferences) return null;

    return (
        <div className="max-w-lg mx-auto p-4">
            {/* Header */}
            <div className="flex items-center gap-3 mb-6">
                <Link to="/chat" className="p-2 hover:bg-surface-hover rounded-full">
                    <ArrowLeft size={20} />
                </Link>
                <h1 className="text-xl font-semibold">Chat Settings</h1>
                {saving && <Loader2 className="animate-spin ml-auto" size={16} />}
            </div>

            {/* Luna Assistance Section */}
            <section className="mb-8">
                <div className="flex items-center gap-2 mb-4">
                    <Bot size={20} className="text-accent" />
                    <h2 className="font-medium">Luna Assistance</h2>
                </div>

                <div className="space-y-4">
                    <ToggleSetting
                        label="Enable Luna Assistance"
                        description="Let Luna help you communicate better"
                        value={preferences.luna_assistance_enabled}
                        onChange={(v) => updatePreference('luna_assistance_enabled', v)}
                    />

                    {preferences.luna_assistance_enabled && (
                        <>
                            <SelectSetting
                                label="Suggestion Mode"
                                description="When should Luna offer suggestions?"
                                value={preferences.suggestion_mode}
                                options={[
                                    { value: 'always', label: 'Always (review every message)' },
                                    { value: 'on_request', label: 'On Request (tap Luna button)' },
                                    { value: 'high_risk_only', label: 'High Risk Only (automatic for risky messages)' },
                                    { value: 'off', label: 'Off (no suggestions)' }
                                ]}
                                onChange={(v) => updatePreference('suggestion_mode', v)}
                            />

                            <ToggleSetting
                                label="Active Intervention"
                                description="Luna warns you about potentially harmful messages"
                                value={preferences.intervention_enabled}
                                onChange={(v) => updatePreference('intervention_enabled', v)}
                            />

                            {preferences.intervention_enabled && (
                                <SelectSetting
                                    label="Intervention Sensitivity"
                                    description="How sensitive should Luna be?"
                                    value={preferences.intervention_sensitivity}
                                    options={[
                                        { value: 'low', label: 'Low (only obvious issues)' },
                                        { value: 'medium', label: 'Medium (balanced)' },
                                        { value: 'high', label: 'High (more proactive)' }
                                    ]}
                                    onChange={(v) => updatePreference('intervention_sensitivity', v)}
                                />
                            )}
                        </>
                    )}
                </div>
            </section>

            {/* Notifications Section */}
            <section className="mb-8">
                <div className="flex items-center gap-2 mb-4">
                    <Bell size={20} className="text-accent" />
                    <h2 className="font-medium">Notifications</h2>
                </div>

                <div className="space-y-4">
                    <ToggleSetting
                        label="Push Notifications"
                        description="Get notified of new messages"
                        value={preferences.push_notifications_enabled}
                        onChange={(v) => updatePreference('push_notifications_enabled', v)}
                    />

                    <ToggleSetting
                        label="Notification Sound"
                        description="Play sound for new messages"
                        value={preferences.notification_sound}
                        onChange={(v) => updatePreference('notification_sound', v)}
                    />
                </div>
            </section>

            {/* Display Section */}
            <section className="mb-8">
                <div className="flex items-center gap-2 mb-4">
                    <Eye size={20} className="text-accent" />
                    <h2 className="font-medium">Display</h2>
                </div>

                <div className="space-y-4">
                    <ToggleSetting
                        label="Read Receipts"
                        description="Show when messages are read"
                        value={preferences.show_read_receipts}
                        onChange={(v) => updatePreference('show_read_receipts', v)}
                    />

                    <ToggleSetting
                        label="Typing Indicators"
                        description="Show when partner is typing"
                        value={preferences.show_typing_indicators}
                        onChange={(v) => updatePreference('show_typing_indicators', v)}
                    />

                    <ToggleSetting
                        label="Sentiment Indicators"
                        description="Show emoji based on message sentiment"
                        value={preferences.show_sentiment_indicators}
                        onChange={(v) => updatePreference('show_sentiment_indicators', v)}
                    />
                </div>
            </section>
        </div>
    );
};

// Helper Components
const ToggleSetting: React.FC<{
    label: string;
    description: string;
    value: boolean;
    onChange: (value: boolean) => void;
}> = ({ label, description, value, onChange }) => (
    <div className="flex items-center justify-between p-3 bg-surface-card rounded-xl">
        <div>
            <p className="font-medium text-sm">{label}</p>
            <p className="text-xs text-text-tertiary">{description}</p>
        </div>
        <button
            onClick={() => onChange(!value)}
            className={`
                w-12 h-6 rounded-full transition-colors relative
                ${value ? 'bg-accent' : 'bg-surface-input'}
            `}
        >
            <span className={`
                absolute top-1 w-4 h-4 bg-white rounded-full transition-transform
                ${value ? 'left-7' : 'left-1'}
            `} />
        </button>
    </div>
);

const SelectSetting: React.FC<{
    label: string;
    description: string;
    value: string;
    options: { value: string; label: string }[];
    onChange: (value: string) => void;
}> = ({ label, description, value, options, onChange }) => (
    <div className="p-3 bg-surface-card rounded-xl">
        <p className="font-medium text-sm mb-1">{label}</p>
        <p className="text-xs text-text-tertiary mb-3">{description}</p>
        <select
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="w-full p-2 bg-surface-input border border-border-input rounded-lg text-sm"
        >
            {options.map((opt) => (
                <option key={opt.value} value={opt.value}>
                    {opt.label}
                </option>
            ))}
        </select>
    </div>
);

export default MessagingSettings;
```

---

## Testing Checklist

### Backend Tests
- [ ] Preferences created with defaults on first access
- [ ] Preferences update correctly
- [ ] Invalid preference values rejected
- [ ] Unread count returns correct number
- [ ] Mark all read updates multiple messages

### Frontend Tests
- [ ] Typing indicator appears when partner types
- [ ] Typing indicator disappears after timeout
- [ ] Read receipts show correct status (sent/delivered/read)
- [ ] Settings page loads preferences
- [ ] Settings changes save and persist
- [ ] Toggle animations work smoothly

### Integration Tests
- [ ] Partner A sees typing when Partner B types
- [ ] Read receipts update across WebSocket
- [ ] Preferences persist after logout/login
