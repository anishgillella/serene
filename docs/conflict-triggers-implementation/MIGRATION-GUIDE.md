# Supabase Migration Guide - Phase 1

This guide walks you through applying the Phase 1 database schema changes to your Supabase PostgreSQL database.

## Prerequisites

- Access to Supabase dashboard
- Your database URL and credentials
- Knowledge of how to run SQL in Supabase

## Option 1: Using Supabase Dashboard (Recommended for MVP)

### Step 1: Open SQL Editor

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project (Serene)
3. Navigate to **SQL Editor** in the left sidebar
4. Click **New Query**

### Step 2: Copy & Paste Migration SQL

Copy the entire content from `migration_conflict_triggers.sql` (below) and paste it into the SQL editor.

### Step 3: Execute

Click **Run** button or press `Cmd+Enter` (Mac) / `Ctrl+Enter` (Windows/Linux)

### Step 4: Verify

You should see:
- ✅ "Success" message
- New tables created: `trigger_phrases`, `unmet_needs`, `conflict_enrichment`
- New columns added to `conflicts` table
- Views created for analytics

---

## Option 2: Using psql CLI (For Advanced Users)

If you prefer command line:

```bash
# 1. Get your database URL from Supabase (Settings > Database > Connection String)
# It looks like: postgresql://postgres:[password]@[host]/postgres

# 2. Connect to your database
psql "postgresql://postgres:[password]@[host]/postgres"

# 3. Copy & paste the migration SQL
# (contents below)

# 4. Type \q to exit
```

---

## Option 3: Using Migrations in Code (Recommended for Production)

If you want to version control migrations:

```bash
# 1. Copy migration_conflict_triggers.sql to your backend migrations folder
cp backend/app/models/migration_conflict_triggers.sql backend/migrations/

# 2. Run during deployment
# (your deployment process handles running migrations)
```

---

## Migration SQL Script

**Location**: `backend/app/models/migration_conflict_triggers.sql`

The script includes:

### 1. ALTER conflicts TABLE
Adds 8 new columns:
- `parent_conflict_id` - UUID reference to parent conflict
- `is_continuation` - BOOLEAN flag
- `days_since_related_conflict` - INT
- `resentment_level` - INT (1-10)
- `unmet_needs` - TEXT[] array
- `has_past_references` - BOOLEAN
- `conflict_chain_id` - UUID
- `is_resolved` - BOOLEAN
- `resolved_at` - TIMESTAMP

Creates indexes for fast lookups.

### 2. CREATE trigger_phrases TABLE
Stores extracted escalation phrases with:
- Phrase text and category
- Emotional intensity (1-10)
- Whether it references past conflicts
- Speaker identification
- Pattern trigger flags
- Escalation correlation metrics

### 3. CREATE unmet_needs TABLE
Tracks core needs identified in conflicts:
- Need name (feeling_heard, trust, etc.)
- Confidence score (0.0-1.0)
- Which partner expressed it
- Evidence from transcript
- Recurrence tracking (chronic needs)

### 4. CREATE conflict_enrichment TABLE
Cache table for enrichment results to avoid reprocessing.

### 5. CREATE VIEWS
- `conflict_chains` - Query related conflicts easily
- `trigger_phrase_analysis` - Pre-aggregated phrase statistics
- `unmet_needs_analysis` - Pre-aggregated needs tracking

### 6. Enable RLS (Row Level Security)
All new tables have RLS enabled with public access policies (MVP only).

---

## Step-by-Step in Supabase Dashboard

### 1. Open SQL Editor
```
Supabase Dashboard → SQL Editor → New Query
```

### 2. Paste the Migration Script
Copy entire contents of `migration_conflict_triggers.sql`

### 3. Execute
Click **Run** or press `Cmd+Enter`

### 4. Check Results

You should see output like:
```
CREATE EXTENSION (if not exists)
ALTER TABLE conflicts ADD COLUMN ...
CREATE TABLE trigger_phrases (...)
CREATE TABLE unmet_needs (...)
CREATE TABLE conflict_enrichment (...)
CREATE OR REPLACE VIEW conflict_chains ...
...
```

### 5. Verify in Table Editor

Navigate to **Table Editor** and verify:
- ✅ `conflicts` table has new columns
- ✅ `trigger_phrases` table exists
- ✅ `unmet_needs` table exists
- ✅ `conflict_enrichment` table exists

---

## Verify the Migration

### Check New Tables Exist

```sql
-- Run in SQL Editor to verify
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('trigger_phrases', 'unmet_needs', 'conflict_enrichment');
```

Expected output:
```
 table_name
────────────────────
 trigger_phrases
 unmet_needs
 conflict_enrichment
```

### Check Conflicts Table Columns

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'conflicts'
ORDER BY ordinal_position;
```

You should see the new columns:
- `parent_conflict_id uuid`
- `resentment_level integer`
- `unmet_needs text[]`
- `has_past_references boolean`
- `is_continuation boolean`
- `conflict_chain_id uuid`
- `is_resolved boolean`
- `resolved_at timestamp with time zone`

### Check Views Created

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_type = 'VIEW';
```

You should see:
- `conflict_chains`
- `trigger_phrase_analysis`
- `unmet_needs_analysis`

---

## Rollback (If Needed)

If something goes wrong, you can rollback the migration:

```sql
-- Drop new tables
DROP TABLE IF EXISTS trigger_phrases CASCADE;
DROP TABLE IF EXISTS unmet_needs CASCADE;
DROP TABLE IF EXISTS conflict_enrichment CASCADE;

-- Drop views
DROP VIEW IF EXISTS conflict_chains CASCADE;
DROP VIEW IF EXISTS trigger_phrase_analysis CASCADE;
DROP VIEW IF EXISTS unmet_needs_analysis CASCADE;

-- Revert conflicts table changes
ALTER TABLE conflicts
DROP COLUMN IF EXISTS parent_conflict_id,
DROP COLUMN IF EXISTS is_continuation,
DROP COLUMN IF EXISTS days_since_related_conflict,
DROP COLUMN IF EXISTS resentment_level,
DROP COLUMN IF EXISTS unmet_needs,
DROP COLUMN IF EXISTS has_past_references,
DROP COLUMN IF EXISTS conflict_chain_id,
DROP COLUMN IF EXISTS is_resolved,
DROP COLUMN IF EXISTS resolved_at;
```

⚠️ **Warning**: This will delete all data in the new tables!

---

## Troubleshooting

### Error: "relation already exists"

This means the table was already created. You can safely ignore it, or use:

```sql
CREATE TABLE IF NOT EXISTS trigger_phrases (...)
```

The migration script already uses `IF NOT EXISTS` for most statements.

### Error: "column already exists"

The column was already added. This is safe to ignore.

### Error: "permission denied"

You need to be logged in as a user with create table permissions (usually `postgres` role).

### Connection timeout

Your Supabase instance might be asleep. Refresh the page and try again.

---

## Testing the Migration

After migration, test that the system works:

### 1. Verify Tables are Empty (First Migration)

```sql
SELECT COUNT(*) FROM trigger_phrases;
SELECT COUNT(*) FROM unmet_needs;
```

Both should return `0` (no data yet).

### 2. Insert Test Data

```sql
-- Insert test relationship (if needed)
INSERT INTO relationships (id, partner_a_name, partner_b_name)
VALUES ('00000000-0000-0000-0000-000000000000', 'Adrian', 'Elara')
ON CONFLICT (id) DO NOTHING;

-- Insert test conflict
INSERT INTO conflicts (id, relationship_id, started_at, status)
VALUES ('test-conflict-1', '00000000-0000-0000-0000-000000000000', NOW(), 'completed')
ON CONFLICT (id) DO NOTHING;

-- Insert test trigger phrase
INSERT INTO trigger_phrases (
  relationship_id, conflict_id, phrase, phrase_category,
  emotional_intensity, references_past_conflict, speaker,
  is_pattern_trigger
)
VALUES (
  '00000000-0000-0000-0000-000000000000',
  'test-conflict-1',
  'You didn''t do that yesterday',
  'temporal_reference',
  8,
  true,
  'partner_a',
  true
);

-- Verify it was inserted
SELECT * FROM trigger_phrases WHERE conflict_id = 'test-conflict-1';
```

---

## Next Steps

After migration:

1. **Restart your backend** - The Python services will use the new tables
2. **Test the enrichment** - Create a new conflict transcript and check for enriched data
3. **Verify in database** - Check that trigger_phrases and unmet_needs are being populated
4. **Monitor logs** - Watch for any enrichment service errors

---

## Data Backup (Recommended Before Migration)

Before running the migration, backup your conflicts table:

```sql
-- Create backup table
CREATE TABLE conflicts_backup_2024_12_25 AS SELECT * FROM conflicts;

-- Later, if needed, restore:
-- TRUNCATE conflicts;
-- INSERT INTO conflicts SELECT * FROM conflicts_backup_2024_12_25;
```

---

## Performance Considerations

### Indexes Created

The migration creates indexes for:
- `parent_conflict_id` - Fast conflict linking queries
- `conflict_chain_id` - Fast conflict chain lookups
- `trigger_phrases(relationship_id, phrase)` - Fast phrase lookups
- `unmet_needs(relationship_id, need)` - Fast need lookups

These should keep queries performant even with large datasets.

### Expected Query Times

With proper indexes:
- Get trigger phrases for relationship: ~10-50ms
- Get unmet needs: ~10-50ms
- Get previous conflicts: ~50-100ms
- Update conflict enrichment: ~20-50ms

---

## Production Deployment Checklist

- [ ] Backup current database
- [ ] Run migration in test/staging first
- [ ] Verify all new tables and columns exist
- [ ] Verify RLS policies are correct
- [ ] Test enrichment service with sample conflict
- [ ] Monitor error logs after deployment
- [ ] Roll back plan ready if needed

---

## Support

If you encounter issues:

1. Check **Supabase Status** - Is the service healthy?
2. Check **Database Logs** - Supabase → Logs → Database
3. Run verification queries above
4. Check backend logs for enrichment errors

For Supabase-specific issues, contact: support@supabase.io
