# Phase 1 Deployment Checklist

Complete this checklist to deploy Phase 1 (Conflict Triggers & Escalation Analysis) to production.

---

## Pre-Deployment (Before Running Migration)

- [ ] **Backup Database**
  - Go to Supabase Dashboard → Settings → Database → Backups
  - Verify recent backup exists (within last 24 hours)
  - (Or manually create backup with: `CREATE TABLE conflicts_backup_2024_12_25 AS SELECT * FROM conflicts;`)

- [ ] **Review Changes**
  - Read `docs/conflict-triggers-implementation/00-OVERVIEW.md`
  - Review migration SQL in `QUICK-MIGRATION.sql`
  - Understand impact on existing conflict data (non-breaking, additive only)

- [ ] **Staging Test (Optional but Recommended)**
  - If you have a staging environment, run migration there first
  - Test that backend still works
  - Create a test conflict and verify enrichment data

- [ ] **Notify Team**
  - Let team know migration is happening
  - Brief 5-minute downtime possible (though should be <10 seconds)
  - Plan for any manual testing after deployment

---

## Migration Execution (Running the SQL)

### Method A: Supabase Dashboard (Recommended)

- [ ] **Open Supabase Dashboard**
  - Navigate to https://supabase.com/dashboard
  - Select your Serene project
  - Go to SQL Editor

- [ ] **Create New Query**
  - Click "+ New Query"
  - Copy entire contents of `docs/conflict-triggers-implementation/QUICK-MIGRATION.sql`
  - Paste into SQL editor

- [ ] **Execute**
  - Click "Run" button or press Cmd+Enter
  - Wait for completion (2-5 seconds)
  - Verify "Success" message at bottom

- [ ] **Save Query** (Optional)
  - Name it: "Phase 1: Conflict Triggers Migration"
  - Save for future reference

### Method B: Command Line

- [ ] **Get Connection String**
  - Supabase Dashboard → Settings → Database → Connection String (psql tab)
  - Copy the connection string

- [ ] **Connect & Run**
  - `psql "<your-connection-string>"`
  - Copy-paste contents of `QUICK-MIGRATION.sql`
  - Press Enter

- [ ] **Verify Success**
  - Should see completion messages
  - Type `\q` to exit

---

## Post-Migration Verification

### Immediate Checks (Before Restarting Backend)

- [ ] **Run Health Check**
  - Open SQL Editor
  - Copy entire contents of `docs/conflict-triggers-implementation/DATABASE-HEALTH-CHECK.sql`
  - Run it
  - Look for ✅ PASS on all checks

- [ ] **Verify Tables Exist**
  - Supabase Dashboard → Table Editor
  - Look for:
    - ✅ `trigger_phrases`
    - ✅ `unmet_needs`
    - ✅ `conflict_enrichment`

- [ ] **Verify Columns Added to conflicts**
  - Supabase → Table Editor → conflicts
  - Scroll right and verify new columns:
    - ✅ `parent_conflict_id`
    - ✅ `resentment_level`
    - ✅ `unmet_needs`
    - ✅ `has_past_references`
    - ✅ `is_continuation`
    - ✅ `conflict_chain_id`
    - ✅ `is_resolved`
    - ✅ `resolved_at`

- [ ] **Verify Views Created**
  - Run this in SQL Editor:
    ```sql
    SELECT table_name FROM information_schema.tables
    WHERE table_type = 'VIEW'
    AND table_name IN ('conflict_chains', 'trigger_phrase_analysis', 'unmet_needs_analysis');
    ```
  - Should return 3 rows

### Backend Restart

- [ ] **Restart Backend Service**
  ```bash
  cd backend
  source venv/bin/activate
  # Kill any running uvicorn process
  # Restart: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  ```

- [ ] **Verify Backend Starts**
  - Check logs for startup messages
  - No errors related to:
    - `trigger_phrases`
    - `unmet_needs`
    - `conflict_enrichment`
  - Ensure API is responding: `curl http://localhost:8000/docs`

- [ ] **Check Backend Logs**
  - Look for any import errors in `conflict_enrichment_service`
  - Verify no database connection issues

### Functional Testing

- [ ] **Create Test Conflict**
  - Use frontend or API to create a test conflict
  - Record a sample transcript
  - Submit the transcript

- [ ] **Verify Enrichment Ran**
  - Check database for entries in `trigger_phrases` and `unmet_needs`
  - Run: `SELECT COUNT(*) FROM trigger_phrases;` (should be > 0)
  - Run: `SELECT COUNT(*) FROM unmet_needs;` (should be > 0)

- [ ] **Check Enrichment Data Quality**
  - Sample trigger phrase:
    ```sql
    SELECT phrase, phrase_category, emotional_intensity, speaker
    FROM trigger_phrases LIMIT 1;
    ```
  - Should see real data from the transcript

- [ ] **Verify No Backend Errors**
  - Check logs for errors in conflict enrichment
  - Look for pattern: `✅ Conflict enrichment complete` in logs
  - No errors like "Error enriching conflict"

---

## Post-Deployment (After Verification)

- [ ] **Update Documentation**
  - Update your deployment docs to mention Phase 1 is active
  - Document how to run the health check query

- [ ] **Monitor for 24 Hours**
  - Watch error logs for any enrichment failures
  - Monitor database performance
  - Create a few more test conflicts to verify consistency

- [ ] **Celebrate! 🎉**
  - Phase 1 is now live
  - Conflict trigger analysis is running
  - Proceed to Phase 2 when ready

---

## Rollback Plan (If Something Goes Wrong)

If something fails, follow these steps:

### Minor Issues (Errors but system still works)

- [ ] **Check Logs**
  - Backend logs for enrichment errors
  - Supabase logs for database errors

- [ ] **Re-run Health Check**
  - Use `DATABASE-HEALTH-CHECK.sql`
  - Identify specific failures

- [ ] **Fix Individual Issues**
  - Missing index? Rerun relevant CREATE INDEX statements
  - RLS policy issue? Rerun RLS policy creation
  - See MIGRATION-GUIDE.md for detailed troubleshooting

### Major Issues (Backend won't start)

- [ ] **Immediate Action**
  - Don't panic! The old data is still fine
  - The new tables are separate from existing tables

- [ ] **Revert Migration (Option 1)**
  - Run rollback script from MIGRATION-GUIDE.md
  - This will drop new tables (but not affect conflicts table much)
  - Restart backend

- [ ] **Fix & Re-run (Option 2)**
  - Debug the issue
  - Restart backend with original code
  - Fix the issue in the code
  - Re-run migration

### Complete Rollback (Nuclear Option)

- [ ] **Drop Everything**
  ```sql
  -- Run in Supabase SQL Editor
  DROP TABLE IF EXISTS trigger_phrases CASCADE;
  DROP TABLE IF EXISTS unmet_needs CASCADE;
  DROP TABLE IF EXISTS conflict_enrichment CASCADE;
  DROP VIEW IF EXISTS conflict_chains CASCADE;
  DROP VIEW IF EXISTS trigger_phrase_analysis CASCADE;
  DROP VIEW IF EXISTS unmet_needs_analysis CASCADE;
  ```

- [ ] **Revert Code Changes**
  - If changes to `conflict_enrichment_service.py` caused issues
  - Remove or disable the enrichment service integration
  - Commit changes

- [ ] **Restart Backend**
  - `uvicorn app.main:app --reload`

- [ ] **Restore from Backup** (Last Resort)
  - Supabase Dashboard → Settings → Database → Backups
  - Restore to pre-migration backup
  - This will revert all data, including any new conflicts

---

## Key Contacts & Resources

- **Supabase Status**: https://status.supabase.io
- **Supabase Docs**: https://supabase.com/docs
- **Phase 1 Docs**: `docs/conflict-triggers-implementation/`
- **Migration Guide**: `docs/conflict-triggers-implementation/MIGRATION-GUIDE.md`
- **Health Check**: `docs/conflict-triggers-implementation/DATABASE-HEALTH-CHECK.sql`

---

## Sign-Off

- [ ] **Migration Completed Successfully**
- [ ] **All Verification Tests Passed**
- [ ] **Backend Restarted & Working**
- [ ] **Test Conflict Created & Enriched Successfully**
- [ ] **No Error Logs for 24 Hours**
- [ ] **Ready for Phase 2 or Production Use**

**Deployed By**: ________________
**Date**: ________________
**Time**: ________________
**Notes**: ________________

---

## Quick Reference: File Locations

| File | Purpose | Location |
|------|---------|----------|
| QUICK-MIGRATION.sql | Fast migration script | `docs/conflict-triggers-implementation/QUICK-MIGRATION.sql` |
| migration_conflict_triggers.sql | Detailed migration script | `backend/app/models/migration_conflict_triggers.sql` |
| DATABASE-HEALTH-CHECK.sql | Verify migration success | `docs/conflict-triggers-implementation/DATABASE-HEALTH-CHECK.sql` |
| MIGRATION-GUIDE.md | Detailed instructions | `docs/conflict-triggers-implementation/MIGRATION-GUIDE.md` |
| MIGRATION-STEPS.md | Step-by-step walkthrough | `docs/conflict-triggers-implementation/MIGRATION-STEPS.md` |
| conflict_enrichment_service.py | Backend service | `backend/app/services/conflict_enrichment_service.py` |

---

**Phase 1 Deployment Checklist Complete! 🚀**

Next: Proceed to Phase 2 (Pattern Detection) when ready.
