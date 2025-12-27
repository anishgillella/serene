-- Migration: Gottman Analytics Schema
-- Run this in Supabase SQL Editor
-- Adds Four Horsemen tracking, repair attempts, and daily check-ins

-- ============================================================================
-- 1. GOTTMAN ANALYSIS TABLE (per-conflict analysis)
-- ============================================================================

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
CREATE POLICY "Allow public access to gottman_analysis" ON gottman_analysis FOR ALL USING (true);

-- ============================================================================
-- 2. GOTTMAN RELATIONSHIP SCORES (aggregated metrics)
-- ============================================================================

CREATE TABLE IF NOT EXISTS gottman_relationship_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID NOT NULL UNIQUE REFERENCES relationships(id) ON DELETE CASCADE,

    -- Rolling Average Four Horsemen (last 30 days or all time)
    avg_criticism_score DECIMAL(4,2) DEFAULT 0,
    avg_contempt_score DECIMAL(4,2) DEFAULT 0,
    avg_defensiveness_score DECIMAL(4,2) DEFAULT 0,
    avg_stonewalling_score DECIMAL(4,2) DEFAULT 0,

    -- Combined Score (0-40, lower is better)
    total_horsemen_score DECIMAL(5,2) DEFAULT 0,
    horsemen_trend VARCHAR(20) DEFAULT 'stable',  -- 'improving', 'stable', 'worsening'

    -- Repair Metrics
    overall_repair_success_rate DECIMAL(4,2) DEFAULT 0,  -- 0-100%
    total_repair_attempts INT DEFAULT 0,
    total_successful_repairs INT DEFAULT 0,

    -- Communication Quality
    partner_a_i_to_you_ratio DECIMAL(4,2) DEFAULT 1.0,
    partner_b_i_to_you_ratio DECIMAL(4,2) DEFAULT 1.0,
    avg_active_listening_per_conflict DECIMAL(4,2) DEFAULT 0,

    -- Partner-Specific Patterns
    partner_a_dominant_horseman VARCHAR(20),  -- Their most-used horseman
    partner_b_dominant_horseman VARCHAR(20),

    -- Gottman Health Score (0-100, higher is better)
    -- Calculated as: 100 - (total_horsemen * 2) + (repair_rate * 0.5)
    gottman_health_score DECIMAL(5,2) DEFAULT 50,

    -- Metadata
    conflicts_analyzed INT DEFAULT 0,
    last_calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    calculation_window_days INT DEFAULT 90,  -- How far back to look

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gottman_scores_relationship ON gottman_relationship_scores(relationship_id);

ALTER TABLE gottman_relationship_scores ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public access to gottman_relationship_scores" ON gottman_relationship_scores FOR ALL USING (true);

-- ============================================================================
-- 3. DAILY CHECK-INS (for 5:1 ratio tracking outside conflicts)
-- ============================================================================

CREATE TABLE IF NOT EXISTS daily_checkins (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,
    partner_id VARCHAR(20) NOT NULL,  -- 'partner_a' or 'partner_b'

    -- Check-in date (one per partner per day)
    checkin_date DATE NOT NULL DEFAULT CURRENT_DATE,

    -- Simple mood/interaction rating
    day_rating VARCHAR(20) NOT NULL,  -- 'positive', 'neutral', 'negative'

    -- Optional: Count of positive moments
    positive_moments INT DEFAULT 0,
    negative_moments INT DEFAULT 0,

    -- Optional: Bids for connection
    bids_made INT DEFAULT 0,
    bids_received_positively INT DEFAULT 0,
    bids_ignored INT DEFAULT 0,

    -- Optional: Appreciation expressed
    appreciation_given BOOLEAN DEFAULT FALSE,
    appreciation_received BOOLEAN DEFAULT FALSE,

    -- Optional: Quality time
    quality_time_minutes INT DEFAULT 0,

    -- Optional notes
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

    -- Is ratio healthy? (>= 5:1)
    is_ratio_healthy BOOLEAN DEFAULT FALSE,
    ratio_trend VARCHAR(20) DEFAULT 'stable',  -- 'improving', 'stable', 'declining'

    -- Metadata
    last_calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    days_with_data INT DEFAULT 0,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE relationship_positivity_ratio ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public access to relationship_positivity_ratio" ON relationship_positivity_ratio FOR ALL USING (true);

-- ============================================================================
-- 5. HELPER FUNCTION: Calculate Gottman Health Score
-- ============================================================================

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
    -- Horsemen penalty: Each point reduces score
    -- Contempt weighted 2x (most damaging per Gottman research)
    horsemen_penalty := (p_criticism * 2) + (p_contempt * 4) + (p_defensiveness * 2) + (p_stonewalling * 2);

    -- Repair bonus: High repair rate adds to score
    repair_bonus := p_repair_rate * 0.3;

    -- Calculate final score (0-100 range)
    health_score := 100 - horsemen_penalty + repair_bonus;

    -- Clamp to 0-100
    IF health_score < 0 THEN
        health_score := 0;
    ELSIF health_score > 100 THEN
        health_score := 100;
    END IF;

    RETURN health_score;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 6. TRIGGER: Auto-update relationship scores when analysis is added
-- ============================================================================

CREATE OR REPLACE FUNCTION update_gottman_relationship_scores()
RETURNS TRIGGER AS $$
BEGIN
    -- Insert or update relationship scores
    INSERT INTO gottman_relationship_scores (relationship_id)
    VALUES (NEW.relationship_id)
    ON CONFLICT (relationship_id) DO NOTHING;

    -- Update aggregated scores
    UPDATE gottman_relationship_scores grs
    SET
        avg_criticism_score = sub.avg_criticism,
        avg_contempt_score = sub.avg_contempt,
        avg_defensiveness_score = sub.avg_defensiveness,
        avg_stonewalling_score = sub.avg_stonewalling,
        total_horsemen_score = sub.avg_criticism + sub.avg_contempt + sub.avg_defensiveness + sub.avg_stonewalling,
        overall_repair_success_rate = CASE WHEN sub.total_repairs > 0
            THEN (sub.successful_repairs::DECIMAL / sub.total_repairs) * 100
            ELSE 0 END,
        total_repair_attempts = sub.total_repairs,
        total_successful_repairs = sub.successful_repairs,
        conflicts_analyzed = sub.conflict_count,
        gottman_health_score = calculate_gottman_health_score(
            sub.avg_criticism,
            sub.avg_contempt,
            sub.avg_defensiveness,
            sub.avg_stonewalling,
            CASE WHEN sub.total_repairs > 0
                THEN (sub.successful_repairs::DECIMAL / sub.total_repairs) * 100
                ELSE 0 END
        ),
        last_calculated_at = NOW(),
        updated_at = NOW()
    FROM (
        SELECT
            relationship_id,
            AVG(criticism_score) as avg_criticism,
            AVG(contempt_score) as avg_contempt,
            AVG(defensiveness_score) as avg_defensiveness,
            AVG(stonewalling_score) as avg_stonewalling,
            SUM(repair_attempts_count) as total_repairs,
            SUM(successful_repairs_count) as successful_repairs,
            COUNT(*) as conflict_count
        FROM gottman_analysis
        WHERE relationship_id = NEW.relationship_id
        GROUP BY relationship_id
    ) sub
    WHERE grs.relationship_id = NEW.relationship_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS trigger_update_gottman_scores ON gottman_analysis;
CREATE TRIGGER trigger_update_gottman_scores
    AFTER INSERT OR UPDATE ON gottman_analysis
    FOR EACH ROW
    EXECUTE FUNCTION update_gottman_relationship_scores();
