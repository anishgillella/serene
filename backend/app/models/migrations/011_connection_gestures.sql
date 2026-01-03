-- ============================================
-- CONNECTION GESTURES SCHEMA
-- Migration: 011_connection_gestures
-- Description: Partner-to-partner emotional gestures
-- ============================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- TABLE: connection_gestures
-- Emotional gestures between partners
-- ============================================
CREATE TABLE IF NOT EXISTS connection_gestures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,

    -- Gesture details
    gesture_type TEXT NOT NULL CHECK (gesture_type IN ('hug', 'kiss', 'thinking_of_you')),
    sent_by TEXT NOT NULL CHECK (sent_by IN ('partner_a', 'partner_b')),

    -- Message content
    message TEXT,  -- Personalized note (max 280 chars enforced in API)
    ai_generated BOOLEAN DEFAULT false,  -- Whether message was AI-generated
    ai_context_used JSONB DEFAULT '{}'::jsonb,  -- What context AI used (for debugging)

    -- Timestamps
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    delivered_at TIMESTAMP WITH TIME ZONE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by TEXT CHECK (acknowledged_by IN ('partner_a', 'partner_b')),

    -- Response tracking
    response_gesture_id UUID REFERENCES connection_gestures(id),

    -- Metadata for analytics
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================

-- Primary query: get gestures for a relationship
CREATE INDEX IF NOT EXISTS idx_gestures_relationship
    ON connection_gestures(relationship_id);

-- Sender filtering
CREATE INDEX IF NOT EXISTS idx_gestures_sent_by
    ON connection_gestures(sent_by);

-- Type filtering for analytics
CREATE INDEX IF NOT EXISTS idx_gestures_type
    ON connection_gestures(gesture_type);

-- Chronological ordering
CREATE INDEX IF NOT EXISTS idx_gestures_sent_at
    ON connection_gestures(sent_at DESC);

-- Pending gestures (unacknowledged) - partial index
CREATE INDEX IF NOT EXISTS idx_gestures_unacknowledged
    ON connection_gestures(relationship_id, sent_by, sent_at)
    WHERE acknowledged_at IS NULL;

-- Analytics queries
CREATE INDEX IF NOT EXISTS idx_gestures_analytics
    ON connection_gestures(relationship_id, gesture_type, sent_at DESC);

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================

ALTER TABLE connection_gestures ENABLE ROW LEVEL SECURITY;

-- Open policy for MVP (will be tightened with multi-tenancy)
DROP POLICY IF EXISTS "Allow public access to connection_gestures" ON connection_gestures;
CREATE POLICY "Allow public access to connection_gestures"
    ON connection_gestures FOR ALL USING (true);
