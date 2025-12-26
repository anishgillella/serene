# Frontend Technical Debt Documentation

**Document Version**: 1.0
**Date**: December 25, 2024
**Status**: Identified - Pending Resolution

---

## Overview

This document catalogs all identified technical debt in the frontend codebase for the Conflict Triggers & Escalation Analysis system.

---

## 1. Critical Bug: Tailwind Dynamic Classes

### Affected Files
- `frontend/src/components/dashboard/HealthScore.tsx` (lines 62-63)
- `frontend/src/components/dashboard/MetricsOverview.tsx`

### Issue
Dynamic Tailwind class generation will not work with JIT compiler:

```tsx
// THIS DOES NOT WORK
className={`stop-color-from-${getHealthColor(data.value).split(' ')[1]}`}
```

Tailwind's JIT compiler only processes classes it can find as literal strings in the source code at build time.

### Fix Required
```tsx
// Create explicit class mappings
const HEALTH_COLORS = {
  excellent: {
    ring: 'stroke-green-500',
    text: 'text-green-600',
    gradient: 'from-green-400 to-green-600'
  },
  good: {
    ring: 'stroke-blue-500',
    text: 'text-blue-600',
    gradient: 'from-blue-400 to-blue-600'
  },
  fair: {
    ring: 'stroke-yellow-500',
    text: 'text-yellow-600',
    gradient: 'from-yellow-400 to-yellow-600'
  },
  poor: {
    ring: 'stroke-red-500',
    text: 'text-red-600',
    gradient: 'from-red-400 to-red-600'
  }
};
```

**Priority**: CRITICAL (Bug)
**Effort**: 30 minutes

---

## 2. Missing Request Cancellation

### Affected Files
- `frontend/src/hooks/useAnalytics.ts`
- `frontend/src/hooks/useDashboardData.ts`
- `frontend/src/hooks/useConflictContext.ts`
- `frontend/src/hooks/useLunaMediator.ts`

### Issue
No AbortController usage - requests not cancelled on component unmount

### Risk
- Memory leaks
- State updates after unmount (React warning)
- Wasted network resources

### Fix Required
```tsx
const fetchData = useCallback(async () => {
  const controller = new AbortController();

  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: { 'ngrok-skip-browser-warning': 'true' }
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    setData(data);
  } catch (err) {
    if (err.name === 'AbortError') {
      return; // Request was cancelled, ignore
    }
    setError(err.message);
  }

  // Cleanup function
  return () => controller.abort();
}, [url]);

useEffect(() => {
  const cleanup = fetchData();
  return () => cleanup?.();
}, [fetchData]);
```

**Priority**: High
**Effort**: 1 hour (all hooks)

---

## 3. Accessibility Issues

### 3.1 Missing ARIA Labels

**Affected Files**: All components

**Examples**:
```tsx
// Before: No accessibility
<button onClick={onClick}>X</button>

// After: Accessible
<button
  onClick={onClick}
  aria-label="Close panel"
  title="Close"
>
  <span className="sr-only">Close</span>
  <XIcon aria-hidden="true" />
</button>
```

---

### 3.2 Color-Only Information

**Affected Files**:
- `frontend/src/components/dashboard/HealthScore.tsx`
- `frontend/src/components/dashboard/RiskMetrics.tsx`
- `frontend/src/components/analytics/EscalationRiskCard.tsx`

**Issue**: Risk levels communicated only through color

**Fix Required**: Add text labels alongside colors
```tsx
// Before
<div className="text-red-600">{score}%</div>

// After
<div className="text-red-600">
  {score}%
  <span className="ml-2 text-sm font-medium">Critical Risk</span>
</div>
```

---

### 3.3 Progress Bars Missing ARIA

**Affected Files**:
- `frontend/src/components/analytics/TriggerPhraseTable.tsx`
- `frontend/src/components/dashboard/HealthScore.tsx`
- `frontend/src/components/dashboard/UnmetNeedsAnalysis.tsx`

**Fix Required**:
```tsx
// Before
<div className="w-full h-2 bg-gray-200">
  <div className="bg-red-500 h-2" style={{ width: '75%' }} />
</div>

// After
<div
  role="progressbar"
  aria-valuenow={75}
  aria-valuemin={0}
  aria-valuemax={100}
  aria-label="Escalation rate: 75%"
  className="w-full h-2 bg-gray-200"
>
  <div className="bg-red-500 h-2" style={{ width: '75%' }} />
</div>
```

---

### 3.4 Tables Missing Proper Markup

**Affected File**: `frontend/src/components/analytics/TriggerPhraseTable.tsx`

**Fix Required**:
```tsx
// Before
<table>
  <thead>
    <tr>
      <th>Phrase</th>
      <th>Count</th>
    </tr>
  </thead>

// After
<table>
  <caption className="sr-only">Trigger phrase analysis</caption>
  <thead>
    <tr>
      <th scope="col">Phrase</th>
      <th scope="col">Count</th>
    </tr>
  </thead>
```

**Priority**: High (Compliance)
**Effort**: 3-4 hours (all components)

---

## 4. Responsive Design Issues

### 4.1 Fixed Width Panels

**Affected File**: `frontend/src/components/MediatorContextPanel.tsx` (line 89)

**Issue**:
```tsx
// Fixed width breaks on mobile
<div className="w-80 max-h-96">
```

**Fix**:
```tsx
<div className="w-full sm:w-80 max-h-[80vh] sm:max-h-96">
```

---

### 4.2 Grid Layout Issues

**Affected File**: `frontend/src/pages/Analytics/Dashboard.tsx`

**Issue**: 3-column grid doesn't adapt properly

**Fix**:
```tsx
// Before
<div className="grid grid-cols-3 gap-6">

// After
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
```

---

### 4.3 Touch Targets

**Issue**: Buttons and interactive elements too small for mobile

**WCAG Requirement**: Minimum 44x44px touch target

**Fix**: Add padding or minimum dimensions
```tsx
<button className="min-h-[44px] min-w-[44px] p-3">
```

**Priority**: High
**Effort**: 2-3 hours

---

## 5. TypeScript Issues

### 5.1 Usage of `any` Type

**Affected Files**:
- `frontend/src/components/dashboard/ConflictTrends.tsx` (line 6)
- Multiple other components

**Current**:
```tsx
interface Props {
  data: any;  // Bad
}
```

**Fix**:
```tsx
interface ConflictMetrics {
  total_conflicts: number;
  resolved_conflicts: number;
  unresolved_conflicts: number;
  resolution_rate: number;
}

interface Props {
  data: {
    metrics: ConflictMetrics;
  };
}
```

---

### 5.2 Missing Null Checks

**Issue**: Optional properties accessed without null checks

**Example**:
```tsx
// Unsafe
{triggerPhrases.most_impactful.map(...)}

// Safe
{triggerPhrases?.most_impactful?.map(...) ?? (
  <p>No data available</p>
)}
```

**Priority**: Medium
**Effort**: 2-3 hours

---

## 6. Loading State Issues

### 6.1 Basic Loading Text

**Affected Files**:
- `frontend/src/pages/Analytics/Dashboard.tsx`
- `frontend/src/pages/Analytics/TriggerPhrases.tsx`
- `frontend/src/pages/Analytics/ConflictAnalysis.tsx`

**Current**:
```tsx
if (loading) return <div>Loading...</div>;
```

**Fix**: Create skeleton components
```tsx
// components/common/Skeleton.tsx
export const SkeletonCard = ({ className = '' }) => (
  <div className={`animate-pulse bg-gray-200 rounded-lg ${className}`} />
);

export const SkeletonText = ({ lines = 3, className = '' }) => (
  <div className={`space-y-2 ${className}`}>
    {[...Array(lines)].map((_, i) => (
      <div
        key={i}
        className={`h-4 bg-gray-200 rounded ${i === lines - 1 ? 'w-2/3' : 'w-full'}`}
      />
    ))}
  </div>
);

// Usage in Dashboard
if (loading) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <SkeletonCard className="h-48" />
      <SkeletonCard className="h-48" />
      <SkeletonCard className="h-48" />
    </div>
  );
}
```

**Priority**: High (UX)
**Effort**: 1-2 hours

---

## 7. Error Handling Issues

### 7.1 Basic Error Display

**Affected Files**: All pages

**Current**:
```tsx
if (error) return <div className="text-red-600">Error: {error}</div>;
```

**Fix**: Create error state component
```tsx
// components/common/ErrorState.tsx
interface ErrorStateProps {
  error: string;
  onRetry?: () => void;
  title?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  error,
  onRetry,
  title = 'Something went wrong'
}) => (
  <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
    <AlertTriangle className="text-red-500 mx-auto mb-4" size={48} />
    <h3 className="text-lg font-bold text-red-800 mb-2">{title}</h3>
    <p className="text-red-600 mb-4">{error}</p>
    {onRetry && (
      <button
        onClick={onRetry}
        className="bg-red-600 text-white px-6 py-2 rounded-lg hover:bg-red-700"
      >
        Try Again
      </button>
    )}
  </div>
);
```

**Priority**: Medium
**Effort**: 1 hour

---

## 8. Performance Issues

### 8.1 Missing Memoization

**Affected Files**: Various components

**Issue**: Functions and objects recreated on every render

**Fix**:
```tsx
// Before
const getHealthStatus = () => {
  if (score >= 80) return 'excellent';
  // ...
};

// After
const getHealthStatus = useCallback(() => {
  if (score >= 80) return 'excellent';
  // ...
}, [score]);

// For expensive computations
const expensiveValue = useMemo(() => {
  return calculateExpensiveValue(data);
}, [data]);
```

---

### 8.2 Index as Key Anti-pattern

**Affected File**: `frontend/src/components/analytics/TriggerPhraseTable.tsx`

**Current**:
```tsx
{phrases.map((phrase, idx) => (
  <tr key={idx}>  // Bad: using index as key
```

**Fix**:
```tsx
{phrases.map((phrase) => (
  <tr key={phrase.phrase}>  // Use unique identifier
```

**Priority**: Medium
**Effort**: 1 hour

---

## 9. Missing Empty States

### Affected Files
- All list/table components

**Issue**: No message when data is empty

**Fix**:
```tsx
{data.length === 0 ? (
  <div className="text-center py-8 text-gray-500">
    <InboxIcon className="mx-auto mb-4 h-12 w-12" />
    <p>No data available yet</p>
    <p className="text-sm">Start recording conflicts to see analytics</p>
  </div>
) : (
  <DataTable data={data} />
)}
```

**Priority**: Medium
**Effort**: 1 hour

---

## 10. Hardcoded Values

### 10.1 Relationship ID

**Affected Files**:
- `frontend/src/pages/Analytics/Dashboard.tsx` (line 14)
- `frontend/src/pages/Analytics/ConflictAnalysis.tsx`
- Other analytics pages

**Current**:
```tsx
const relationshipId = "00000000-0000-0000-0000-000000000000";
```

**Fix**: Get from context or props
```tsx
const { currentRelationship } = useRelationship();
const relationshipId = currentRelationship?.id;
```

**Priority**: Medium
**Effort**: 30 minutes

---

## Summary Table

| ID | Issue | Priority | Effort | Status |
|----|-------|----------|--------|--------|
| 1 | Tailwind dynamic classes | CRITICAL | 30m | Pending |
| 2 | Missing AbortController | High | 1h | Pending |
| 3.1 | Missing ARIA labels | High | 1h | Pending |
| 3.2 | Color-only information | High | 1h | Pending |
| 3.3 | Progress bars ARIA | High | 30m | Pending |
| 3.4 | Table accessibility | High | 30m | Pending |
| 4.1 | Fixed width panels | High | 30m | Pending |
| 4.2 | Grid layout issues | High | 30m | Pending |
| 4.3 | Touch targets | High | 1h | Pending |
| 5.1 | `any` types | Medium | 2h | Pending |
| 5.2 | Missing null checks | Medium | 1h | Pending |
| 6.1 | Loading skeletons | High | 1-2h | Pending |
| 7.1 | Error recovery UI | Medium | 1h | Pending |
| 8.1 | Missing memoization | Medium | 1h | Pending |
| 8.2 | Index as key | Medium | 30m | Pending |
| 9 | Empty states | Medium | 1h | Pending |
| 10.1 | Hardcoded relationship ID | Medium | 30m | Pending |

---

## Estimated Total Effort

| Priority | Count | Total Effort |
|----------|-------|--------------|
| CRITICAL | 1 | 30 minutes |
| High | 9 | 7-8 hours |
| Medium | 7 | 7-8 hours |
| **Total** | **17** | **14-16 hours** |

---

## Component-by-Component Checklist

### Dashboard Components
- [ ] HealthScore.tsx - Fix Tailwind, add ARIA
- [ ] RiskMetrics.tsx - Add ARIA, responsive
- [ ] MetricsOverview.tsx - Fix Tailwind
- [ ] ConflictTrends.tsx - Add types, ARIA
- [ ] TriggerPhraseHeatmap.tsx - Add ARIA
- [ ] UnmetNeedsAnalysis.tsx - Add ARIA
- [ ] RecommendationsPanel.tsx - Add empty state
- [ ] InsightsPanel.tsx - Responsive

### Analytics Components
- [ ] EscalationRiskCard.tsx - Color + text labels
- [ ] TriggerPhraseTable.tsx - Table accessibility, key fix
- [ ] UnresolvedIssuesList.tsx - Empty state
- [ ] ChronicNeedsList.tsx - Add ARIA

### Pages
- [ ] Dashboard.tsx - Skeleton, responsive, error UI
- [ ] ConflictAnalysis.tsx - Loading, error
- [ ] TriggerPhrases.tsx - Loading, error
- [ ] Timeline.tsx - Loading, error

### Hooks
- [ ] useAnalytics.ts - AbortController
- [ ] useDashboardData.ts - AbortController
- [ ] useConflictContext.ts - AbortController
- [ ] useLunaMediator.ts - AbortController

### New Components to Create
- [ ] components/common/Skeleton.tsx
- [ ] components/common/ErrorState.tsx
- [ ] components/common/EmptyState.tsx

---

*This document should be updated as issues are resolved.*
