# Step-by-Step: Run Migration on Supabase

## 🎯 Goal
Apply Phase 1 database schema to your Supabase PostgreSQL database in 5 minutes.

## ⏱️ Time Required
- **5 minutes** - if you have Supabase access
- **10 minutes** - if you need to find credentials first

---

## Method 1: Supabase Dashboard (Easiest) ⭐

### Step 1️⃣: Open Supabase Dashboard

1. Go to https://supabase.com/dashboard
2. Log in with your credentials
3. Select your "Serene" project
4. Click on **SQL Editor** in the left sidebar

**Screenshot reference**: Top left → "SQL Editor" menu item

### Step 2️⃣: Create New Query

1. Click **+ New Query** button (top right)
2. You should see a blank SQL editor

### Step 3️⃣: Copy Migration SQL

1. **Option A** (Recommended for first-time):
   - Copy the contents of `QUICK-MIGRATION.sql`
   - Paste into the SQL editor

2. **Option B** (For detailed control):
   - Copy the contents of `migration_conflict_triggers.sql`
   - Paste into the SQL editor

**Which to choose?**
- **QUICK-MIGRATION.sql**: Smaller, faster, all-in-one
- **migration_conflict_triggers.sql**: More detailed comments, can be split if needed

### Step 4️⃣: Execute the Migration

1. Click the **Run** button (or press `Cmd+Enter` / `Ctrl+Enter`)
2. Wait 2-5 seconds for execution
3. You should see **"Success"** message at bottom

**Expected output**:
```
CREATE EXTENSION
ALTER TABLE
CREATE TABLE
CREATE INDEX
...
```

### Step 5️⃣: Verify It Worked

1. Navigate to **Table Editor** (left sidebar)
2. Look for these new tables:
   - ✅ `trigger_phrases`
   - ✅ `unmet_needs`
   - ✅ `conflict_enrichment`

3. Click on **conflicts** table
4. Scroll right to see new columns:
   - ✅ `parent_conflict_id`
   - ✅ `resentment_level`
   - ✅ `unmet_needs`
   - ✅ `has_past_references`
   - ✅ `is_continuation`
   - ✅ `conflict_chain_id`
   - ✅ `is_resolved`
   - ✅ `resolved_at`

**All there? You're done! 🎉**

---

## Method 2: Command Line (Advanced)

### Step 1️⃣: Get Connection String

1. Go to Supabase Dashboard
2. Click **Settings** → **Database**
3. Under "Connection String", select **psql** tab
4. Copy the entire connection string (looks like):
   ```
   postgresql://postgres:[password]@[host]/postgres
   ```

### Step 2️⃣: Connect to Database

```bash
# Paste your connection string here
psql "postgresql://postgres:[password]@[host]/postgres"
```

You should see:
```
postgres=>
```

### Step 3️⃣: Run Migration

1. Open `QUICK-MIGRATION.sql` in a text editor
2. Copy all contents
3. Paste into psql terminal
4. Press Enter

You should see completion messages.

### Step 4️⃣: Verify

```sql
-- Check new tables exist
SELECT table_name FROM information_schema.tables
WHERE table_name IN ('trigger_phrases', 'unmet_needs', 'conflict_enrichment');
```

Exit:
```sql
\q
```

---

## Verification Queries

Run these in Supabase SQL Editor to confirm everything worked:

### Query 1: Check New Tables

```sql
-- Should return 3 rows
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('trigger_phrases', 'unmet_needs', 'conflict_enrichment')
ORDER BY table_name;
```

**Expected output**:
```
 table_name
────────────────────
 conflict_enrichment
 trigger_phrases
 unmet_needs
```

### Query 2: Check New Columns on conflicts

```sql
-- Should return 8 new columns
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'conflicts'
AND column_name IN (
  'parent_conflict_id',
  'is_continuation',
  'resentment_level',
  'unmet_needs',
  'has_past_references',
  'conflict_chain_id',
  'is_resolved',
  'resolved_at'
)
ORDER BY column_name;
```

**Expected output**:
```
       column_name        |              data_type
──────────────────────────┼────────────────────────────────
 conflict_chain_id        | uuid
 has_past_references      | boolean
 is_continuation          | boolean
 is_resolved              | boolean
 parent_conflict_id       | uuid
 resentment_level         | integer
 resolved_at              | timestamp with time zone
 unmet_needs              | text[]
```

### Query 3: Check Views Created

```sql
-- Should return 3 views
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_type = 'VIEW'
AND table_name LIKE '%trigger_phrase%'
OR table_name LIKE '%unmet_need%'
OR table_name LIKE '%conflict_chain%'
ORDER BY table_name;
```

**Expected output**:
```
       table_name
────────────────────────────
 conflict_chains
 trigger_phrase_analysis
 unmet_needs_analysis
```

### Query 4: Test Insert (Optional)

```sql
-- Insert a test trigger phrase to verify everything works
INSERT INTO trigger_phrases (
  relationship_id,
  conflict_id,
  phrase,
  phrase_category,
  emotional_intensity,
  references_past_conflict,
  speaker,
  is_pattern_trigger
)
VALUES (
  '00000000-0000-0000-0000-000000000000',
  '00000000-0000-0000-0000-000000000001',
  'Test phrase',
  'temporal_reference',
  5,
  true,
  'partner_a',
  false
)
RETURNING *;
```

If this succeeds, the table is working! (You can delete this test row later)

---

## Troubleshooting

### ❌ Error: "relation already exists"

**Cause**: Table was already created in a previous attempt.

**Solution**: This is fine! The migration uses `CREATE TABLE IF NOT EXISTS`, so it won't fail. Just run it again.

### ❌ Error: "column already exists"

**Cause**: You ran the migration twice.

**Solution**: This is expected and safe. Continue with verification.

### ❌ Error: "permission denied"

**Cause**: You're not logged in as a user with CREATE permissions.

**Solution**:
1. Make sure you're using the `psql` connection string (not the JavaScript one)
2. Use the `postgres` user (not a restricted user)

### ❌ Error: "syntax error"

**Cause**: The SQL was corrupted during copy-paste.

**Solution**:
1. Try again with fresh copy-paste
2. Use QUICK-MIGRATION.sql (it's simpler)

### ❌ Error: "timeout"

**Cause**: Supabase database is asleep or slow.

**Solution**:
1. Refresh the page
2. Wait a minute
3. Try again

---

## After Migration

### 1. Restart Your Backend

```bash
# In your backend directory
cd backend
source venv/bin/activate
# Restart your uvicorn server
```

### 2. Test the Enrichment

1. Create a new conflict in the app
2. Record a transcript
3. Check the database for:
   - Rows in `trigger_phrases` table
   - Rows in `unmet_needs` table
   - Updated `conflicts` row with `resentment_level`, etc.

### 3. Monitor Logs

Watch for any errors in your backend logs related to:
- `conflict_enrichment_service`
- `trigger_phrases`
- `unmet_needs`

---

## Rollback (If Something Goes Wrong)

⚠️ **Only do this if you want to undo the migration!**

```sql
-- Drop the new tables (this will DELETE all data in them)
DROP TABLE IF EXISTS trigger_phrases CASCADE;
DROP TABLE IF EXISTS unmet_needs CASCADE;
DROP TABLE IF EXISTS conflict_enrichment CASCADE;

-- Drop the views
DROP VIEW IF EXISTS conflict_chains CASCADE;
DROP VIEW IF EXISTS trigger_phrase_analysis CASCADE;
DROP VIEW IF EXISTS unmet_needs_analysis CASCADE;

-- Remove new columns from conflicts table
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

---

## Summary Checklist

- [ ] Opened Supabase SQL Editor
- [ ] Copied QUICK-MIGRATION.sql
- [ ] Pasted into SQL Editor
- [ ] Clicked Run button
- [ ] Got "Success" message
- [ ] Verified new tables exist (Table Editor)
- [ ] Verified new columns on conflicts table
- [ ] Verified views created
- [ ] Restarted backend
- [ ] Ready for Phase 1 testing! ✅

---

## Next Steps

Now that the database is ready:

1. **Test Phase 1** - Create a conflict and verify enrichment data
2. **Review logs** - Check backend logs for any enrichment errors
3. **Proceed to Phase 2** - Start implementing pattern detection analytics (optional)
4. **Proceed to Phase 3** - Integrate context awareness into Luna (optional)
5. **Proceed to Phase 4** - Build analytics dashboard (optional)

---

## Questions?

If something doesn't work:

1. Check **MIGRATION-GUIDE.md** for detailed troubleshooting
2. Review the verification queries above
3. Check **Supabase Status** (https://status.supabase.io)
4. Check your backend logs for enrichment service errors

You've got this! 🚀
