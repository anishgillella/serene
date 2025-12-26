# Frontend Integration - Phase 4: Dashboard Visualizations

**Phase**: 4 - Dashboard & User Insights
**Timeline**: 2-3 weeks
**Priority**: High (peak user value)
**User Impact**: Couples see their patterns and relationship health

---

## Overview

Phase 4 creates a comprehensive dashboard showing couples their conflict patterns, triggers, and health metrics. This is the most visible phase for users.

---

## Main Dashboard Layout

**File**: `src/pages/Analytics/Dashboard.tsx`

```tsx
import { useState, useEffect } from 'react';
import { HealthScore } from '../components/dashboard/HealthScore';
import { RiskMetrics } from '../components/dashboard/RiskMetrics';
import { InsightsPanel } from '../components/dashboard/InsightsPanel';
import { RecommendationsPanel } from '../components/dashboard/RecommendationsPanel';

export const Dashboard: React.FC = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch('/api/analytics/health-score'),
      fetch('/api/analytics/escalation-risk'),
      fetch('/api/analytics/dashboard')
    ])
      .then(async (responses) => {
        const [health, risk, dashboard] = await Promise.all(
          responses.map(r => r.json())
        );
        setData({ health, risk, dashboard });
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div>Loading dashboard...</div>;

  return (
    <div className="space-y-8 p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold mb-2">Your Relationship Health</h1>
        <p className="text-gray-600">
          Understanding your patterns and working toward stronger connection
        </p>
      </div>

      {/* Top Row: Health Score & Risk */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <HealthScore score={data.health} />

        <RiskMetrics risk={data.risk} />

        <InsightsPanel insights={data.dashboard.insights} />
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Metrics & Trends */}
        <div className="lg:col-span-2 space-y-6">
          <MetricsOverview data={data.dashboard.metrics} />
          <ConflictTrends data={data.dashboard.trends} />
          <TriggerPhraseHeatmap data={data.dashboard.triggers} />
        </div>

        {/* Right: Recommendations */}
        <div>
          <RecommendationsPanel recommendations={data.risk.recommendations} />
        </div>
      </div>

      {/* Bottom: Detailed Analysis */}
      <UnmetNeedsAnalysis needs={data.dashboard.chronic_needs} />
    </div>
  );
};
```

---

## Dashboard Components

### 1. Health Score Card

**File**: `src/components/dashboard/HealthScore.tsx`

```tsx
interface Props {
  score: {
    value: number;        // 0-100
    trend: 'up' | 'down' | 'stable';
    breakdownFactors: {
      unresolved_issues: number;
      conflict_frequency: number;
      escalation_risk: number;
      resentment_level: number;
    };
  };
}

export const HealthScore: React.FC<Props> = ({ score }) => {
  const getColor = (value: number) => {
    if (value >= 80) return 'text-green-600';
    if (value >= 60) return 'text-blue-600';
    if (value >= 40) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getTrendIcon = () => {
    switch (score.trend) {
      case 'up': return '📈';
      case 'down': return '📉';
      default: return '➡️';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-8">
      <h2 className="text-lg font-bold text-gray-800 mb-6">Relationship Health</h2>

      {/* Main Score */}
      <div className="mb-8">
        <div className="flex items-end gap-4">
          <div className={`text-6xl font-bold ${getColor(score.value)}`}>
            {score.value}
          </div>
          <div className="text-4xl mb-2">{getTrendIcon()}</div>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3 mt-4 overflow-hidden">
          <div
            className={`h-full transition-all ${
              score.value >= 80
                ? 'bg-green-500'
                : score.value >= 60
                ? 'bg-blue-500'
                : score.value >= 40
                ? 'bg-yellow-500'
                : 'bg-red-500'
            }`}
            style={{ width: `${score.value}%` }}
          />
        </div>
      </div>

      {/* Breakdown */}
      <div className="space-y-3 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">Unresolved issues:</span>
          <span className="font-bold">{score.breakdownFactors.unresolved_issues}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Conflict frequency:</span>
          <span className="font-bold">{score.breakdownFactors.conflict_frequency}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Escalation risk:</span>
          <span className="font-bold">
            {(score.breakdownFactors.escalation_risk * 100).toFixed(0)}%
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Avg resentment:</span>
          <span className="font-bold">
            {score.breakdownFactors.resentment_level.toFixed(1)}/10
          </span>
        </div>
      </div>
    </div>
  );
};
```

### 2. Risk Metrics Cards

**File**: `src/components/dashboard/RiskMetrics.tsx`

```tsx
interface Props {
  risk: {
    score: number;
    interpretation: string;
    unresolved_issues: number;
    days_until_predicted: number;
  };
}

export const RiskMetrics: React.FC<Props> = ({ risk }) => {
  const metrics = [
    {
      label: 'Escalation Risk',
      value: (risk.score * 100).toFixed(0) + '%',
      status: risk.interpretation,
      icon: '⚠️'
    },
    {
      label: 'Unresolved Issues',
      value: risk.unresolved_issues,
      status: risk.unresolved_issues > 2 ? 'high' : 'low',
      icon: '📋'
    },
    {
      label: 'Days to Next Conflict',
      value: risk.days_until_predicted,
      status: risk.days_until_predicted < 5 ? 'urgent' : 'stable',
      icon: '📅'
    }
  ];

  return (
    <div className="space-y-4">
      {metrics.map((metric) => (
        <div
          key={metric.label}
          className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500"
        >
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-gray-600">{metric.label}</p>
              <p className="text-3xl font-bold mt-1">{metric.value}</p>
            </div>
            <div className="text-3xl">{metric.icon}</div>
          </div>
          <p className="text-xs text-gray-500 mt-2 capitalize">
            Status: {metric.status}
          </p>
        </div>
      ))}
    </div>
  );
};
```

### 3. Conflict Trends Chart

**File**: `src/components/dashboard/ConflictTrends.tsx`

```tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

interface Props {
  data: Array<{
    week: string;
    conflicts: number;
    avg_resentment: number;
    health_score: number;
  }>;
}

export const ConflictTrends: React.FC<Props> = ({ data }) => {
  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h3 className="text-xl font-bold mb-6">30-Day Trends</h3>

      <LineChart width={600} height={300} data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="week" />
        <YAxis />
        <Tooltip />
        <Line
          type="monotone"
          dataKey="conflicts"
          stroke="#3b82f6"
          name="Conflicts"
        />
        <Line
          type="monotone"
          dataKey="avg_resentment"
          stroke="#ef4444"
          name="Avg Resentment"
        />
        <Line
          type="monotone"
          dataKey="health_score"
          stroke="#10b981"
          name="Health Score"
        />
      </LineChart>

      {/* Interpretation */}
      <div className="mt-6 space-y-2 text-sm text-gray-600">
        {data[0].conflicts > data[data.length - 1].conflicts ? (
          <p>✅ Good: Fewer conflicts this month</p>
        ) : (
          <p>⚠️ Rising: Conflicts are increasing</p>
        )}

        {data[0].avg_resentment > data[data.length - 1].avg_resentment ? (
          <p>✅ Good: Resentment is decreasing</p>
        ) : (
          <p>⚠️ Rising: Resentment is building</p>
        )}
      </div>
    </div>
  );
};
```

### 4. Trigger Phrase Heatmap

**File**: `src/components/dashboard/TriggerPhraseHeatmap.tsx`

```tsx
interface Props {
  data: {
    phrases: Array<{
      phrase: string;
      weekly_usage: number[];  // Last 4 weeks
      escalation_rate: number;
    }>;
  };
}

export const TriggerPhraseHeatmap: React.FC<Props> = ({ data }) => {
  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h3 className="text-xl font-bold mb-6">Trigger Phrase Trends</h3>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b">
              <th className="text-left p-2">Phrase</th>
              <th className="text-center p-2">Week 1</th>
              <th className="text-center p-2">Week 2</th>
              <th className="text-center p-2">Week 3</th>
              <th className="text-center p-2">Week 4</th>
              <th className="text-right p-2">Escalates</th>
            </tr>
          </thead>
          <tbody>
            {data.phrases.map((phrase) => (
              <tr key={phrase.phrase} className="border-b hover:bg-gray-50">
                <td className="p-2 font-medium">"{phrase.phrase}"</td>
                {phrase.weekly_usage.map((count, idx) => (
                  <td
                    key={idx}
                    className="text-center p-2"
                    style={{
                      backgroundColor: `rgba(239, 68, 68, ${count / 10})`
                    }}
                  >
                    {count}x
                  </td>
                ))}
                <td className="text-right p-2 font-bold">
                  {(phrase.escalation_rate * 100).toFixed(0)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 text-sm text-gray-600">
        <p>
          💡 Phrases that appear more frequently are correlated with larger
          conflicts. Focus on replacing these with healthier communication.
        </p>
      </div>
    </div>
  );
};
```

### 5. Unmet Needs Analysis

**File**: `src/components/dashboard/UnmetNeedsAnalysis.tsx`

```tsx
interface Props {
  needs: Array<{
    need: string;
    conflict_count: number;
    percentage: number;
    first_appeared: Date;
  }>;
}

export const UnmetNeedsAnalysis: React.FC<Props> = ({ needs }) => {
  const sortedNeeds = [...needs].sort((a, b) => b.percentage - a.percentage);

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h3 className="text-2xl font-bold mb-2">Your Core Unmet Needs</h3>
      <p className="text-gray-600 mb-6">
        These needs show up repeatedly in your conflicts. Addressing them will
        improve your relationship health.
      </p>

      <div className="space-y-4">
        {sortedNeeds.map((need) => (
          <div key={need.need} className="border-l-4 border-purple-500 pl-4">
            <div className="flex justify-between items-start">
              <div>
                <h4 className="font-bold text-lg capitalize">
                  {need.need.replace(/_/g, ' ')}
                </h4>
                <p className="text-sm text-gray-600">
                  Appears in {need.conflict_count} conflicts ({need.percentage}%)
                </p>
              </div>
              <div className="text-right">
                <p className="text-3xl font-bold text-purple-600">
                  {need.percentage.toFixed(0)}%
                </p>
              </div>
            </div>

            {/* Recommendation */}
            <div className="mt-3 p-3 bg-purple-50 rounded text-sm">
              {getRecommendation(need.need)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

function getRecommendation(need: string): string {
  const recommendations: Record<string, string> = {
    feeling_heard:
      'Try active listening: Repeat back what you hear before responding.',
    trust:
      'Build trust gradually through consistency and follow-through on commitments.',
    appreciation:
      'Express specific gratitude regularly for the small things.',
    respect:
      'Approach disagreements as collaborative problem-solving, not winning.',
    autonomy:
      'Give each other space to make decisions independently.',
    security:
      'Create predictability and reassurance in your routines.',
    intimacy:
      'Make time for emotional and physical connection.',
    validation:
      'Acknowledge feelings even if you disagree with actions.'
  };

  return recommendations[need] || 'Work on understanding this need better.';
}
```

### 6. Recommendations Panel

**File**: `src/components/dashboard/RecommendationsPanel.tsx`

```tsx
interface Props {
  recommendations: string[];
}

export const RecommendationsPanel: React.FC<Props> = ({ recommendations }) => {
  return (
    <div className="bg-white rounded-lg shadow-lg p-6 sticky top-6">
      <h3 className="text-xl font-bold mb-6">What to Do Now</h3>

      <div className="space-y-4">
        {recommendations.map((rec, idx) => (
          <div key={idx} className="flex gap-3 p-3 bg-blue-50 rounded">
            <span className="text-2xl">
              {['🎯', '💬', '⏰', '🤝'][idx % 4]}
            </span>
            <p className="text-sm">{rec}</p>
          </div>
        ))}
      </div>

      <button className="w-full mt-6 px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700">
        💬 Talk to Luna
      </button>
    </div>
  );
};
```

---

## New Routes

Add these routes to your router:

**File**: `src/App.tsx`

```tsx
import { Dashboard } from './pages/Analytics/Dashboard';
import { ConflictAnalysis } from './pages/Analytics/ConflictAnalysis';
import { TriggerPhrases } from './pages/Analytics/TriggerPhrases';
import { Timeline } from './pages/Analytics/Timeline';

<Routes>
  {/* Existing routes */}
  <Route path="/" element={<Home />} />
  <Route path="/fight-capture" element={<FightCapture />} />

  {/* NEW Analytics routes */}
  <Route path="/analytics" element={<Dashboard />} />
  <Route path="/analytics/conflicts" element={<ConflictAnalysis />} />
  <Route path="/analytics/triggers" element={<TriggerPhrases />} />
  <Route path="/analytics/timeline" element={<Timeline />} />
</Routes>
```

---

## Updated Navigation

**File**: `src/components/navigation/MainNav.tsx`

```tsx
<nav className="bg-white border-b">
  <div className="max-w-7xl mx-auto flex items-center justify-between p-4">
    <div className="flex gap-8">
      <Link to="/" className="font-bold">Serene</Link>

      <div className="flex gap-4">
        <Link to="/fight-capture">Record Fight</Link>
        <Link to="/history">History</Link>

        {/* NEW Analytics Section */}
        <div className="border-l pl-4">
          <Link to="/analytics" className="font-semibold text-purple-600">
            📊 Analytics
          </Link>
          <div className="text-xs text-gray-600 mt-1">
            <Link to="/analytics">Health</Link>
            <Link to="/analytics/triggers">Triggers</Link>
            <Link to="/analytics/timeline">Timeline</Link>
          </div>
        </div>
      </div>
    </div>

    <div className="flex gap-4">
      <button onClick={() => setTheme(isDark ? 'light' : 'dark')}>
        {isDark ? '☀️' : '🌙'}
      </button>
      <button onClick={() => handleLogout()}>Logout</button>
    </div>
  </nav>
);
```

---

## Analytics Service Hook

**File**: `src/hooks/useDashboardData.ts`

```typescript
export const useDashboardData = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [health, risk, dashboard] = await Promise.all([
        fetch('/api/analytics/health-score').then(r => r.json()),
        fetch('/api/analytics/escalation-risk').then(r => r.json()),
        fetch('/api/analytics/dashboard').then(r => r.json())
      ]);

      setData({ health, risk, dashboard });
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  // Refresh every 5 minutes
  useEffect(() => {
    const interval = setInterval(loadData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  return { data, loading, error, refresh: loadData };
};
```

---

## Styling

**File**: `src/styles/dashboard.css`

```css
/* Dashboard grid */
.dashboard-grid {
  @apply grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6;
}

/* Cards */
.dashboard-card {
  @apply bg-white rounded-lg shadow-lg p-6;
}

.dashboard-card-title {
  @apply text-xl font-bold mb-4;
}

/* Metric display */
.metric-large {
  @apply text-5xl font-bold;
}

.metric-small {
  @apply text-sm text-gray-600;
}

/* Status indicators */
.status-good {
  @apply text-green-600;
}

.status-warning {
  @apply text-yellow-600;
}

.status-critical {
  @apply text-red-600;
}
```

---

## Testing Checklist

- [ ] Dashboard loads all data correctly
- [ ] Health score displays accurately
- [ ] Trends show correct direction
- [ ] Trigger phrase heatmap updates
- [ ] Recommendations are actionable
- [ ] All charts render properly
- [ ] Mobile responsive design works
- [ ] Navigation works smoothly
- [ ] Data refreshes on interval
- [ ] Error handling works

---

## Summary: Phase 4 Frontend

| Item | Status |
|------|--------|
| Main dashboard page | ✅ |
| Health score component | ✅ |
| Risk metrics cards | ✅ |
| Conflict trends chart | ✅ |
| Trigger heatmap | ✅ |
| Unmet needs analysis | ✅ |
| Recommendations panel | ✅ |
| Navigation updates | ✅ |
| Responsive design | ✅ |
| Data hooks | ✅ |

---

## Next Steps

- Implement Phase 1-3 first
- Gather feedback from users on Phase 4 UI
- Consider additional visualizations (calendar correlations, cycle tracking, etc.)
- Optimize performance for large datasets
