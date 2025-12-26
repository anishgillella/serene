# Frontend Integration - Phase 2: Analytics & Pattern Detection

**Phase**: 2 - Intelligence & Pattern Detection
**Timeline**: 2-3 weeks
**Priority**: High (delivers user value)
**User Impact**: New analytics pages and metrics

---

## Overview

Phase 2 adds analytics endpoints to the backend. The frontend creates new pages and components to visualize this data.

---

## New Routes to Create

### 1. `/analytics/conflicts` - Main Dashboard

**File**: `src/pages/Analytics/ConflictAnalysis.tsx`

Shows:
- Escalation risk score (large, prominent)
- Unresolved issues list
- Chronic unmet needs
- Next steps recommendations

```tsx
import { useState, useEffect } from 'react';
import { EscalationRiskCard } from '../components/analytics/EscalationRiskCard';
import { UnresolvedIssuesList } from '../components/analytics/UnresolvedIssuesList';
import { ChronicNeedsList } from '../components/analytics/ChronicNeedsList';

export const ConflictAnalysis: React.FC = () => {
  const [riskData, setRiskData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalyticsData();
  }, []);

  const fetchAnalyticsData = async () => {
    try {
      const response = await fetch('/api/analytics/escalation-risk');
      const data = await response.json();
      setRiskData(data);
    } catch (error) {
      console.error('Failed to load analytics', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading analytics...</div>;

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-3xl font-bold">Relationship Health & Patterns</h1>

      {/* Risk Score */}
      <EscalationRiskCard data={riskData} />

      {/* Unresolved Issues */}
      <UnresolvedIssuesList issues={riskData.unresolved_issues} />

      {/* Chronic Needs */}
      <ChronicNeedsList needs={riskData.chronic_needs} />

      {/* Recommendations */}
      <div className="bg-blue-50 p-6 rounded-lg">
        <h2 className="font-bold mb-4">Recommended Actions</h2>
        <ul className="space-y-2">
          {riskData.recommendations.map((rec: string) => (
            <li key={rec} className="flex items-start">
              <span className="mr-3">→</span>
              <span>{rec}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};
```

### 2. `/analytics/triggers` - Trigger Phrase Analysis

**File**: `src/pages/Analytics/TriggerPhrases.tsx`

Shows:
- Most impactful trigger phrases
- Usage frequency trends
- Speaker-specific patterns
- Category breakdown

```tsx
import { TriggerPhraseTable } from '../components/analytics/TriggerPhraseTable';
import { TriggerPhraseHeatmap } from '../components/analytics/TriggerPhraseHeatmap';
import { CategoryBreakdown } from '../components/analytics/CategoryBreakdown';

export const TriggerPhrases: React.FC = () => {
  const [phrases, setPhrases] = useState([]);

  useEffect(() => {
    const response = await fetch('/api/analytics/trigger-phrases');
    const data = await response.json();
    setPhrases(data.most_impactful);
  }, []);

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-3xl font-bold">Trigger Phrase Analysis</h1>

      <div className="grid grid-cols-2 gap-6">
        <div>
          <h2 className="font-bold mb-4">Most Impactful Phrases</h2>
          <TriggerPhraseTable phrases={phrases} />
        </div>

        <div>
          <h2 className="font-bold mb-4">Category Breakdown</h2>
          <CategoryBreakdown phrases={phrases} />
        </div>
      </div>

      <div>
        <h2 className="font-bold mb-4">Frequency Trend (Last 30 Days)</h2>
        <TriggerPhraseHeatmap />
      </div>
    </div>
  );
};
```

### 3. `/analytics/timeline` - Conflict Timeline

**File**: `src/pages/Analytics/Timeline.tsx`

Shows:
- Vertical timeline of conflicts
- Conflict chains visualization
- Related conflicts connected
- Resolution status indicators

```tsx
import { ConflictTimeline } from '../components/analytics/ConflictTimeline';
import { ConflictChains } from '../components/analytics/ConflictChains';

export const Timeline: React.FC = () => {
  const [conflicts, setConflicts] = useState([]);
  const [chains, setChains] = useState([]);

  useEffect(() => {
    Promise.all([
      fetch('/api/conflicts?sort=started_at&order=desc'),
      fetch('/api/analytics/conflict-chains')
    ]).then(([r1, r2]) => {
      setConflicts(r1.json());
      setChains(r2.json());
    });
  }, []);

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-3xl font-bold">Conflict Timeline</h1>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <h2 className="font-bold mb-4">Chronological View</h2>
          <ConflictTimeline conflicts={conflicts} />
        </div>

        <div>
          <h2 className="font-bold mb-4">Conflict Chains</h2>
          <ConflictChains chains={chains} />
        </div>
      </div>
    </div>
  );
};
```

---

## New Components to Create

### Component 1: EscalationRiskCard

**File**: `src/components/analytics/EscalationRiskCard.tsx`

```tsx
interface Props {
  data: {
    risk_score: number;
    interpretation: string;
    unresolved_issues: number;
    days_until_predicted_conflict: number;
  };
}

export const EscalationRiskCard: React.FC<Props> = ({ data }) => {
  const getColor = (score: number) => {
    if (score < 0.25) return 'text-green-600';
    if (score < 0.50) return 'text-yellow-600';
    if (score < 0.75) return 'text-orange-600';
    return 'text-red-600';
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-8">
      <h2 className="text-2xl font-bold mb-6">Escalation Risk</h2>

      <div className="flex items-center justify-between mb-6">
        <div>
          <div className={`text-6xl font-bold ${getColor(data.risk_score)}`}>
            {(data.risk_score * 100).toFixed(0)}%
          </div>
          <p className="text-2xl text-gray-600 mt-2 capitalize">
            {data.interpretation}
          </p>
        </div>

        <div className="text-right">
          <p className="text-gray-600">Next conflict likely in</p>
          <p className="text-4xl font-bold text-gray-800">
            {data.days_until_predicted_conflict} days
          </p>
        </div>
      </div>

      <div className="bg-blue-50 p-4 rounded">
        <p className="text-sm text-blue-800">
          You have <strong>{data.unresolved_issues}</strong> unresolved issues.
          Address them to reduce escalation risk.
        </p>
      </div>
    </div>
  );
};
```

### Component 2: TriggerPhraseTable

**File**: `src/components/analytics/TriggerPhraseTable.tsx`

```tsx
interface Props {
  phrases: Array<{
    phrase: string;
    speaker: string;
    usage_count: number;
    avg_emotional_intensity: number;
    escalation_rate: number;
  }>;
}

export const TriggerPhraseTable: React.FC<Props> = ({ phrases }) => {
  return (
    <table className="w-full border-collapse">
      <thead>
        <tr className="border-b">
          <th className="text-left p-2">Phrase</th>
          <th className="text-center p-2">Used</th>
          <th className="text-center p-2">Intensity</th>
          <th className="text-center p-2">Escalates</th>
        </tr>
      </thead>
      <tbody>
        {phrases.map((phrase) => (
          <tr key={phrase.phrase} className="border-b hover:bg-gray-50">
            <td className="p-2">"{phrase.phrase}"</td>
            <td className="text-center p-2">{phrase.usage_count}x</td>
            <td className="text-center p-2">
              <div className="w-24 bg-gray-200 rounded h-2">
                <div
                  className="bg-red-500 h-2 rounded"
                  style={{
                    width: `${(phrase.avg_emotional_intensity / 10) * 100}%`
                  }}
                />
              </div>
            </td>
            <td className="text-center p-2">
              {(phrase.escalation_rate * 100).toFixed(0)}%
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};
```

### Component 3: ConflictTimeline

**File**: `src/components/analytics/ConflictTimeline.tsx`

```tsx
export const ConflictTimeline: React.FC<Props> = ({ conflicts }) => {
  return (
    <div className="space-y-4">
      {conflicts.map((conflict, idx) => (
        <div key={conflict.id} className="flex gap-4">
          {/* Timeline line */}
          <div className="flex flex-col items-center">
            <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
            {idx < conflicts.length - 1 && (
              <div className="w-0.5 h-16 bg-gray-300"></div>
            )}
          </div>

          {/* Conflict card */}
          <div className="flex-1 bg-white p-4 rounded border">
            <p className="font-bold">{conflict.metadata?.topic || 'Conflict'}</p>
            <p className="text-sm text-gray-600">
              {new Date(conflict.started_at).toLocaleDateString()}
            </p>
            {conflict.resentment_level && (
              <p className="text-sm mt-2">
                Resentment: <strong>{conflict.resentment_level}/10</strong>
              </p>
            )}
            {conflict.is_resolved && (
              <span className="inline-block mt-2 px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                ✓ Resolved
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
```

---

## Navigation Updates

Add to main navigation:

**File**: `src/components/navigation/SidebarNav.tsx` or `src/App.tsx`

```tsx
<nav>
  {/* Existing links */}
  <Link to="/">Dashboard</Link>
  <Link to="/fight-capture">Fight Capture</Link>
  <Link to="/history">History</Link>

  {/* NEW Phase 2 links */}
  <div className="border-t my-4 pt-4">
    <h3 className="text-sm font-bold text-gray-600 mb-2">ANALYTICS</h3>
    <Link to="/analytics/conflicts">Conflict Analysis</Link>
    <Link to="/analytics/triggers">Trigger Phrases</Link>
    <Link to="/analytics/timeline">Timeline</Link>
  </div>
</nav>
```

---

## API Integration

### New Endpoints Used

```typescript
// Get escalation risk
GET /api/analytics/escalation-risk
→ {
  risk_score: 0.72,
  interpretation: 'high',
  unresolved_issues: 3,
  days_until_predicted_conflict: 4,
  recommendations: [...]
}

// Get trigger phrases
GET /api/analytics/trigger-phrases
→ {
  most_impactful: [
    {
      phrase: "You didn't do that yesterday",
      category: "temporal_reference",
      usage_count: 8,
      avg_emotional_intensity: 8.2,
      escalation_rate: 0.75
    }
  ]
}

// Get conflict chains
GET /api/analytics/conflict-chains
→ {
  chains: [
    {
      root_cause: "Communication breakdown",
      conflicts_in_chain: 4,
      unmet_needs: ["feeling_heard", "trust"]
    }
  ]
}

// Get unmet needs
GET /api/analytics/unmet-needs
→ {
  chronic_needs: [
    {
      need: "feeling_heard",
      conflict_count: 7,
      appears_in_percentage: 71
    }
  ]
}
```

---

## TypeScript Types to Add

**File**: `src/types/analytics.ts` (NEW)

```typescript
export interface EscalationRisk {
  risk_score: number;           // 0.0-1.0
  interpretation: 'low' | 'medium' | 'high' | 'critical';
  unresolved_issues: number;
  days_until_predicted_conflict: number;
  factors: Record<string, number>;
  recommendations: string[];
}

export interface TriggerPhrase {
  phrase: string;
  phrase_category: string;
  usage_count: number;
  avg_emotional_intensity: number;
  escalation_rate: number;
  speaker?: string;
}

export interface ConflictChain {
  root_cause: string;
  conflicts_in_chain: number;
  timeline: string;
  unmet_needs: string[];
  resolution_attempts: number;
}

export interface UnmetNeed {
  need: string;
  conflict_count: number;
  first_appeared: Date;
  days_appeared_in: number;
  is_chronic: boolean;
  percentage_of_conflicts: number;
}
```

---

## Styling with Tailwind

Add to `src/index.css`:

```css
/* Analytics cards */
.analytics-card {
  @apply bg-white rounded-lg shadow-md p-6;
}

.analytics-card-title {
  @apply text-2xl font-bold mb-4;
}

/* Risk score colors */
.risk-low { @apply text-green-600; }
.risk-medium { @apply text-yellow-600; }
.risk-high { @apply text-orange-600; }
.risk-critical { @apply text-red-600; }

/* Timeline styling */
.timeline-node {
  @apply w-3 h-3 rounded-full bg-blue-500;
}

.timeline-line {
  @apply w-0.5 bg-gray-300;
}
```

---

## Testing Checklist

- [ ] Analytics routes load without errors
- [ ] Risk score displays correctly
- [ ] Trigger phrase table shows real data
- [ ] Timeline displays conflicts chronologically
- [ ] API calls succeed and return expected data
- [ ] Responsive design works on mobile
- [ ] Navigation links work correctly
- [ ] Loading states display properly
- [ ] Error states handled gracefully

---

## Summary: Phase 2 Frontend

| Item | Required | Optional |
|------|----------|----------|
| 3 new routes | ✅ | - |
| 5+ new components | ✅ | - |
| Navigation updates | ✅ | - |
| TypeScript types | ✅ | - |
| API integration | ✅ | - |
| Styling | ✅ | - |

---

## Next Phase

See `FRONTEND-PHASE-3.md` for Luna context awareness integration.
