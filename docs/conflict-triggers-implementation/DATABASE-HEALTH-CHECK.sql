-- Database Health Check for Phase 1
-- Run this after migration to verify everything is working
-- Copy & paste into Supabase SQL Editor

-- ============================================================================
-- SECTION 1: Schema Verification
-- ============================================================================

-- Check 1.1: Verify all new tables exist
SELECT
  'Tables' as check_type,
  count(*) as count,
  string_agg(table_name, ', ') as tables
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('trigger_phrases', 'unmet_needs', 'conflict_enrichment');

-- Check 1.2: Verify conflicts table has all new columns
SELECT
  'Conflicts Table Columns' as check_type,
  count(*) as column_count,
  string_agg(column_name, ', ' ORDER BY column_name) as columns
FROM information_schema.columns
WHERE table_name = 'conflicts'
AND column_name IN (
  'parent_conflict_id',
  'is_continuation',
  'days_since_related_conflict',
  'resentment_level',
  'unmet_needs',
  'has_past_references',
  'conflict_chain_id',
  'is_resolved',
  'resolved_at'
);

-- Check 1.3: Verify all views exist
SELECT
  'Views' as check_type,
  count(*) as count,
  string_agg(table_name, ', ') as views
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_type = 'VIEW'
AND table_name IN ('conflict_chains', 'trigger_phrase_analysis', 'unmet_needs_analysis');

-- ============================================================================
-- SECTION 2: Index Verification
-- ============================================================================

-- Check 2.1: Verify indexes on trigger_phrases
SELECT
  'trigger_phrases Indexes' as check_type,
  count(*) as index_count,
  string_agg(indexname, ', ' ORDER BY indexname) as indexes
FROM pg_indexes
WHERE tablename = 'trigger_phrases';

-- Check 2.2: Verify indexes on unmet_needs
SELECT
  'unmet_needs Indexes' as check_type,
  count(*) as index_count,
  string_agg(indexname, ', ' ORDER BY indexname) as indexes
FROM pg_indexes
WHERE tablename = 'unmet_needs';

-- Check 2.3: Verify indexes on conflicts table
SELECT
  'conflicts Indexes (Phase 1)' as check_type,
  count(*) as index_count,
  string_agg(indexname, ', ' ORDER BY indexname) as indexes
FROM pg_indexes
WHERE tablename = 'conflicts'
AND indexname IN (
  'idx_conflicts_parent_conflict_id',
  'idx_conflicts_conflict_chain_id',
  'idx_conflicts_resentment_level',
  'idx_conflicts_is_continuation',
  'idx_conflicts_is_resolved'
);

-- ============================================================================
-- SECTION 3: RLS (Row Level Security) Verification
-- ============================================================================

-- Check 3.1: Verify RLS is enabled
SELECT
  tablename,
  'RLS Enabled' as status
FROM pg_tables
WHERE tablename IN ('trigger_phrases', 'unmet_needs', 'conflict_enrichment')
AND rowsecurity = true;

-- Check 3.2: Verify RLS policies exist
SELECT
  schemaname,
  tablename,
  policyname,
  qual as policy_definition
FROM pg_policies
WHERE tablename IN ('trigger_phrases', 'unmet_needs', 'conflict_enrichment');

-- ============================================================================
-- SECTION 4: Data Integrity Checks
-- ============================================================================

-- Check 4.1: Count of records in new tables
SELECT
  'trigger_phrases' as table_name,
  count(*) as record_count
FROM trigger_phrases
UNION ALL
SELECT
  'unmet_needs' as table_name,
  count(*) as record_count
FROM unmet_needs
UNION ALL
SELECT
  'conflict_enrichment' as table_name,
  count(*) as record_count
FROM conflict_enrichment;

-- Check 4.2: Sample conflicts with enrichment data
SELECT
  id as conflict_id,
  relationship_id,
  resentment_level,
  has_past_references,
  is_continuation,
  is_resolved,
  array_length(unmet_needs, 1) as unmet_needs_count
FROM conflicts
WHERE resentment_level IS NOT NULL
OR has_past_references IS NOT NULL
LIMIT 5;

-- Check 4.3: Verify foreign key relationships
SELECT
  'Orphaned trigger_phrases (bad foreign key)' as check,
  count(*) as count
FROM trigger_phrases tp
LEFT JOIN conflicts c ON tp.conflict_id = c.id
WHERE c.id IS NULL;

-- Check 4.4: Verify no orphaned unmet_needs
SELECT
  'Orphaned unmet_needs (bad foreign key)' as check,
  count(*) as count
FROM unmet_needs un
LEFT JOIN conflicts c ON un.conflict_id = c.id
WHERE c.id IS NULL;

-- ============================================================================
-- SECTION 5: Performance Checks
-- ============================================================================

-- Check 5.1: Table size
SELECT
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE tablename IN ('trigger_phrases', 'unmet_needs', 'conflict_enrichment', 'conflicts')
AND schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check 5.2: Index size
SELECT
  indexname,
  pg_size_pretty(pg_relation_size(indexname::regclass)) as size
FROM pg_indexes
WHERE tablename IN ('trigger_phrases', 'unmet_needs')
AND indexname LIKE 'idx_%'
ORDER BY pg_relation_size(indexname::regclass) DESC;

-- Check 5.3: Bloat check (unused space in tables)
-- If this returns rows, consider VACUUM
SELECT
  tablename,
  round(100.0 * (CASE WHEN otta > 0 THEN sml.relpages - otta ELSE 0 END) / sml.relpages) as table_bloat_ratio
FROM (
  SELECT
    schemaname,
    tablename,
    cc,
    bs,
    ceil((cc*(datahdr-20))/(bs-20.0)) as otta,
    relpages::bigint
  FROM (
    SELECT
      schemaname,
      tablename,
      CEIL((cc+nullhdr)/bs) as otta,
      cc,
      bs,
      relpages
    FROM (
      SELECT
        schemaname,
        tablename,
        (datawidth+(hdr+8))::float as cc,
        (SELECT (avg(total_hdr_size))::int FROM (SELECT total_hdr_size FROM pg_stat_user_tables) as x) as hdr,
        (SELECT (current_setting('block_size'))::numeric) as bs,
        relpages
      FROM pg_stat_user_tables
      WHERE schemaname IN ('public')
    ) as t1
  ) as t2
) as sml
WHERE tablename IN ('trigger_phrases', 'unmet_needs', 'conflict_enrichment')
AND relpages > 1;

-- ============================================================================
-- SECTION 6: Connection & Permission Checks
-- ============================================================================

-- Check 6.1: Current user
SELECT current_user;

-- Check 6.2: User permissions on new tables
SELECT
  table_name,
  privilege
FROM information_schema.table_privileges
WHERE table_name IN ('trigger_phrases', 'unmet_needs', 'conflict_enrichment')
AND grantee = current_user;

-- ============================================================================
-- SECTION 7: Summary Report
-- ============================================================================

-- Generate comprehensive health report
WITH schema_check AS (
  SELECT
    'Schema' as category,
    CASE
      WHEN count(*) = 3 THEN '✅ PASS - All tables exist'
      ELSE '❌ FAIL - Missing tables'
    END as status,
    count(*) as details
  FROM information_schema.tables
  WHERE table_schema = 'public'
  AND table_name IN ('trigger_phrases', 'unmet_needs', 'conflict_enrichment')
),
columns_check AS (
  SELECT
    'Columns' as category,
    CASE
      WHEN count(*) = 8 THEN '✅ PASS - All columns added to conflicts'
      ELSE '❌ FAIL - Missing columns on conflicts'
    END as status,
    count(*) as details
  FROM information_schema.columns
  WHERE table_name = 'conflicts'
  AND column_name IN (
    'parent_conflict_id',
    'is_continuation',
    'days_since_related_conflict',
    'resentment_level',
    'unmet_needs',
    'has_past_references',
    'conflict_chain_id',
    'is_resolved',
    'resolved_at'
  )
),
views_check AS (
  SELECT
    'Views' as category,
    CASE
      WHEN count(*) = 3 THEN '✅ PASS - All views created'
      ELSE '❌ FAIL - Missing views'
    END as status,
    count(*) as details
  FROM information_schema.tables
  WHERE table_schema = 'public'
  AND table_type = 'VIEW'
  AND table_name IN ('conflict_chains', 'trigger_phrase_analysis', 'unmet_needs_analysis')
),
rls_check AS (
  SELECT
    'RLS' as category,
    CASE
      WHEN count(*) = 3 THEN '✅ PASS - RLS enabled on all tables'
      ELSE '⚠️ WARNING - RLS not fully enabled'
    END as status,
    count(*) as details
  FROM pg_tables
  WHERE tablename IN ('trigger_phrases', 'unmet_needs', 'conflict_enrichment')
  AND rowsecurity = true
)
SELECT category, status, details FROM schema_check
UNION ALL SELECT category, status, details FROM columns_check
UNION ALL SELECT category, status, details FROM views_check
UNION ALL SELECT category, status, details FROM rls_check;

-- ============================================================================
-- SECTION 8: Recommended Actions
-- ============================================================================

-- If you see any issues above, here are recommended actions:

-- ACTION 1: If table bloat detected, run VACUUM
-- VACUUM ANALYZE trigger_phrases;
-- VACUUM ANALYZE unmet_needs;
-- VACUUM ANALYZE conflict_enrichment;

-- ACTION 2: If missing indexes, re-run migration:
-- See migration_conflict_triggers.sql

-- ACTION 3: If RLS not enabled:
-- ALTER TABLE trigger_phrases ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE unmet_needs ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE conflict_enrichment ENABLE ROW LEVEL SECURITY;

-- ACTION 4: If permissions issues:
-- GRANT SELECT, INSERT, UPDATE ON trigger_phrases TO your_app_role;
-- GRANT SELECT, INSERT, UPDATE ON unmet_needs TO your_app_role;
-- GRANT SELECT ON conflict_enrichment TO your_app_role;

-- ============================================================================
-- END OF HEALTH CHECK
-- ============================================================================
-- If all checks pass with ✅, your Phase 1 migration is complete and healthy!
