-- Migration 008: Advanced Analytics Features
-- Adds tables for:
-- 1. Surface vs Underlying Concerns mapping
-- 2. Emotional Temperature Timeline (per-message intensity)
-- 3. Partner-Specific Trigger Sensitivity scores
-- 4. Conflict Annotations for replay

-- ============================================================================
-- 1. SURFACE VS UNDERLYING CONCERNS
-- Maps what was said to what it really means
-- ============================================================================

CREATE TABLE IF NOT EXISTS surface_underlying_mapping (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conflict_id UUID NOT NULL REFERENCES conflicts(id) ON DELETE CASCADE,
    relationship_id UUID NOT NULL,

    -- The surface statement
    speaker VARCHAR(20) NOT NULL CHECK (speaker IN ('partner_a', 'partner_b')),
    surface_statement TEXT NOT NULL,
    surface_category VARCHAR(50), -- 'complaint', 'accusation', 'withdrawal', 'dismissal', 'demand'

    -- The underlying meaning
    underlying_concern TEXT NOT NULL,
    underlying_emotion VARCHAR(50), -- 'hurt', 'fear', 'loneliness', 'overwhelm', 'rejection', 'disrespect'
    underlying_need VARCHAR(50), -- Maps to existing need categories

    -- Confidence and context
    confidence DECIMAL(3,2) DEFAULT 0.8 CHECK (confidence >= 0 AND confidence <= 1),
    evidence TEXT, -- Quote or context supporting the interpretation

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Indexes
    CONSTRAINT fk_surface_relationship FOREIGN KEY (relationship_id)
        REFERENCES relationships(id) ON DELETE CASCADE
);

CREATE INDEX idx_surface_underlying_conflict ON surface_underlying_mapping(conflict_id);
CREATE INDEX idx_surface_underlying_relationship ON surface_underlying_mapping(relationship_id);
CREATE INDEX idx_surface_underlying_speaker ON surface_underlying_mapping(speaker);

-- ============================================================================
-- 2. EMOTIONAL TEMPERATURE TIMELINE
-- Tracks emotional intensity at each message in a conflict
-- ============================================================================

CREATE TABLE IF NOT EXISTS emotional_temperature (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conflict_id UUID NOT NULL REFERENCES conflicts(id) ON DELETE CASCADE,
    relationship_id UUID NOT NULL,
    message_sequence INT NOT NULL, -- Links to rant_messages.sequence_number

    -- Speaker info
    speaker VARCHAR(20) NOT NULL CHECK (speaker IN ('partner_a', 'partner_b')),

    -- Temperature metrics (all 0-10 scale)
    emotional_intensity INT NOT NULL CHECK (emotional_intensity >= 0 AND emotional_intensity <= 10),
    negativity_score INT DEFAULT 5 CHECK (negativity_score >= 0 AND negativity_score <= 10),
    defensiveness_level INT DEFAULT 0 CHECK (defensiveness_level >= 0 AND defensiveness_level <= 10),

    -- What's happening at this point
    escalation_delta INT DEFAULT 0 CHECK (escalation_delta >= -5 AND escalation_delta <= 5), -- Change from previous
    is_escalation_point BOOLEAN DEFAULT FALSE,
    is_repair_attempt BOOLEAN DEFAULT FALSE,
    is_de_escalation BOOLEAN DEFAULT FALSE,

    -- Detected emotions at this moment
    primary_emotion VARCHAR(50), -- 'anger', 'hurt', 'frustration', 'sadness', 'contempt', 'fear'
    secondary_emotion VARCHAR(50),

    -- Brief note about what's happening
    moment_note TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT fk_temp_relationship FOREIGN KEY (relationship_id)
        REFERENCES relationships(id) ON DELETE CASCADE
);

CREATE INDEX idx_emotional_temp_conflict ON emotional_temperature(conflict_id);
CREATE INDEX idx_emotional_temp_sequence ON emotional_temperature(conflict_id, message_sequence);
CREATE INDEX idx_emotional_temp_escalation ON emotional_temperature(is_escalation_point) WHERE is_escalation_point = TRUE;

-- ============================================================================
-- 3. PARTNER-SPECIFIC TRIGGER SENSITIVITY
-- Aggregated sensitivity scores per partner per trigger type
-- ============================================================================

CREATE TABLE IF NOT EXISTS partner_trigger_sensitivity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    relationship_id UUID NOT NULL,
    partner VARCHAR(20) NOT NULL CHECK (partner IN ('partner_a', 'partner_b')),

    -- The trigger category or specific phrase pattern
    trigger_category VARCHAR(50) NOT NULL, -- 'criticism', 'dismissal', 'past_reference', 'tone', 'topic_money', etc.
    trigger_description TEXT, -- Human-readable description

    -- Sensitivity metrics
    sensitivity_score DECIMAL(3,2) NOT NULL CHECK (sensitivity_score >= 0 AND sensitivity_score <= 1), -- 0-1 scale
    reaction_intensity_avg DECIMAL(3,1) CHECK (reaction_intensity_avg >= 0 AND reaction_intensity_avg <= 10), -- Average escalation when triggered

    -- Evidence
    times_triggered INT DEFAULT 1,
    escalation_rate DECIMAL(3,2) DEFAULT 0.5, -- How often this leads to escalation
    example_phrases TEXT[], -- Array of example phrases that trigger this

    -- Timestamps
    first_observed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_observed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT fk_sensitivity_relationship FOREIGN KEY (relationship_id)
        REFERENCES relationships(id) ON DELETE CASCADE,
    CONSTRAINT unique_partner_trigger UNIQUE (relationship_id, partner, trigger_category)
);

CREATE INDEX idx_sensitivity_relationship ON partner_trigger_sensitivity(relationship_id);
CREATE INDEX idx_sensitivity_partner ON partner_trigger_sensitivity(relationship_id, partner);
CREATE INDEX idx_sensitivity_score ON partner_trigger_sensitivity(sensitivity_score DESC);

-- ============================================================================
-- 4. CONFLICT ANNOTATIONS FOR REPLAY
-- Stores annotations/insights for specific moments in a conflict
-- ============================================================================

CREATE TABLE IF NOT EXISTS conflict_annotations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conflict_id UUID NOT NULL REFERENCES conflicts(id) ON DELETE CASCADE,
    relationship_id UUID NOT NULL,

    -- Position in conversation
    message_sequence_start INT NOT NULL, -- Start of annotated section
    message_sequence_end INT, -- End (null = single message)

    -- Annotation content
    annotation_type VARCHAR(50) NOT NULL, -- 'escalation', 'repair_attempt', 'missed_bid', 'horseman', 'breakthrough', 'suggestion'
    annotation_title VARCHAR(100),
    annotation_text TEXT NOT NULL,

    -- For suggestions/alternatives
    suggested_alternative TEXT, -- What could have been said instead

    -- Metadata
    severity VARCHAR(20), -- 'info', 'warning', 'critical', 'positive'
    related_horseman VARCHAR(20), -- 'criticism', 'contempt', 'defensiveness', 'stonewalling'
    related_need VARCHAR(50), -- Links to unmet need if applicable

    -- Auto-generated vs manual
    is_auto_generated BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT fk_annotation_relationship FOREIGN KEY (relationship_id)
        REFERENCES relationships(id) ON DELETE CASCADE
);

CREATE INDEX idx_annotations_conflict ON conflict_annotations(conflict_id);
CREATE INDEX idx_annotations_sequence ON conflict_annotations(conflict_id, message_sequence_start);
CREATE INDEX idx_annotations_type ON conflict_annotations(annotation_type);

-- ============================================================================
-- 5. CROSS-CONFLICT EMOTIONAL TRENDS
-- Aggregated emotional health over time
-- ============================================================================

CREATE TABLE IF NOT EXISTS emotional_trends (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    relationship_id UUID NOT NULL,

    -- Time period
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    period_type VARCHAR(20) NOT NULL CHECK (period_type IN ('daily', 'weekly', 'monthly')),

    -- Aggregated metrics
    conflicts_count INT DEFAULT 0,
    avg_peak_intensity DECIMAL(3,1), -- Average peak emotional intensity
    avg_resolution_time_minutes INT, -- How long conflicts last on average

    -- Trend indicators
    escalation_trend VARCHAR(20), -- 'improving', 'stable', 'worsening'
    repair_success_rate DECIMAL(3,2), -- 0-1

    -- Partner-specific
    partner_a_avg_intensity DECIMAL(3,1),
    partner_b_avg_intensity DECIMAL(3,1),

    -- Horsemen presence
    horsemen_frequency DECIMAL(3,2), -- How often horsemen appear
    most_common_horseman VARCHAR(20),

    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT fk_trends_relationship FOREIGN KEY (relationship_id)
        REFERENCES relationships(id) ON DELETE CASCADE,
    CONSTRAINT unique_trend_period UNIQUE (relationship_id, period_start, period_type)
);

CREATE INDEX idx_trends_relationship ON emotional_trends(relationship_id);
CREATE INDEX idx_trends_period ON emotional_trends(relationship_id, period_start DESC);

-- ============================================================================
-- VIEWS FOR EASY QUERYING
-- ============================================================================

-- View: Partner sensitivity summary
CREATE OR REPLACE VIEW partner_sensitivity_summary AS
SELECT
    relationship_id,
    partner,
    COUNT(*) as total_triggers,
    AVG(sensitivity_score) as avg_sensitivity,
    MAX(sensitivity_score) as max_sensitivity,
    SUM(times_triggered) as total_times_triggered,
    AVG(escalation_rate) as avg_escalation_rate,
    ARRAY_AGG(trigger_category ORDER BY sensitivity_score DESC) as triggers_by_severity
FROM partner_trigger_sensitivity
GROUP BY relationship_id, partner;

-- View: Conflict emotional summary
CREATE OR REPLACE VIEW conflict_emotional_summary AS
SELECT
    conflict_id,
    relationship_id,
    COUNT(*) as total_messages,
    MAX(emotional_intensity) as peak_intensity,
    AVG(emotional_intensity) as avg_intensity,
    MIN(emotional_intensity) as min_intensity,
    COUNT(*) FILTER (WHERE is_escalation_point) as escalation_points,
    COUNT(*) FILTER (WHERE is_repair_attempt) as repair_attempts,
    COUNT(*) FILTER (WHERE is_de_escalation) as de_escalations,
    MAX(message_sequence) FILTER (WHERE emotional_intensity = (
        SELECT MAX(emotional_intensity) FROM emotional_temperature et2
        WHERE et2.conflict_id = emotional_temperature.conflict_id
    )) as peak_moment_sequence
FROM emotional_temperature
GROUP BY conflict_id, relationship_id;

-- View: Surface to underlying patterns
CREATE OR REPLACE VIEW underlying_patterns AS
SELECT
    relationship_id,
    speaker,
    underlying_emotion,
    underlying_need,
    COUNT(*) as occurrence_count,
    AVG(confidence) as avg_confidence,
    ARRAY_AGG(DISTINCT surface_category) as surface_categories_used
FROM surface_underlying_mapping
GROUP BY relationship_id, speaker, underlying_emotion, underlying_need
HAVING COUNT(*) >= 2;

COMMENT ON TABLE surface_underlying_mapping IS 'Maps surface statements to underlying emotional concerns and needs';
COMMENT ON TABLE emotional_temperature IS 'Tracks emotional intensity at each message in a conflict for timeline visualization';
COMMENT ON TABLE partner_trigger_sensitivity IS 'Aggregated sensitivity scores for each partner to specific trigger types';
COMMENT ON TABLE conflict_annotations IS 'Annotations and insights for conflict replay feature';
COMMENT ON TABLE emotional_trends IS 'Aggregated emotional health metrics over time periods';
