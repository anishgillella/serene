# Serene Multi-Tenancy Conversion Plan

## Overview

This documentation outlines the conversion of Serene from a single-couple MVP (hardcoded "Adrian & Elara") to a multi-tenant application where any couple can use the platform.

## Current State

| Issue | Details |
|-------|---------|
| Hardcoded Relationship ID | `DEFAULT_RELATIONSHIP_ID = "00000000-0000-0000-0000-000000000000"` in 20+ files |
| Hardcoded Names | "Adrian Malhotra" / "Elara Voss" in 21 files |
| No Couple Selection | App assumes single couple |
| Data Leakage Risk | One RAG query missing `relationship_id` filter |

## Solution: Relationship-Based Routing (No Auth Required)

Instead of user authentication, we identify couples by their **relationship_id** passed via URL params, headers, or localStorage.

```
┌─────────────────────────────────────────────────────────────┐
│                    How It Works                              │
├─────────────────────────────────────────────────────────────┤
│  1. First visit → Show "Create Relationship" or enter names │
│  2. Create → Generate new relationship_id, store in localStorage │
│  3. All API calls include relationship_id as parameter      │
│  4. Partner names stored in couple_profiles table           │
│  5. Shareable link: serene.app/?r={relationship_id}         │
└─────────────────────────────────────────────────────────────┘
```

## New Data Model

```
couple_profiles (NEW - simple partner details)
├── id: UUID
├── relationship_id: UUID → relationships.id (unique)
├── partner_a_name: TEXT (e.g., "Adrian")
├── partner_a_email: TEXT (optional, for future notifications)
├── partner_b_name: TEXT (e.g., "Elara")
├── partner_b_email: TEXT (optional)
├── created_at: TIMESTAMP
└── updated_at: TIMESTAMP

Test Data (seeded):
- relationship_id: 00000000-0000-0000-0000-000000000000
- partner_a_name: "Adrian"
- partner_b_name: "Elara"
```

## User Flow

| Step | What Happens |
|------|--------------|
| **New Couple** | Enter both partner names → Creates relationship + couple_profile → Stores ID in localStorage |
| **Returning User** | App checks localStorage for `relationship_id` → Loads their data |
| **Switching Couples** | URL param `?r={id}` overrides localStorage (for testing/demos) |
| **Share with Partner** | Copy link with relationship_id → Partner opens → Same data |

## API Pattern

```python
# Every endpoint resolves relationship_id from:
# 1. Query param: ?relationship_id=xxx
# 2. Header: X-Relationship-ID
# 3. Fallback: DEFAULT_RELATIONSHIP_ID (for backward compatibility)

@router.get("/conflicts")
async def list_conflicts(relationship_id: str = Query(default=DEFAULT_RELATIONSHIP_ID)):
    conflicts = db_service.get_all_conflicts(relationship_id)
    return {"conflicts": conflicts}
```

## Frontend Pattern

```typescript
// Store on relationship creation
localStorage.setItem('serene_relationship_id', relationshipId);

// Include in all API calls
const relationshipId = localStorage.getItem('serene_relationship_id')
                       || '00000000-0000-0000-0000-000000000000';

fetch(`${API_URL}/api/conflicts?relationship_id=${relationshipId}`);
```

## Phases (Simplified)

| Phase | Name | Goal | Status |
|-------|------|------|--------|
| 1 | ~~Authentication Foundation~~ | ~~Add Auth0~~ | Deferred |
| 2 | [Multi-Tenancy Core](./02-phase-multi-tenancy-core.md) | couple_profiles table, dynamic relationship_id | **Next** |
| 3 | ~~Partner Invitation~~ | ~~Email invites~~ | Deferred (use shareable links instead) |
| 4 | [Data Model Cleanup](./04-phase-data-model-cleanup.md) | Gender-neutral schema | Later |
| 5 | ~~Security Hardening~~ | ~~RLS policies~~ | Deferred (requires auth) |
| 6 | [Future: Auth & Security](./06-phase-future-optimizations.md) | Add Auth0 when ready | Future |

## Implementation Order (Revised)

```
Phase 2 (Multi-Tenancy Core)
    │
    ├── Create couple_profiles table
    ├── Seed Adrian/Elara test data
    ├── Update backend to read relationship_id from requests
    ├── Add frontend localStorage + couple selection UI
    └── Fix RAG security bug
    │
    ▼
Phase 4 (Data Model Cleanup) - Optional
    │
    ▼
Phase 6 (Auth) - When Ready
```

## Test Data

The default test couple (Adrian & Elara) is preserved:

| Field | Value |
|-------|-------|
| relationship_id | `00000000-0000-0000-0000-000000000000` |
| partner_a_name | Adrian |
| partner_b_name | Elara |

All existing conflicts, transcripts, and analysis remain accessible under this ID.

## Security Note

- Without auth, anyone with a relationship_id can access that couple's data
- UUIDs are 128-bit random, practically impossible to guess
- Acceptable for MVP; auth can be added later for production security
- Easy migration path: link relationship_id to user accounts when auth is implemented

## Files to Modify (Phase 2)

| File | Changes |
|------|---------|
| `backend/app/models/migrations/002_couple_profiles.sql` | Create table, seed data |
| `backend/app/services/db_service.py` | Add couple_profiles methods |
| `backend/app/main.py` | Read relationship_id from requests |
| `backend/app/routes/post_fight.py` | Use dynamic relationship_id |
| `backend/app/routes/calendar.py` | Use dynamic relationship_id |
| `backend/app/routes/analytics.py` | Use dynamic relationship_id |
| `backend/app/services/transcript_rag.py` | Fix missing filter (security) |
| `frontend/src/App.tsx` | Add couple selection/creation flow |
| `frontend/src/components/navigation/Sidebar.tsx` | Show dynamic partner names |
