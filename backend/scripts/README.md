# Data Verification Scripts

Scripts for verifying data integrity and querying ground truth across all storage systems.

## Scripts

### `verify_data_integrity.py`

Verifies that all data exists in all 3 storage locations (Database, Storage, Pinecone).

**Usage:**
```bash
# Check all conflicts
python scripts/verify_data_integrity.py

# Check specific conflict
python scripts/verify_data_integrity.py --conflict-id <conflict_id>

# Check all conflicts for a relationship
python scripts/verify_data_integrity.py --relationship-id <relationship_id>

# Check specific profile
python scripts/verify_data_integrity.py --profile-id <profile_id>
```

**Output:**
- Summary of complete vs incomplete items
- List of issues found (missing in some locations)

### `query_ground_truth.py`

Query and compare data from all 3 sources side-by-side for ground truth verification.

**Usage:**
```bash
# Query conflict
python scripts/query_ground_truth.py --conflict-id <conflict_id>

# Query conflict with analysis and repair plans
python scripts/query_ground_truth.py --conflict-id <conflict_id> --analysis --repair-plans

# Query profile
python scripts/query_ground_truth.py --profile-id <profile_id>
```

**Output:**
- Side-by-side comparison of data from Database, Storage, and Pinecone
- Shows actual data content for verification

## Setup

1. Ensure environment variables are set (`.env.local` or `.env`):
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `PINECONE_API_KEY`
   - `DATABASE_URL`

2. Run from backend directory:
   ```bash
   cd backend
   python scripts/verify_data_integrity.py
   ```

## Example Output

```
🔍 Verifying all conflicts...
  Checking conflict 7f136c56...
  Checking conflict a1b2c3d4...

================================================================================
VERIFICATION SUMMARY
================================================================================

Total items checked: 12
✅ Complete (all 3 locations): 10
⚠️  Incomplete (missing in some locations): 2

⚠️  ISSUES FOUND:

  analysis - 7f136c56
    - Missing in Pinecone (analysis namespace)

  repair_plan - a1b2c3d4
    - Missing in storage: repair_plans/rel_id/conflict_id_repair_partner_a.json
```

