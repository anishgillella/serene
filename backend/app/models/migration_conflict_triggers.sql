-- Migration: Add conflict triggers and escalation tracking
-- Phase 1: Data Capture & Enrichment
-- Purpose: Capture trigger phrases, conflict linkages, and unmet needs

-- ============================================================================
-- 1. ALTER conflicts TABLE - Add conflict relationship and enrichment fields
-- ============================================================================

ALTER TABLE conflicts ADD COLUMN IF NOT EXISTS (
    -- Conflict Relationships
    parent_conflict_id UUID REFERENCES conflicts(id),
    is_continuation BOOLEAN DEFAULT FALSE,
    days_since_related_conflict INT,

    -- Emotional Context
    resentment_level INT CHECK (resentment_level >= 1 AND resentment_level <= 10),
    unmet_needs TEXT[] DEFAULT '{}',

    -- Analysis Flags
    has_past_references BOOLEAN DEFAULT FALSE,
    conflict_chain_id UUID,

    -- Status tracking
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for conflict relationships
CREATE INDEX IF NOT EXISTS idx_conflicts_parent_conflict_id ON conflicts(parent_conflict_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_conflict_chain_id ON conflicts(conflict_chain_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_resentment_level ON conflicts(resentment_level);
CREATE INDEX IF NOT EXISTS idx_conflicts_is_continuation ON conflicts(is_continuation);
CREATE INDEX IF NOT EXISTS idx_conflicts_is_resolved ON conflicts(is_resolved);

-- ============================================================================
-- 2. CREATE trigger_phrases TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS trigger_phrases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,

    -- Phrase Content
    phrase TEXT NOT NULL,
    phrase_category VARCHAR(100),
    -- Categories: 'temporal_reference', 'passive_aggressive', 'blame', 'dismissal', 'threat', 'dismissal_of_feelings', 'accusation'

    -- Context
    conflict_id UUID NOT NULL REFERENCES conflicts(id) ON DELETE CASCADE,
    speaker VARCHAR(50), -- 'partner_a' or 'partner_b'
    timestamp_in_transcript INT, -- seconds into transcript where phrase appears
    full_sentence TEXT, -- full sentence context

    -- Analysis
    emotional_intensity INT CHECK (emotional_intensity >= 1 AND emotional_intensity <= 10),
    references_past_conflict BOOLEAN DEFAULT FALSE,
    past_conflict_id UUID REFERENCES conflicts(id) ON DELETE SET NULL,

    -- Tracking & Patterns
    frequency INT DEFAULT 1, -- how many times this phrase used across all conflicts
    last_used_at TIMESTAMP WITH TIME ZONE,
    is_pattern_trigger BOOLEAN DEFAULT FALSE, -- does this tend to escalate?
    escalation_correlation DECIMAL(3,2), -- 0.0-1.0, how often does this trigger big fights?

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for trigger_phrases
CREATE INDEX IF NOT EXISTS idx_trigger_phrases_relationship ON trigger_phrases(relationship_id);
CREATE INDEX IF NOT EXISTS idx_trigger_phrases_conflict ON trigger_phrases(conflict_id);
CREATE INDEX IF NOT EXISTS idx_trigger_phrases_phrase ON trigger_phrases(phrase);
CREATE INDEX IF NOT EXISTS idx_trigger_phrases_category ON trigger_phrases(phrase_category);
CREATE INDEX IF NOT EXISTS idx_trigger_phrases_is_pattern ON trigger_phrases(is_pattern_trigger);
CREATE INDEX IF NOT EXISTS idx_trigger_phrases_speaker ON trigger_phrases(speaker);
CREATE INDEX IF NOT EXISTS idx_trigger_phrases_emotional_intensity ON trigger_phrases(emotional_intensity);

-- Enable RLS
ALTER TABLE trigger_phrases ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public access to trigger_phrases" ON trigger_phrases FOR ALL USING (true);

-- ============================================================================
-- 3. CREATE unmet_needs TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS unmet_needs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,
    conflict_id UUID NOT NULL REFERENCES conflicts(id) ON DELETE CASCADE,

    -- Need Content
    need VARCHAR(100), -- e.g., 'feeling_heard', 'trust', 'appreciation', 'respect', 'autonomy', 'security', 'intimacy', 'validation'
    identified_by VARCHAR(50), -- 'gpt_analysis' or 'manual'
    confidence DECIMAL(3,2), -- 0.0-1.0, how confident is the LLM about this need?

    -- Context
    speaker VARCHAR(50), -- 'partner_a' or 'partner_b' or 'both'
    evidence TEXT, -- quote or context from transcript

    -- Track Recurrence & Chronicity
    first_identified_at TIMESTAMP WITH TIME ZONE,
    times_identified INT DEFAULT 1, -- appears in how many conflicts?
    is_chronic BOOLEAN DEFAULT FALSE, -- shows up in 3+ conflicts
    appears_in_percentage DECIMAL(5,2), -- what % of their conflicts

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for unmet_needs
CREATE INDEX IF NOT EXISTS idx_unmet_needs_relationship ON unmet_needs(relationship_id);
CREATE INDEX IF NOT EXISTS idx_unmet_needs_conflict ON unmet_needs(conflict_id);
CREATE INDEX IF NOT EXISTS idx_unmet_needs_need ON unmet_needs(need);
CREATE INDEX IF NOT EXISTS idx_unmet_needs_chronic ON unmet_needs(is_chronic);
CREATE INDEX IF NOT EXISTS idx_unmet_needs_speaker ON unmet_needs(speaker);

-- Enable RLS
ALTER TABLE unmet_needs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public access to unmet_needs" ON unmet_needs FOR ALL USING (true);

-- ============================================================================
-- 4. CREATE conflict_enrichment TABLE (optional, for caching enrichment results)
-- ============================================================================

CREATE TABLE IF NOT EXISTS conflict_enrichment (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conflict_id UUID NOT NULL UNIQUE REFERENCES conflicts(id) ON DELETE CASCADE,
    relationship_id UUID NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,

    -- Enrichment Results (cached from LLM analysis)
    parent_conflict_id UUID REFERENCES conflicts(id) ON DELETE SET NULL,
    trigger_phrases_count INT DEFAULT 0,
    unmet_needs_count INT DEFAULT 0,
    resentment_level INT,
    has_past_references BOOLEAN DEFAULT FALSE,
    identified_chain_id UUID,

    -- Metadata
    enriched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    enrichment_confidence DECIMAL(3,2), -- 0.0-1.0, how confident is the analysis?
    metadata JSONB DEFAULT '{}'::jsonb,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for conflict_enrichment
CREATE INDEX IF NOT EXISTS idx_conflict_enrichment_conflict ON conflict_enrichment(conflict_id);
CREATE INDEX IF NOT EXISTS idx_conflict_enrichment_relationship ON conflict_enrichment(relationship_id);
CREATE INDEX IF NOT EXISTS idx_conflict_enrichment_enriched_at ON conflict_enrichment(enriched_at DESC);

-- Enable RLS
ALTER TABLE conflict_enrichment ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public access to conflict_enrichment" ON conflict_enrichment FOR ALL USING (true);

-- ============================================================================
-- 5. CREATE VIEW for Conflict Chains (for easier querying)
-- ============================================================================

CREATE OR REPLACE VIEW conflict_chains AS
SELECT
    cf.id as conflict_id,
    cf.relationship_id,
    cf.parent_conflict_id,
    cf.conflict_chain_id,
    cf.resentment_level,
    cf.unmet_needs,
    cf.is_resolved,
    cf.started_at,
    COUNT(*) OVER (PARTITION BY cf.conflict_chain_id) as chain_length
FROM conflicts cf
WHERE cf.conflict_chain_id IS NOT NULL
ORDER BY cf.started_at DESC;

-- ============================================================================
-- 6. CREATE VIEW for Trigger Analysis (for easier querying)
-- ============================================================================

CREATE OR REPLACE VIEW trigger_phrase_analysis AS
SELECT
    tp.phrase,
    tp.phrase_category,
    tp.relationship_id,
    tp.speaker,
    COUNT(*) as usage_count,
    AVG(tp.emotional_intensity) as avg_emotional_intensity,
    COUNT(CASE WHEN tp.is_pattern_trigger THEN 1 END)::FLOAT / COUNT(*) as escalation_rate,
    MAX(tp.last_used_at) as most_recent_use,
    ARRAY_AGG(DISTINCT tp.conflict_id) as conflict_ids
FROM trigger_phrases tp
GROUP BY tp.phrase, tp.phrase_category, tp.relationship_id, tp.speaker
ORDER BY usage_count DESC, avg_emotional_intensity DESC;

-- ============================================================================
-- 7. CREATE VIEW for Unmet Needs Analysis
-- ============================================================================

CREATE OR REPLACE VIEW unmet_needs_analysis AS
SELECT
    un.need,
    un.relationship_id,
    COUNT(DISTINCT un.conflict_id) as conflict_count,
    MIN(un.first_identified_at) as first_appeared,
    COUNT(DISTINCT DATE(un.created_at)) as days_appeared_in,
    CASE WHEN COUNT(DISTINCT un.conflict_id) >= 3 THEN TRUE ELSE FALSE END as is_chronic,
    ROUND(100.0 * COUNT(DISTINCT un.conflict_id) /
        (SELECT COUNT(*) FROM conflicts c WHERE c.relationship_id = un.relationship_id), 2) as percentage_of_conflicts
FROM unmet_needs un
GROUP BY un.need, un.relationship_id
ORDER BY conflict_count DESC;

-- ============================================================================
-- 8. GRANT permissions (for app user)
-- ============================================================================

-- If using a restricted app role, grant necessary permissions
-- GRANT SELECT, INSERT, UPDATE ON conflicts TO app_user;
-- GRANT SELECT, INSERT ON trigger_phrases TO app_user;
-- GRANT SELECT, INSERT ON unmet_needs TO app_user;
-- GRANT SELECT ON conflict_enrichment TO app_user;
-- GRANT SELECT ON conflict_chains TO app_user;
-- GRANT SELECT ON trigger_phrase_analysis TO app_user;
-- GRANT SELECT ON unmet_needs_analysis TO app_user;
