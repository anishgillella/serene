-- Phase 4: Gender-Neutral Data Model Migration
-- This migration updates gendered field names to be inclusive of all relationship types

-- ============================================
-- 1. ADD partner_profile TYPE TO pdf_type ENUM
-- ============================================

-- Add new gender-neutral pdf_type values while keeping backward compatibility
-- Old values: boyfriend_profile, girlfriend_profile
-- New values: partner_a_profile, partner_b_profile (plus 'partner_profile' as generic)

-- Update existing profiles table comment
COMMENT ON COLUMN profiles.pdf_type IS 'Profile type: partner_a_profile, partner_b_profile, partner_profile, handbook (legacy: boyfriend_profile, girlfriend_profile)';

-- ============================================
-- 2. UPDATE CONFLICT_ANALYSIS TABLE (if exists)
-- ============================================

-- Add gender-neutral columns if they don't exist
DO $$
BEGIN
    -- Add unmet_needs_partner_a if unmet_needs_boyfriend exists and partner_a doesn't
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'conflict_analysis' AND column_name = 'unmet_needs_boyfriend')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'conflict_analysis' AND column_name = 'unmet_needs_partner_a')
    THEN
        ALTER TABLE conflict_analysis ADD COLUMN unmet_needs_partner_a TEXT;
        UPDATE conflict_analysis SET unmet_needs_partner_a = unmet_needs_boyfriend;
    END IF;

    -- Add unmet_needs_partner_b if unmet_needs_girlfriend exists and partner_b doesn't
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'conflict_analysis' AND column_name = 'unmet_needs_girlfriend')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'conflict_analysis' AND column_name = 'unmet_needs_partner_b')
    THEN
        ALTER TABLE conflict_analysis ADD COLUMN unmet_needs_partner_b TEXT;
        UPDATE conflict_analysis SET unmet_needs_partner_b = unmet_needs_girlfriend;
    END IF;
END $$;

-- ============================================
-- 3. UPDATE REPAIR_PLANS TABLE (if exists)
-- ============================================

DO $$
BEGIN
    -- Add repair_plan_partner_a if repair_plan_boyfriend exists and partner_a doesn't
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'repair_plans' AND column_name = 'repair_plan_boyfriend')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'repair_plans' AND column_name = 'repair_plan_partner_a')
    THEN
        ALTER TABLE repair_plans ADD COLUMN repair_plan_partner_a JSONB;
        UPDATE repair_plans SET repair_plan_partner_a = repair_plan_boyfriend;
    END IF;

    -- Add repair_plan_partner_b if repair_plan_girlfriend exists and partner_b doesn't
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'repair_plans' AND column_name = 'repair_plan_girlfriend')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'repair_plans' AND column_name = 'repair_plan_partner_b')
    THEN
        ALTER TABLE repair_plans ADD COLUMN repair_plan_partner_b JSONB;
        UPDATE repair_plans SET repair_plan_partner_b = repair_plan_girlfriend;
    END IF;
END $$;

-- ============================================
-- 4. CREATE PDF_TYPE MAPPING VIEW
-- ============================================

-- Create a view that maps old pdf_type values to new ones for backward compatibility
-- Note: Only includes columns that exist in the profiles table
CREATE OR REPLACE VIEW v_profiles_normalized AS
SELECT
    id,
    relationship_id,
    CASE pdf_type
        WHEN 'boyfriend_profile' THEN 'partner_a_profile'
        WHEN 'girlfriend_profile' THEN 'partner_b_profile'
        ELSE pdf_type
    END AS pdf_type,
    pdf_type AS original_pdf_type,
    file_path,
    created_at,
    updated_at
FROM profiles;

-- ============================================
-- 5. CREATE HELPER FUNCTION FOR PDF_TYPE NORMALIZATION
-- ============================================

CREATE OR REPLACE FUNCTION normalize_pdf_type(pdf_type_input TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN CASE pdf_type_input
        WHEN 'boyfriend_profile' THEN 'partner_a_profile'
        WHEN 'girlfriend_profile' THEN 'partner_b_profile'
        WHEN 'boyfriend' THEN 'partner_a_profile'
        WHEN 'girlfriend' THEN 'partner_b_profile'
        ELSE pdf_type_input
    END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================
-- 6. UPDATE TEST DATA TO USE GENDER-NEUTRAL NAMES
-- ============================================

-- Keep Adrian & Elara for backward compatibility but ensure partner names are set
UPDATE relationships
SET
    partner_a_name = COALESCE(partner_a_name, 'Partner A'),
    partner_b_name = COALESCE(partner_b_name, 'Partner B')
WHERE partner_a_name IS NULL OR partner_b_name IS NULL;

-- ============================================
-- 7. ADD INDEX FOR NORMALIZED PDF_TYPE QUERIES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_profiles_pdf_type_normalized
ON profiles ((
    CASE pdf_type
        WHEN 'boyfriend_profile' THEN 'partner_a_profile'
        WHEN 'girlfriend_profile' THEN 'partner_b_profile'
        ELSE pdf_type
    END
));

-- ============================================
-- 8. DOCUMENT THE MIGRATION
-- ============================================

COMMENT ON TABLE profiles IS 'User profile PDFs. pdf_type supports both legacy (boyfriend_profile, girlfriend_profile) and new (partner_a_profile, partner_b_profile) values.';
