-- =====================================================================
-- CLEAN MIGRATION: Drop cycle_predictions table
-- Run this after the main migration to remove the deprecated table
-- =====================================================================

-- Drop the cycle_predictions table if it exists
DROP TABLE IF EXISTS cycle_predictions CASCADE;

-- Note: The cycle_events table now handles all cycle tracking
-- Users manually log events (period_start, period_end, symptoms, moods)
-- No more ML predictions or forecasting

