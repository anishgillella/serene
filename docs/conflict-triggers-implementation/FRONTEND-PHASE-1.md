# Frontend Integration - Phase 1: Data Capture

**Phase**: 1 - Data Capture & Enrichment
**Timeline**: 1-2 weeks (concurrent with backend)
**Priority**: Medium (enrichment works without frontend changes)
**User Impact**: None (no visible changes, data captured in background)

---

## Overview

Phase 1 enrichment happens entirely in the backend. The frontend doesn't need changes to capture trigger phrases and unmet needs. However, we recommend preparing the infrastructure for displaying this data in future phases.

---

## What Changed in Backend

- ✅ Trigger phrases extracted from transcripts
- ✅ Unmet needs identified
- ✅ Resentment level calculated
- ✅ Conflicts linked together
- ✅ All stored in database

---

## Frontend: No Changes Required

The frontend continues working as-is. Enrichment happens silently in the background:

1. User records conflict → Frontend handles normally
2. Transcript stored → Backend enriches automatically
3. No UI changes needed
4. Data available for Phase 2+

---

## Optional: Prepare for Phase 2

### Add Enrichment Status Indicator (Optional)

While not necessary for Phase 1, you could add a visual indicator that enrichment is in progress:

**File**: `src/pages/PostFightSession.tsx`

```tsx
// Optional: Show enrichment status
const [enrichmentStatus, setEnrichmentStatus] = useState<'idle' | 'enriching' | 'complete'>('idle');

// When conflict is stored
const handleStoreTranscript = async () => {
  setEnrichmentStatus('enriching');

  // ... existing code to store transcript ...

  // Check enrichment completion (optional polling)
  setTimeout(() => setEnrichmentStatus('complete'), 3000);
};

// Optional UI
{enrichmentStatus === 'enriching' && (
  <div className="p-4 bg-blue-50 rounded">
    <p className="text-sm text-blue-600">
      📊 Analyzing conflict patterns...
    </p>
  </div>
)}
```

**Note**: This is optional. Phase 1 works without any frontend changes.

---

## API No Changes

The existing endpoints remain unchanged:

- `POST /api/post-fight/conflicts/{id}/store-transcript` - Works same as before
- `POST /api/post-fight/conflicts/{id}/generate-analysis` - Works same as before
- `POST /api/post-fight/conflicts/{id}/generate-repair-plans` - Works same as before

Enrichment happens automatically in the background task.

---

## Data Available in Backend

After Phase 1, these fields are available in the database:

```typescript
// New fields on Conflict object
{
  parent_conflict_id?: UUID;           // Links to parent conflict
  resentment_level?: number;            // 1-10
  unmet_needs?: string[];               // ['feeling_heard', 'trust', ...]
  has_past_references?: boolean;        // True if references past
  is_continuation?: boolean;            // True if continuing past issue
  conflict_chain_id?: UUID;             // Groups related conflicts
  is_resolved?: boolean;                // Resolution status
  resolved_at?: datetime;               // When resolved
}
```

And new tables:
- `trigger_phrases` - Extracted phrases
- `unmet_needs` - Core needs identified

---

## Next: Phase 2 Frontend

Phase 2 adds analytics endpoints that the frontend will consume:

- `GET /api/analytics/escalation-risk` - Risk score
- `GET /api/analytics/trigger-phrases` - Phrase analytics
- `GET /api/analytics/conflict-chains` - Related conflicts
- `GET /api/analytics/unmet-needs` - Chronic needs

Phase 2 frontend will create:
- New `/analytics` pages
- Risk score cards
- Trigger phrase tables
- Conflict timeline visualization

---

## Summary: Phase 1 Frontend

| Item | Status | Notes |
|------|--------|-------|
| UI Changes | ❌ None | Data captured in background |
| API Changes | ✅ None | Existing endpoints work |
| Data Available | ✅ Yes | Available for Phase 2+ |
| User Impact | ✅ None | Silent background processing |
| Frontend Ready | ✅ Yes | No changes needed |

---

## Checklist

- [ ] Backend Phase 1 deployed
- [ ] Enrichment running successfully
- [ ] Test conflict created and enriched
- [ ] Frontend unchanged and working normally
- [ ] Ready for Phase 2 frontend

---

## Next Phase

See `FRONTEND-PHASE-2.md` for analytics dashboard frontend work.
