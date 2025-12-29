# Database Schema Reference

Complete database schema for the partner messaging feature.

## Overview

| Table | Purpose | Phase |
|-------|---------|-------|
| `partner_conversations` | One conversation per relationship | 1 |
| `partner_messages` | Individual messages with analysis | 1 |
| `partner_messaging_preferences` | User settings for Luna assistance | 2 |
| `message_suggestions` | Luna's pre-send suggestions (private) | 3 |

---

## Tech Stack & Configuration

### Database

| Component | Technology | Version |
|-----------|------------|---------|
| Database | PostgreSQL | 15+ |
| Hosting | Supabase | Latest |
| Driver | psycopg2-binary | 2.9+ |
| UUID Extension | uuid-ossp | Built-in |

### Connection Configuration

**Environment Variable** (in `backend/app/config.py`):
```python
DATABASE_URL = os.getenv("DATABASE_URL")
# Format: postgresql://user:password@host:port/database
```

### Supabase Configuration

Row Level Security (RLS) is enabled but set to public for MVP. Production should implement proper policies:

```sql
-- Example production RLS policy
CREATE POLICY "Users can only access their relationship's messages"
ON partner_messages
FOR ALL
USING (
    conversation_id IN (
        SELECT pc.id FROM partner_conversations pc
        JOIN relationship_members rm ON pc.relationship_id = rm.relationship_id
        WHERE rm.user_id = auth.uid()
    )
);
```

### Migration Execution

**Option 1: psql CLI**
```bash
psql $DATABASE_URL -f backend/app/models/migrations/009_partner_messaging.sql
```

**Option 2: Supabase Dashboard**
1. Go to SQL Editor
2. Paste migration content
3. Run

**Option 3: Python Script**
```python
from app.services.db_service import db_service

with open('backend/app/models/migrations/009_partner_messaging.sql') as f:
    sql = f.read()

with db_service.get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
```

---

## Complete Migration File

**File**: `backend/app/models/migrations/009_partner_messaging.sql`

```sql
-- ============================================
-- PARTNER MESSAGING SCHEMA
-- Migration: 009_partner_messaging
-- Description: Partner-to-partner messaging with Luna assistance
-- ============================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- ============================================
-- TABLE: partner_conversations
-- One conversation per relationship (partner-to-partner chat)
-- ============================================
CREATE TABLE IF NOT EXISTS partner_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Conversation metadata
    last_message_at TIMESTAMP WITH TIME ZONE,
    last_message_preview TEXT,
    message_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,

    -- Extensible metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- One conversation per relationship
    CONSTRAINT uq_partner_conversations_relationship UNIQUE (relationship_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_partner_conversations_relationship
    ON partner_conversations(relationship_id);
CREATE INDEX IF NOT EXISTS idx_partner_conversations_last_message
    ON partner_conversations(last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_partner_conversations_active
    ON partner_conversations(is_active) WHERE is_active = true;

-- Row Level Security (open for MVP)
ALTER TABLE partner_conversations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public access to partner_conversations"
    ON partner_conversations FOR ALL USING (true);


-- ============================================
-- TABLE: partner_messages
-- Individual messages between partners
-- ============================================
CREATE TABLE IF NOT EXISTS partner_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES partner_conversations(id) ON DELETE CASCADE,
    sender_id TEXT NOT NULL CHECK (sender_id IN ('partner_a', 'partner_b')),
    content TEXT NOT NULL,

    -- Message status
    status TEXT DEFAULT 'sent' CHECK (status IN ('sent', 'delivered', 'read')),
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    delivered_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,

    -- ============================================
    -- Analysis fields (populated async - Phase 4)
    -- ============================================
    sentiment_score FLOAT CHECK (sentiment_score >= -1.0 AND sentiment_score <= 1.0),
    sentiment_label TEXT CHECK (sentiment_label IN ('positive', 'neutral', 'negative', 'mixed')),
    emotions JSONB DEFAULT '[]'::jsonb,
    -- e.g., ["frustrated", "hurt", "hopeful"]

    detected_triggers JSONB DEFAULT '[]'::jsonb,
    -- e.g., ["you always", "you never"]

    escalation_risk TEXT CHECK (escalation_risk IN ('low', 'medium', 'high', 'critical')),

    gottman_markers JSONB DEFAULT '{}'::jsonb,
    -- e.g., {"criticism": true, "contempt": false, "defensiveness": false, "stonewalling": false}

    -- ============================================
    -- Luna intervention tracking (Phase 3)
    -- ============================================
    luna_intervened BOOLEAN DEFAULT false,
    intervention_type TEXT CHECK (intervention_type IN ('suggestion', 'warning', 'reframe')),
    intervention_accepted BOOLEAN,
    original_content TEXT,  -- stored if Luna suggestion was accepted (for analytics)

    -- Reply threading (future)
    reply_to_id UUID REFERENCES partner_messages(id),

    -- Extensible metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Soft delete
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_partner_messages_conversation
    ON partner_messages(conversation_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_partner_messages_sender
    ON partner_messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_partner_messages_status
    ON partner_messages(status);
CREATE INDEX IF NOT EXISTS idx_partner_messages_sent_at
    ON partner_messages(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_partner_messages_not_deleted
    ON partner_messages(conversation_id, sent_at DESC) WHERE deleted_at IS NULL;

-- Indexes for analytics queries
CREATE INDEX IF NOT EXISTS idx_partner_messages_sentiment
    ON partner_messages(sentiment_label) WHERE sentiment_label IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_partner_messages_escalation
    ON partner_messages(escalation_risk) WHERE escalation_risk IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_partner_messages_luna_intervened
    ON partner_messages(luna_intervened) WHERE luna_intervened = true;

-- Row Level Security
ALTER TABLE partner_messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public access to partner_messages"
    ON partner_messages FOR ALL USING (true);


-- ============================================
-- TABLE: partner_messaging_preferences
-- Per-user settings for Luna assistance
-- ============================================
CREATE TABLE IF NOT EXISTS partner_messaging_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,
    partner_id TEXT NOT NULL CHECK (partner_id IN ('partner_a', 'partner_b')),

    -- ============================================
    -- Luna assistance settings
    -- ============================================
    luna_assistance_enabled BOOLEAN DEFAULT true,
    suggestion_mode TEXT DEFAULT 'on_request'
        CHECK (suggestion_mode IN ('always', 'on_request', 'high_risk_only', 'off')),
    -- always: Luna reviews every message
    -- on_request: User clicks Luna button to request review
    -- high_risk_only: Luna only intervenes for detected high-risk messages
    -- off: No Luna involvement

    -- ============================================
    -- Active intervention settings
    -- ============================================
    intervention_enabled BOOLEAN DEFAULT true,
    intervention_sensitivity TEXT DEFAULT 'medium'
        CHECK (intervention_sensitivity IN ('low', 'medium', 'high')),
    -- low: Only obvious issues (many negative messages, severe triggers)
    -- medium: Balanced detection
    -- high: More proactive intervention

    -- ============================================
    -- Notification preferences
    -- ============================================
    push_notifications_enabled BOOLEAN DEFAULT true,
    notification_sound BOOLEAN DEFAULT true,

    -- ============================================
    -- UI preferences
    -- ============================================
    show_sentiment_indicators BOOLEAN DEFAULT false,  -- Show emoji based on sentiment
    show_read_receipts BOOLEAN DEFAULT true,
    show_typing_indicators BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- One preferences record per partner per relationship
    CONSTRAINT uq_messaging_prefs_partner UNIQUE (relationship_id, partner_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_messaging_prefs_relationship
    ON partner_messaging_preferences(relationship_id);

-- Row Level Security
ALTER TABLE partner_messaging_preferences ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public access to partner_messaging_preferences"
    ON partner_messaging_preferences FOR ALL USING (true);


-- ============================================
-- TABLE: message_suggestions
-- Luna's pre-send suggestions (private to sender)
-- ============================================
CREATE TABLE IF NOT EXISTS message_suggestions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES partner_conversations(id) ON DELETE CASCADE,
    sender_id TEXT NOT NULL CHECK (sender_id IN ('partner_a', 'partner_b')),

    -- ============================================
    -- Original message analysis
    -- ============================================
    original_message TEXT NOT NULL,
    risk_assessment TEXT NOT NULL CHECK (risk_assessment IN ('safe', 'risky', 'high_risk')),
    detected_issues JSONB DEFAULT '[]'::jsonb,
    -- e.g., ["accusatory_language", "known_trigger", "escalation_pattern", "gottman_criticism"]

    -- ============================================
    -- Luna's suggestions
    -- ============================================
    primary_suggestion TEXT NOT NULL,
    suggestion_rationale TEXT NOT NULL,
    alternatives JSONB DEFAULT '[]'::jsonb,
    -- e.g., [{"text": "...", "tone": "gentle", "rationale": "..."}]

    underlying_need TEXT,  -- The emotional need Luna detected

    -- ============================================
    -- User response tracking
    -- ============================================
    user_action TEXT CHECK (user_action IN ('accepted', 'rejected', 'modified', 'ignored')),
    final_message_id UUID REFERENCES partner_messages(id),
    selected_alternative_index INTEGER,  -- which alternative was chosen (0 = primary)

    -- ============================================
    -- Timing and context
    -- ============================================
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    responded_at TIMESTAMP WITH TIME ZONE,
    context_message_count INTEGER,  -- how many prior messages were considered

    -- Extensible metadata
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_message_suggestions_conversation
    ON message_suggestions(conversation_id);
CREATE INDEX IF NOT EXISTS idx_message_suggestions_sender
    ON message_suggestions(sender_id);
CREATE INDEX IF NOT EXISTS idx_message_suggestions_action
    ON message_suggestions(user_action) WHERE user_action IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_message_suggestions_created
    ON message_suggestions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_message_suggestions_risk
    ON message_suggestions(risk_assessment);

-- Row Level Security
ALTER TABLE message_suggestions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public access to message_suggestions"
    ON message_suggestions FOR ALL USING (true);


-- ============================================
-- TRIGGERS: Auto-update conversation on new message
-- ============================================
CREATE OR REPLACE FUNCTION update_conversation_on_message()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE partner_conversations
    SET
        last_message_at = NEW.sent_at,
        last_message_preview = LEFT(NEW.content, 100),
        message_count = message_count + 1,
        updated_at = NOW()
    WHERE id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_conversation_on_message ON partner_messages;
CREATE TRIGGER trigger_update_conversation_on_message
    AFTER INSERT ON partner_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_on_message();


-- ============================================
-- TRIGGERS: Auto-update preferences timestamp
-- ============================================
CREATE OR REPLACE FUNCTION update_messaging_prefs_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_messaging_prefs_timestamp ON partner_messaging_preferences;
CREATE TRIGGER trigger_update_messaging_prefs_timestamp
    BEFORE UPDATE ON partner_messaging_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_messaging_prefs_timestamp();


-- ============================================
-- OPTIONAL: Additional tables for analytics
-- (Only create if they don't exist from other migrations)
-- ============================================

-- Escalation events tracking
CREATE TABLE IF NOT EXISTS escalation_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,
    source TEXT NOT NULL,  -- 'partner_messaging', 'conflict', 'call', etc.
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    context TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_escalation_events_relationship
    ON escalation_events(relationship_id, created_at DESC);


-- ============================================
-- MIGRATION COMPLETE
-- ============================================
```

---

## Entity Relationship Diagram

```
┌─────────────────────┐
│    relationships    │
│  (existing table)   │
├─────────────────────┤
│ id (PK)             │
│ partner_a_id        │
│ partner_b_id        │
│ ...                 │
└──────────┬──────────┘
           │
           │ 1:1
           ▼
┌─────────────────────────────────┐
│     partner_conversations       │
├─────────────────────────────────┤
│ id (PK)                         │
│ relationship_id (FK, UNIQUE)    │
│ last_message_at                 │
│ last_message_preview            │
│ message_count                   │
│ is_active                       │
│ created_at, updated_at          │
└──────────┬──────────────────────┘
           │
           │ 1:N
           ▼
┌─────────────────────────────────┐
│       partner_messages          │
├─────────────────────────────────┤
│ id (PK)                         │
│ conversation_id (FK)            │
│ sender_id ('partner_a'|'b')     │
│ content                         │
│ status (sent|delivered|read)    │
│ sent_at, delivered_at, read_at  │
│ ─────── Analysis Fields ─────── │
│ sentiment_score, sentiment_label│
│ emotions, detected_triggers     │
│ escalation_risk, gottman_markers│
│ ─────── Luna Fields ────────── │
│ luna_intervened                 │
│ intervention_type               │
│ original_content                │
│ reply_to_id (FK, self)          │
│ deleted_at (soft delete)        │
└─────────────────────────────────┘


┌─────────────────────┐
│    relationships    │
└──────────┬──────────┘
           │
           │ 1:2 (one per partner)
           ▼
┌─────────────────────────────────────┐
│   partner_messaging_preferences     │
├─────────────────────────────────────┤
│ id (PK)                             │
│ relationship_id (FK)                │
│ partner_id ('partner_a'|'b')        │
│ ─────── Luna Settings ────────────  │
│ luna_assistance_enabled             │
│ suggestion_mode                     │
│ intervention_enabled                │
│ intervention_sensitivity            │
│ ─────── Notification Settings ────  │
│ push_notifications_enabled          │
│ notification_sound                  │
│ ─────── UI Settings ───────────────│
│ show_sentiment_indicators           │
│ show_read_receipts                  │
│ show_typing_indicators              │
│ created_at, updated_at              │
│ UNIQUE(relationship_id, partner_id) │
└─────────────────────────────────────┘


┌─────────────────────────────────┐
│     partner_conversations       │
└──────────┬──────────────────────┘
           │
           │ 1:N
           ▼
┌─────────────────────────────────┐
│      message_suggestions        │
├─────────────────────────────────┤
│ id (PK)                         │
│ conversation_id (FK)            │
│ sender_id                       │
│ ─────── Original ───────────── │
│ original_message                │
│ risk_assessment                 │
│ detected_issues                 │
│ ─────── Suggestions ────────── │
│ primary_suggestion              │
│ suggestion_rationale            │
│ alternatives (JSONB)            │
│ underlying_need                 │
│ ─────── Response ───────────── │
│ user_action                     │
│ final_message_id (FK)           │
│ selected_alternative_index      │
│ created_at, responded_at        │
└─────────────────────────────────┘
```

---

## Field Descriptions

### partner_messages.status

| Value | Description |
|-------|-------------|
| `sent` | Message saved to database, not yet confirmed received |
| `delivered` | Recipient's device acknowledged receipt |
| `read` | Recipient opened/viewed the message |

### partner_messages.escalation_risk

| Value | Description | Trigger Threshold |
|-------|-------------|-------------------|
| `low` | Normal conversation | Default |
| `medium` | Some concerning patterns | 1-2 minor issues |
| `high` | Likely to escalate | Known triggers, accusations |
| `critical` | Immediate intervention suggested | Multiple severe markers |

### partner_messaging_preferences.suggestion_mode

| Value | Description |
|-------|-------------|
| `always` | Luna reviews every message before sending |
| `on_request` | User clicks Luna button to request review |
| `high_risk_only` | Luna only shows suggestions for detected high-risk |
| `off` | No Luna suggestions (analysis still runs for dashboard) |

### partner_messaging_preferences.intervention_sensitivity

| Value | Consecutive Negative | Escalation Score | Triggers |
|-------|---------------------|------------------|----------|
| `low` | 4+ messages | > 0.8 | Severe only |
| `medium` | 3+ messages | > 0.6 | All known |
| `high` | 2+ messages | > 0.4 | Predicted too |

### message_suggestions.user_action

| Value | Description |
|-------|-------------|
| `accepted` | User sent Luna's suggested text |
| `rejected` | User sent their original message |
| `modified` | User edited the suggestion before sending |
| `ignored` | User cancelled without sending |

---

## Running the Migration

```bash
# Connect to your Supabase PostgreSQL
psql $DATABASE_URL

# Run the migration
\i backend/app/models/migrations/009_partner_messaging.sql

# Verify tables created
\dt partner_*
\dt message_suggestions
```

Or via Python:

```python
from app.services.db_service import db_service

# Read migration file
with open('backend/app/models/migrations/009_partner_messaging.sql', 'r') as f:
    migration_sql = f.read()

# Execute
with db_service.get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute(migration_sql)
    conn.commit()
```

---

## Security Notes

1. **Row Level Security**: Currently set to public for MVP. In production, implement proper RLS policies that check user membership in relationship.

2. **Sensitive Data**: `message_suggestions` contains draft messages that were never sent. Consider data retention policies.

3. **Indexes**: Analytics queries may need additional indexes based on actual usage patterns.

4. **Soft Delete**: Messages use soft delete (`deleted_at`). Implement hard delete policy after retention period.
