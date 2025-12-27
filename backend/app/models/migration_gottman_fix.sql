-- Migration Fix: Increase DECIMAL precision for Gottman scores
-- Run this in Supabase SQL Editor to fix the numeric field overflow error

-- ============================================================================
-- 1. ALTER gottman_relationship_scores columns to handle larger values
-- ============================================================================

-- Total horsemen can be 0-40, so need DECIMAL(5,2)
ALTER TABLE gottman_relationship_scores
    ALTER COLUMN total_horsemen_score TYPE DECIMAL(5,2);

-- Gottman health score can be 0-100
ALTER TABLE gottman_relationship_scores
    ALTER COLUMN gottman_health_score TYPE DECIMAL(5,2);

-- Repair success rate is 0-100%
ALTER TABLE gottman_relationship_scores
    ALTER COLUMN overall_repair_success_rate TYPE DECIMAL(5,2);

-- Average horsemen scores are 0-10, but DECIMAL(4,2) should work
-- However, let's increase to be safe
ALTER TABLE gottman_relationship_scores
    ALTER COLUMN avg_criticism_score TYPE DECIMAL(5,2);

ALTER TABLE gottman_relationship_scores
    ALTER COLUMN avg_contempt_score TYPE DECIMAL(5,2);

ALTER TABLE gottman_relationship_scores
    ALTER COLUMN avg_defensiveness_score TYPE DECIMAL(5,2);

ALTER TABLE gottman_relationship_scores
    ALTER COLUMN avg_stonewalling_score TYPE DECIMAL(5,2);

ALTER TABLE gottman_relationship_scores
    ALTER COLUMN partner_a_i_to_you_ratio TYPE DECIMAL(5,2);

ALTER TABLE gottman_relationship_scores
    ALTER COLUMN partner_b_i_to_you_ratio TYPE DECIMAL(5,2);

ALTER TABLE gottman_relationship_scores
    ALTER COLUMN avg_active_listening_per_conflict TYPE DECIMAL(5,2);

-- ============================================================================
-- 2. Update the calculate_gottman_health_score function to clamp values
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
    -- Clamp input values to expected ranges
    p_criticism := LEAST(GREATEST(p_criticism, 0), 10);
    p_contempt := LEAST(GREATEST(p_contempt, 0), 10);
    p_defensiveness := LEAST(GREATEST(p_defensiveness, 0), 10);
    p_stonewalling := LEAST(GREATEST(p_stonewalling, 0), 10);
    p_repair_rate := LEAST(GREATEST(p_repair_rate, 0), 100);

    -- Horsemen penalty: Each point reduces score
    -- Contempt weighted 2x (most damaging per Gottman research)
    horsemen_penalty := (p_criticism * 2) + (p_contempt * 4) + (p_defensiveness * 2) + (p_stonewalling * 2);

    -- Repair bonus: High repair rate adds to score
    repair_bonus := p_repair_rate * 0.3;

    -- Calculate final score (0-100 range)
    health_score := 100 - horsemen_penalty + repair_bonus;

    -- Clamp to 0-100
    health_score := LEAST(GREATEST(health_score, 0), 100);

    RETURN health_score;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 3. Update the trigger function to clamp values before update
-- ============================================================================

CREATE OR REPLACE FUNCTION update_gottman_relationship_scores()
RETURNS TRIGGER AS $$
BEGIN
    -- Insert or update relationship scores
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

-- Recreate trigger
DROP TRIGGER IF EXISTS trigger_update_gottman_scores ON gottman_analysis;
CREATE TRIGGER trigger_update_gottman_scores
    AFTER INSERT OR UPDATE ON gottman_analysis
    FOR EACH ROW
    EXECUTE FUNCTION update_gottman_relationship_scores();
