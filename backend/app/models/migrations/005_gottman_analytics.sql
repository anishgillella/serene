-- ============================================================================
-- Migration 005: Gottman Analytics Schema
-- ============================================================================
-- Purpose: Implements Dr. John Gottman's relationship research framework
--   - Four Horsemen tracking (Criticism, Contempt, Defensiveness, Stonewalling)
--   - Repair attempt success tracking
--   - Communication quality metrics (I/You statements)
--   - Daily check-ins for 5:1 ratio tracking
--
-- Run this in Supabase SQL Editor ONCE.
-- This is an idempotent script - safe to re-run.
-- ============================================================================

-- ============================================================================
-- 1. GOTTMAN ANALYSIS TABLE (per-conflict analysis)
-- ============================================================================
-- Stores detailed Gottman metrics extracted from each conflict transcript.

CREATE TABLE IF NOT EXISTS gottman_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conflict_id UUID NOT NULL REFERENCES conflicts(id) ON DELETE CASCADE,
    relationship_id UUID NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,

    -- Four Horsemen Scores (0-10 each, lower is better)
    criticism_score INT DEFAULT 0 CHECK (criticism_score >= 0 AND criticism_score <= 10),
    contempt_score INT DEFAULT 0 CHECK (contempt_score >= 0 AND contempt_score <= 10),
    defensiveness_score INT DEFAULT 0 CHECK (defensiveness_score >= 0 AND defensiveness_score <= 10),
    stonewalling_score INT DEFAULT 0 CHECK (stonewalling_score >= 0 AND stonewalling_score <= 10),

    -- Per-partner horsemen instances (JSON arrays)
    -- Format: [{"type": "criticism", "quote": "...", "severity": 1-10}]
    partner_a_horsemen JSONB DEFAULT '[]'::jsonb,
    partner_b_horsemen JSONB DEFAULT '[]'::jsonb,

    -- Repair Attempts
    repair_attempts_count INT DEFAULT 0,
    successful_repairs_count INT DEFAULT 0,
    -- Format: [{"speaker": "partner_a", "type": "humor", "quote": "...", "successful": true}]
    repair_attempt_details JSONB DEFAULT '[]'::jsonb,

    -- Communication Quality Metrics
    partner_a_i_statements INT DEFAULT 0,
    partner_a_you_statements INT DEFAULT 0,
    partner_b_i_statements INT DEFAULT 0,
    partner_b_you_statements INT DEFAULT 0,
    interruption_count INT DEFAULT 0,
    active_listening_instances INT DEFAULT 0,

    -- Emotional Flooding Detection
    emotional_flooding_detected BOOLEAN DEFAULT FALSE,
    flooding_partner VARCHAR(20),  -- 'partner_a', 'partner_b', 'both', null

    -- Positive/Negative Interaction Count (within this conflict)
    positive_interactions INT DEFAULT 0,
    negative_interactions INT DEFAULT 0,

    -- Overall Assessment
    primary_issue TEXT,
    most_concerning_horseman VARCHAR(20),  -- 'criticism', 'contempt', 'defensiveness', 'stonewalling'
    repair_effectiveness VARCHAR(20),  -- 'high', 'medium', 'low', 'none_attempted'
    recommended_focus TEXT,

    -- Analysis Metadata
    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    model_version VARCHAR(50) DEFAULT 'gpt-4',
    analysis_confidence DECIMAL(3,2) DEFAULT 0.8,
    raw_llm_response JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure one analysis per conflict
    UNIQUE(conflict_id)
);

CREATE INDEX IF NOT EXISTS idx_gottman_analysis_conflict ON gottman_analysis(conflict_id);
CREATE INDEX IF NOT EXISTS idx_gottman_analysis_relationship ON gottman_analysis(relationship_id);
CREATE INDEX IF NOT EXISTS idx_gottman_analysis_analyzed_at ON gottman_analysis(analyzed_at DESC);

ALTER TABLE gottman_analysis ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public access to gottman_analysis" ON gottman_analysis;
CREATE POLICY "Allow public access to gottman_analysis" ON gottman_analysis FOR ALL USING (true);

-- ============================================================================
-- 2. GOTTMAN RELATIONSHIP SCORES (aggregated metrics)
-- ============================================================================
-- Stores rolling averages and health scores for the entire relationship.
-- Note: Using DECIMAL(5,2) for all scores to prevent overflow issues.

CREATE TABLE IF NOT EXISTS gottman_relationship_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID NOT NULL UNIQUE REFERENCES relationships(id) ON DELETE CASCADE,

    -- Rolling Average Four Horsemen (0-10 scale)
    avg_criticism_score DECIMAL(5,2) DEFAULT 0,
    avg_contempt_score DECIMAL(5,2) DEFAULT 0,
    avg_defensiveness_score DECIMAL(5,2) DEFAULT 0,
    avg_stonewalling_score DECIMAL(5,2) DEFAULT 0,

    -- Combined Score (0-40, lower is better)
    total_horsemen_score DECIMAL(5,2) DEFAULT 0,
    horsemen_trend VARCHAR(20) DEFAULT 'stable',  -- 'improving', 'stable', 'worsening'

    -- Repair Metrics (0-100%)
    overall_repair_success_rate DECIMAL(5,2) DEFAULT 0,
    total_repair_attempts INT DEFAULT 0,
    total_successful_repairs INT DEFAULT 0,

    -- Communication Quality
    partner_a_i_to_you_ratio DECIMAL(5,2) DEFAULT 1.0,
    partner_b_i_to_you_ratio DECIMAL(5,2) DEFAULT 1.0,
    avg_active_listening_per_conflict DECIMAL(5,2) DEFAULT 0,

    -- Partner-Specific Patterns
    partner_a_dominant_horseman VARCHAR(20),  -- Their most-used horseman
    partner_b_dominant_horseman VARCHAR(20),

    -- Gottman Health Score (0-100, higher is better)
    gottman_health_score DECIMAL(5,2) DEFAULT 50,

    -- Metadata
    conflicts_analyzed INT DEFAULT 0,
    last_calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    calculation_window_days INT DEFAULT 90,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gottman_scores_relationship ON gottman_relationship_scores(relationship_id);

ALTER TABLE gottman_relationship_scores ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public access to gottman_relationship_scores" ON gottman_relationship_scores;
CREATE POLICY "Allow public access to gottman_relationship_scores" ON gottman_relationship_scores FOR ALL USING (true);

-- ============================================================================
-- 3. DAILY CHECK-INS (for 5:1 ratio tracking outside conflicts)
-- ============================================================================
-- Optional feature for partners to log daily positive/negative interactions.

CREATE TABLE IF NOT EXISTS daily_checkins (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,
    partner_id VARCHAR(20) NOT NULL,  -- 'partner_a' or 'partner_b'

    -- Check-in date (one per partner per day)
    checkin_date DATE NOT NULL DEFAULT CURRENT_DATE,

    -- Simple mood/interaction rating
    day_rating VARCHAR(20) NOT NULL,  -- 'positive', 'neutral', 'negative'

    -- Counts
    positive_moments INT DEFAULT 0,
    negative_moments INT DEFAULT 0,

    -- Optional: Bids for connection
    bids_made INT DEFAULT 0,
    bids_received_positively INT DEFAULT 0,
    bids_ignored INT DEFAULT 0,

    -- Appreciation
    appreciation_given BOOLEAN DEFAULT FALSE,
    appreciation_received BOOLEAN DEFAULT FALSE,

    -- Quality time
    quality_time_minutes INT DEFAULT 0,

    -- Notes
    notes TEXT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- One check-in per partner per day
    UNIQUE(relationship_id, partner_id, checkin_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_checkins_relationship ON daily_checkins(relationship_id);
CREATE INDEX IF NOT EXISTS idx_daily_checkins_date ON daily_checkins(checkin_date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_checkins_partner ON daily_checkins(partner_id);

ALTER TABLE daily_checkins ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public access to daily_checkins" ON daily_checkins;
CREATE POLICY "Allow public access to daily_checkins" ON daily_checkins FOR ALL USING (true);

-- ============================================================================
-- 4. RELATIONSHIP 5:1 RATIO TRACKING (aggregated from check-ins)
-- ============================================================================

CREATE TABLE IF NOT EXISTS relationship_positivity_ratio (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID NOT NULL UNIQUE REFERENCES relationships(id) ON DELETE CASCADE,

    -- Rolling 7-day ratio
    ratio_7_day DECIMAL(4,2) DEFAULT 0,
    positive_count_7_day INT DEFAULT 0,
    negative_count_7_day INT DEFAULT 0,

    -- Rolling 30-day ratio
    ratio_30_day DECIMAL(4,2) DEFAULT 0,
    positive_count_30_day INT DEFAULT 0,
    negative_count_30_day INT DEFAULT 0,

    -- All-time ratio
    ratio_all_time DECIMAL(4,2) DEFAULT 0,
    positive_count_all_time INT DEFAULT 0,
    negative_count_all_time INT DEFAULT 0,

    -- Bid for connection success rate
    bid_success_rate DECIMAL(4,2) DEFAULT 0,

    -- Health indicator
    is_ratio_healthy BOOLEAN DEFAULT FALSE,  -- >= 5:1
    ratio_trend VARCHAR(20) DEFAULT 'stable',

    -- Metadata
    last_calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    days_with_data INT DEFAULT 0,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE relationship_positivity_ratio ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public access to relationship_positivity_ratio" ON relationship_positivity_ratio;
CREATE POLICY "Allow public access to relationship_positivity_ratio" ON relationship_positivity_ratio FOR ALL USING (true);

-- ============================================================================
-- 5. HELPER FUNCTION: Calculate Gottman Health Score
-- ============================================================================
-- Formula: 100 - horsemen_penalty + repair_bonus
-- Contempt is weighted 2x (most damaging per Gottman research)

CREATE OR REPLACE FUNCTION calculate_gottman_health_score(
    p_criticism DECIMAL,
    p_contempt DECIMAL,
    p_defensiveness DECIMAL,
    p_stonewalling DECIMAL,
    p_repair_rate DECIMAL
) RETURNS DECIMAL AS $$
DECLARE
    horsemen_penalty DECIMAL;
    repair_bonus DECIMAL;
    health_score DECIMAL;
BEGIN
    -- Clamp input values to expected ranges
    p_criticism := LEAST(GREATEST(p_criticism, 0), 10);
    p_contempt := LEAST(GREATEST(p_contempt, 0), 10);
    p_defensiveness := LEAST(GREATEST(p_defensiveness, 0), 10);
    p_stonewalling := LEAST(GREATEST(p_stonewalling, 0), 10);
    p_repair_rate := LEAST(GREATEST(p_repair_rate, 0), 100);

    -- Horsemen penalty (contempt weighted 2x)
    horsemen_penalty := (p_criticism * 2) + (p_contempt * 4) + (p_defensiveness * 2) + (p_stonewalling * 2);

    -- Repair bonus
    repair_bonus := p_repair_rate * 0.3;

    -- Calculate and clamp final score
    health_score := LEAST(GREATEST(100 - horsemen_penalty + repair_bonus, 0), 100);

    RETURN health_score;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 6. TRIGGER: Auto-update relationship scores when analysis is added
-- ============================================================================

CREATE OR REPLACE FUNCTION update_gottman_relationship_scores()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure relationship scores row exists
    INSERT INTO gottman_relationship_scores (relationship_id)
    VALUES (NEW.relationship_id)
    ON CONFLICT (relationship_id) DO NOTHING;

    -- Update aggregated scores with clamped values
    UPDATE gottman_relationship_scores grs
    SET
        avg_criticism_score = LEAST(sub.avg_criticism, 10),
        avg_contempt_score = LEAST(sub.avg_contempt, 10),
        avg_defensiveness_score = LEAST(sub.avg_defensiveness, 10),
        avg_stonewalling_score = LEAST(sub.avg_stonewalling, 10),
        total_horsemen_score = LEAST(sub.avg_criticism + sub.avg_contempt + sub.avg_defensiveness + sub.avg_stonewalling, 40),
        overall_repair_success_rate = LEAST(CASE WHEN sub.total_repairs > 0
            THEN (sub.successful_repairs::DECIMAL / sub.total_repairs) * 100
            ELSE 0 END, 100),
        total_repair_attempts = sub.total_repairs,
        total_successful_repairs = sub.successful_repairs,
        conflicts_analyzed = sub.conflict_count,
        gottman_health_score = calculate_gottman_health_score(
            LEAST(sub.avg_criticism, 10),
            LEAST(sub.avg_contempt, 10),
            LEAST(sub.avg_defensiveness, 10),
            LEAST(sub.avg_stonewalling, 10),
            LEAST(CASE WHEN sub.total_repairs > 0
                THEN (sub.successful_repairs::DECIMAL / sub.total_repairs) * 100
                ELSE 0 END, 100)
        ),
        last_calculated_at = NOW(),
        updated_at = NOW()
    FROM (
        SELECT
            relationship_id,
            COALESCE(AVG(criticism_score), 0) as avg_criticism,
            COALESCE(AVG(contempt_score), 0) as avg_contempt,
            COALESCE(AVG(defensiveness_score), 0) as avg_defensiveness,
            COALESCE(AVG(stonewalling_score), 0) as avg_stonewalling,
            COALESCE(SUM(repair_attempts_count), 0) as total_repairs,
            COALESCE(SUM(successful_repairs_count), 0) as successful_repairs,
            COUNT(*) as conflict_count
        FROM gottman_analysis
        WHERE relationship_id = NEW.relationship_id
        GROUP BY relationship_id
    ) sub
    WHERE grs.relationship_id = NEW.relationship_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger (drop first to ensure clean state)
DROP TRIGGER IF EXISTS trigger_update_gottman_scores ON gottman_analysis;
CREATE TRIGGER trigger_update_gottman_scores
    AFTER INSERT OR UPDATE ON gottman_analysis
    FOR EACH ROW
    EXECUTE FUNCTION update_gottman_relationship_scores();

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- Tables created:
--   - gottman_analysis (per-conflict Four Horsemen analysis)
--   - gottman_relationship_scores (aggregated relationship health)
--   - daily_checkins (optional 5:1 ratio tracking)
--   - relationship_positivity_ratio (aggregated check-in data)
--
-- Functions created:
--   - calculate_gottman_health_score()
--   - update_gottman_relationship_scores() (trigger function)
--
-- Next steps:
--   1. Restart backend to pick up new code
--   2. Run backfill endpoint to analyze existing conflicts:
--      POST /api/analytics/gottman/backfill
-- ============================================================================
