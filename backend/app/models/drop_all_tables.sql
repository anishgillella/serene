-- =====================================================================
-- DESTRUCTIVE: Drop all tables in public schema
-- WARNING: This will DELETE ALL DATA in your database!
-- =====================================================================

-- Drop all tables in order (respecting dependencies)
DROP TABLE IF EXISTS repair_plans CASCADE;
DROP TABLE IF EXISTS conflict_analysis CASCADE;
DROP TABLE IF EXISTS intimacy_events CASCADE;
DROP TABLE IF EXISTS memorable_dates CASCADE;
DROP TABLE IF EXISTS cycle_events CASCADE;
DROP TABLE IF EXISTS profiles CASCADE;
DROP TABLE IF EXISTS mediator_messages CASCADE;
DROP TABLE IF EXISTS mediator_sessions CASCADE;
DROP TABLE IF EXISTS rant_messages CASCADE;
DROP TABLE IF EXISTS conflicts CASCADE;
DROP TABLE IF EXISTS relationships CASCADE;

-- Drop any remaining tables that might exist
DROP TABLE IF EXISTS cycle_predictions CASCADE;

-- Verify all tables are gone
SELECT tablename FROM pg_tables WHERE schemaname = 'public';
