# Backend Technical Debt Documentation

**Document Version**: 1.0
**Date**: December 25, 2024
**Status**: Identified - Pending Resolution

---

## Overview

This document catalogs all identified technical debt in the backend codebase for the Conflict Triggers & Escalation Analysis system.

---

## 1. Pattern Analysis Service

**File**: `backend/app/services/pattern_analysis_service.py`

### 1.1 Incomplete Implementation: Phrase Trends

**Location**: Lines 328-332

**Current State**:
```python
def _calculate_phrase_trends(self, relationship_id: str) -> List[Dict]:
    """Calculate trends in trigger phrase usage"""
    # This would query time-series data
    # For now, return empty list - can be enhanced
    return []
```

**Impact**: Feature incomplete - users don't get trend data
**Effort to Fix**: 2-3 hours
**Priority**: Medium

---

### 1.2 Missing Input Validation

**Locations**:
- Line 30: `relationship_id` not validated as UUID
- Lines 72-76: No null check before `mean()` call

**Risk**: Runtime errors with invalid input
**Effort to Fix**: 30 minutes
**Priority**: High

---

### 1.3 Repeated Datetime Parsing

**Locations**: Lines 82-86, 170-177, 213-218

**Issue**: Same datetime parsing logic repeated multiple times

**Proposed Fix**: Extract to utility function
```python
def parse_conflict_date(date_value) -> datetime:
    if isinstance(date_value, str):
        return datetime.fromisoformat(date_value.replace("Z", "+00:00"))
    return date_value
```

**Effort to Fix**: 30 minutes
**Priority**: Low (code quality)

---

## 2. Conflict Enrichment Service

**File**: `backend/app/services/conflict_enrichment_service.py`

### 2.1 No Retry Logic for LLM Calls

**Location**: Lines 65-68

**Issue**: Single attempt to call LLM, no retry on transient failures

**Proposed Fix**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def _call_llm(self, prompt: str) -> str:
    return await llm_service.analyze_with_prompt(prompt)
```

**Effort to Fix**: 30 minutes
**Priority**: Medium

---

### 2.2 Fragile JSON Parsing

**Location**: Lines 150-180

**Issue**: Uses regex to extract JSON from LLM response

**Risk**: Breaks if LLM changes response format

**Proposed Fix**: Use structured output from LLM or JSON schema validation

**Effort to Fix**: 1-2 hours
**Priority**: Medium

---

### 2.3 Sequential Database Saves

**Location**: Lines 200-225

**Issue**: Saves trigger phrases one at a time (N queries)

**Proposed Fix**: Batch insert
```python
def save_trigger_phrases_batch(self, phrases: List[dict]):
    query = """
        INSERT INTO trigger_phrases (...)
        VALUES %s
    """
    execute_values(cursor, query, phrases)
```

**Effort to Fix**: 1 hour
**Priority**: Medium (performance)

---

## 3. Database Service

**File**: `backend/app/services/db_service.py`

### 3.1 Print Statements Instead of Logging

**Locations**: Lines 95, 98, 137, 187, 203, 217, 715-717, 734-735 (and more)

**Issue**: Using `print()` instead of proper logging

**Impact**: No log aggregation, no log levels, poor debugging in production

**Effort to Fix**: 1 hour
**Priority**: Medium

---

### 3.2 Potential SQL Injection

**Location**: Lines 349-350 (if exists)

**Issue**: Dynamic query building with string formatting

**Risk**: CRITICAL security vulnerability

**Effort to Fix**: 1-2 hours
**Priority**: CRITICAL

---

### 3.3 Missing Connection Cleanup

**Location**: Lines 920-924

**Issue**: `close()` method exists but never called

**Risk**: Connection leaks under high load

**Effort to Fix**: 30 minutes
**Priority**: High

---

### 3.4 N+1 Query Pattern

**Multiple Locations**

**Issue**: Separate queries for related data instead of JOINs

**Example**:
```python
# Current: Multiple queries
conflicts = get_conflicts(relationship_id)
for c in conflicts:
    phrases = get_phrases(c['id'])  # N queries!
```

**Proposed Fix**: Use SQL JOINs with JSON aggregation

**Effort to Fix**: 2-3 hours
**Priority**: High (performance)

---

### 3.5 Missing Database Indexes

**Tables Affected**: conflicts, trigger_phrases, unmet_needs

**Missing Indexes**:
```sql
CREATE INDEX idx_conflicts_relationship_started
  ON conflicts(relationship_id, started_at DESC);

CREATE INDEX idx_trigger_phrases_relationship
  ON trigger_phrases(relationship_id);

CREATE INDEX idx_unmet_needs_relationship
  ON unmet_needs(relationship_id);

CREATE INDEX idx_conflicts_parent
  ON conflicts(parent_conflict_id)
  WHERE parent_conflict_id IS NOT NULL;
```

**Effort to Fix**: 30 minutes
**Priority**: High

---

## 4. Analytics Routes

**File**: `backend/app/routes/analytics.py`

### 4.1 Sequential Async Calls

**Location**: Lines 129-136

**Issue**: Dashboard endpoint calls 4 async methods sequentially

**Proposed Fix**:
```python
risk_report, phrases, chains, needs = await asyncio.gather(
    pattern_analysis_service.calculate_escalation_risk(relationship_id),
    pattern_analysis_service.find_trigger_phrase_patterns(relationship_id),
    pattern_analysis_service.identify_conflict_chains(relationship_id),
    pattern_analysis_service.track_chronic_needs(relationship_id),
)
```

**Effort to Fix**: 30 minutes
**Priority**: High (performance)

---

### 4.2 No Caching

**All Endpoints**

**Issue**: Expensive calculations repeated on every request

**Proposed Fix**: Add Redis caching with appropriate TTLs

**Effort to Fix**: 2-3 hours
**Priority**: High (performance)

---

### 4.3 No Rate Limiting

**All Endpoints**

**Issue**: No protection against abuse

**Proposed Fix**: Add rate limiting middleware

**Effort to Fix**: 1 hour
**Priority**: Medium

---

## 5. Mediator Context Routes

**File**: `backend/app/routes/mediator_context.py`

### 5.1 Hardcoded Empty Chains

**Location**: Line 84

**Code**: `"active_chains": []`

**Issue**: Always returns empty array

**Effort to Fix**: 30 minutes
**Priority**: Low

---

### 5.2 Fragile String Matching

**Location**: Line 141

**Code**: `if need in response.lower()`

**Issue**: Simple substring matching, prone to false positives

**Proposed Fix**: Use NLP-based matching or exact phrase matching

**Effort to Fix**: 1-2 hours
**Priority**: Low

---

## 6. Luna Agent

**File**: `backend/app/agents/luna/agent.py`

### 6.1 No Partner Name Validation

**Location**: Lines 52-53, 105-106

**Issue**: Partner names could be empty or contain injection

**Proposed Fix**: Validate and sanitize partner names

**Effort to Fix**: 30 minutes
**Priority**: Medium

---

### 6.2 Silent Context Failures

**Location**: Lines 234-245

**Issue**: If context fetch fails, agent created without context (no error to user)

**Risk**: Degraded experience without user awareness

**Effort to Fix**: 30 minutes
**Priority**: Low

---

## Summary Table

| ID | Issue | File | Priority | Effort | Status |
|----|-------|------|----------|--------|--------|
| 1.1 | Incomplete phrase trends | pattern_analysis_service.py | Medium | 2-3h | Pending |
| 1.2 | Missing input validation | pattern_analysis_service.py | High | 30m | Pending |
| 1.3 | Repeated datetime parsing | pattern_analysis_service.py | Low | 30m | Pending |
| 2.1 | No LLM retry logic | conflict_enrichment_service.py | Medium | 30m | Pending |
| 2.2 | Fragile JSON parsing | conflict_enrichment_service.py | Medium | 1-2h | Pending |
| 2.3 | Sequential DB saves | conflict_enrichment_service.py | Medium | 1h | Pending |
| 3.1 | Print vs logging | db_service.py | Medium | 1h | Pending |
| 3.2 | SQL injection risk | db_service.py | CRITICAL | 1-2h | Pending |
| 3.3 | Connection cleanup | db_service.py | High | 30m | Pending |
| 3.4 | N+1 queries | db_service.py | High | 2-3h | Pending |
| 3.5 | Missing indexes | Database | High | 30m | Pending |
| 4.1 | Sequential async calls | analytics.py | High | 30m | Pending |
| 4.2 | No caching | analytics.py | High | 2-3h | Pending |
| 4.3 | No rate limiting | analytics.py | Medium | 1h | Pending |
| 5.1 | Hardcoded empty chains | mediator_context.py | Low | 30m | Pending |
| 5.2 | Fragile string matching | mediator_context.py | Low | 1-2h | Pending |
| 6.1 | No name validation | agent.py | Medium | 30m | Pending |
| 6.2 | Silent context failures | agent.py | Low | 30m | Pending |

---

## Estimated Total Effort

| Priority | Count | Total Effort |
|----------|-------|--------------|
| CRITICAL | 1 | 1-2 hours |
| High | 7 | 9-12 hours |
| Medium | 7 | 7-11 hours |
| Low | 4 | 2-4 hours |
| **Total** | **19** | **19-29 hours** |

---

*This document should be updated as issues are resolved.*
