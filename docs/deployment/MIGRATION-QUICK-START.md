# 🚀 Phase 1 Migration: Quick Start Guide

**⏱️ Time Required**: 5-10 minutes
**📍 Location**: Supabase Dashboard → SQL Editor
**✅ Status**: Ready to Deploy

---

## The TL;DR

1. Go to Supabase SQL Editor
2. Copy `docs/conflict-triggers-implementation/QUICK-MIGRATION.sql`
3. Paste & Run
4. Done! ✨

---

## Step-by-Step

### Step 1: Open Supabase Dashboard

```
https://supabase.com/dashboard
↓
Select "Serene" project
↓
Click "SQL Editor" (left sidebar)
↓
Click "+ New Query"
```

### Step 2: Copy Migration Script

**File**: `docs/conflict-triggers-implementation/QUICK-MIGRATION.sql`

Copy the entire contents.

### Step 3: Paste into Supabase

Paste into the blank SQL editor window.

### Step 4: Execute

Click **Run** button or press **Cmd+Enter**

Wait 2-5 seconds...

### Step 5: Verify Success

Look for:
```
✅ Success message at bottom
```

---

## Verify It Worked (2 minutes)

### Check 1: Tables Exist

Copy this into a new SQL query:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_name IN ('trigger_phrases', 'unmet_needs', 'conflict_enrichment');
```

**Expected result**: 3 rows returned

### Check 2: Columns Added to conflicts

```sql
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'conflicts'
AND column_name IN ('parent_conflict_id', 'resentment_level', 'unmet_needs');
```

**Expected result**: 3 rows returned

### Check 3: Visual Verification

1. Go to **Table Editor** (left sidebar)
2. Look for: `trigger_phrases` table ✅
3. Look for: `unmet_needs` table ✅
4. Look for: `conflict_enrichment` table ✅
5. Click `conflicts` table and scroll right
6. Verify new columns exist ✅

---

## Next: Restart Backend

```bash
cd backend
source venv/bin/activate
# Restart your uvicorn server
# (Kill existing process and start new one)
```

**Watch logs for**: `✅ Conflict enrichment complete...`

---

## Test It Works (Optional)

1. Create a new conflict in the app
2. Record a transcript
3. Check database:

```sql
SELECT COUNT(*) as trigger_phrases_count FROM trigger_phrases;
SELECT COUNT(*) as unmet_needs_count FROM unmet_needs;
```

Both should be **> 0** if enrichment ran successfully.

---

## If Something Goes Wrong

### Error: "relation already exists"
→ Run migration again (it's safe)

### Error: "permission denied"
→ Make sure you're logged in as `postgres` user

### Error: "timeout"
→ Refresh page and try again

### No data in trigger_phrases/unmet_needs
→ Check backend logs for enrichment errors
→ Verify database connection in backend

**Detailed troubleshooting**: See `docs/conflict-triggers-implementation/MIGRATION-GUIDE.md`

---

## Reference Files

| Need | File |
|------|------|
| Run migration | `docs/conflict-triggers-implementation/QUICK-MIGRATION.sql` |
| Verify it worked | `docs/conflict-triggers-implementation/DATABASE-HEALTH-CHECK.sql` |
| Detailed guide | `docs/conflict-triggers-implementation/MIGRATION-GUIDE.md` |
| Step-by-step | `docs/conflict-triggers-implementation/MIGRATION-STEPS.md` |
| Production checklist | `DEPLOYMENT-CHECKLIST.md` |
| Full overview | `PHASE-1-COMPLETE.md` |

---

## That's It!

You've successfully deployed Phase 1. The system is now:

- ✅ Capturing trigger phrases
- ✅ Identifying unmet needs
- ✅ Linking conflicts
- ✅ Tracking resentment
- ✅ Ready for Phase 2+

**Enjoy! 🎉**
