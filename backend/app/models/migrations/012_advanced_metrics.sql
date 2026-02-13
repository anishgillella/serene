-- Migration 012: Advanced Metrics Tables
-- Adds attachment_style_tracking, bid_response_tracking, repair_plan_compliance

-- ============================================================================
-- ATTACHMENT STYLE TRACKING
-- ============================================================================
CREATE TABLE IF NOT EXISTS attachment_style_tracking (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    relationship_id UUID NOT NULL REFERENCES relationships(id),
    partner VARCHAR(20) NOT NULL CHECK (partner IN ('partner_a', 'partner_b')),
    primary_style VARCHAR(30) NOT NULL,
    secondary_style VARCHAR(30),
    confidence FLOAT NOT NULL,
    behavioral_indicators JSONB DEFAULT '{}',
    summary TEXT,
    interaction_dynamic TEXT,
    conflicts_analyzed INTEGER DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(relationship_id, partner)
);

CREATE INDEX IF NOT EXISTS idx_attachment_relationship
    ON attachment_style_tracking(relationship_id);

-- ============================================================================
-- BID-RESPONSE TRACKING
-- ============================================================================
CREATE TABLE IF NOT EXISTS bid_response_tracking (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    relationship_id UUID NOT NULL,
    conflict_id UUID NOT NULL,
    partner_making_bid VARCHAR(20) NOT NULL,
    bid_type VARCHAR(50) NOT NULL,
    response_type VARCHAR(20) NOT NULL CHECK (response_type IN ('toward', 'away', 'against')),
    message_sequence INTEGER,
    bid_text TEXT,
    response_text TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bid_response_relationship
    ON bid_response_tracking(relationship_id);
CREATE INDEX IF NOT EXISTS idx_bid_response_conflict
    ON bid_response_tracking(conflict_id);

-- ============================================================================
-- REPAIR PLAN COMPLIANCE
-- ============================================================================
CREATE TABLE IF NOT EXISTS repair_plan_compliance (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    repair_plan_id UUID NOT NULL,
    conflict_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    partner VARCHAR(20) NOT NULL,
    step_index INTEGER NOT NULL,
    step_description TEXT NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(repair_plan_id, step_index, partner)
);

CREATE INDEX IF NOT EXISTS idx_compliance_conflict
    ON repair_plan_compliance(conflict_id);
CREATE INDEX IF NOT EXISTS idx_compliance_relationship
    ON repair_plan_compliance(relationship_id);

-- Add compliance_status column to repair_plans if it exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'repair_plans') THEN
        ALTER TABLE repair_plans ADD COLUMN IF NOT EXISTS
            compliance_status VARCHAR(20) DEFAULT 'pending';
    END IF;
END $$;
