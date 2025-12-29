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
DROP POLICY IF EXISTS "Allow public access to partner_conversations" ON partner_conversations;
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
    detected_triggers JSONB DEFAULT '[]'::jsonb,
    escalation_risk TEXT CHECK (escalation_risk IN ('low', 'medium', 'high', 'critical')),
    gottman_markers JSONB DEFAULT '{}'::jsonb,

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
DROP POLICY IF EXISTS "Allow public access to partner_messages" ON partner_messages;
CREATE POLICY "Allow public access to partner_messages"
    ON partner_messages FOR ALL USING (true);


-- ============================================
-- TABLE: partner_messaging_preferences
-- Per-user settings for Luna assistance (Phase 2)
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
    show_sentiment_indicators BOOLEAN DEFAULT false,
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
DROP POLICY IF EXISTS "Allow public access to partner_messaging_preferences" ON partner_messaging_preferences;
CREATE POLICY "Allow public access to partner_messaging_preferences"
    ON partner_messaging_preferences FOR ALL USING (true);


-- ============================================
-- TABLE: message_suggestions
-- Luna's pre-send suggestions (private to sender) - Phase 3
-- ============================================
CREATE TABLE IF NOT EXISTS message_suggestions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES partner_conversations(id) ON DELETE CASCADE,
    sender_id TEXT NOT NULL CHECK (sender_id IN ('partner_a', 'partner_b')),

    -- Original message analysis
    original_message TEXT NOT NULL,
    risk_assessment TEXT NOT NULL CHECK (risk_assessment IN ('safe', 'risky', 'high_risk')),
    detected_issues JSONB DEFAULT '[]'::jsonb,

    -- Luna's suggestions
    primary_suggestion TEXT NOT NULL,
    suggestion_rationale TEXT NOT NULL,
    alternatives JSONB DEFAULT '[]'::jsonb,
    underlying_need TEXT,

    -- User response tracking
    user_action TEXT CHECK (user_action IN ('accepted', 'rejected', 'modified', 'ignored')),
    final_message_id UUID REFERENCES partner_messages(id),
    selected_alternative_index INTEGER,

    -- Timing and context
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    responded_at TIMESTAMP WITH TIME ZONE,
    context_message_count INTEGER,

    metadata JSONB DEFAULT '{}'::jsonb
);

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

ALTER TABLE message_suggestions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public access to message_suggestions" ON message_suggestions;
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
-- MIGRATION COMPLETE
-- ============================================
