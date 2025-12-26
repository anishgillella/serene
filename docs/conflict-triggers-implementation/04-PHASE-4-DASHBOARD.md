# Phase 4: Dashboard Visualization - Insights & Analytics

**Goal**: Show couples the conflict patterns and escalation risks in intuitive visualizations

**Timeline**: 2-3 weeks

**Deliverables**:
- New dashboard pages and components
- Data visualization components
- Real-time metrics displays
- Actionable insights UI

**Depends On**: Phase 1 (Data) + Phase 2 (Analytics) + Phase 3 (Luna)

---

## 4.1 Dashboard Pages & Layouts

### Page 1: Conflict Overview & Risk Assessment

**URL**: `/analytics/conflicts`

**Components**:
1. **Escalation Risk Card** (top)
   - Large risk score (0.0-1.0) with color coding
   - Status: Low / Medium / High / Critical
   - Key factors contributing to risk
   - Days until predicted next conflict
   - CTA: "Start Mediation with Luna"

2. **Unresolved Issues Summary**
   - Card list showing each unresolved conflict
   - Days unresolved
   - Resentment level indicator
   - Unmet needs tags
   - CTA: "Resolve with Luna"

3. **Chronic Unmet Needs Panel**
   - List of needs appearing in 3+ conflicts
   - Percentage of conflicts where it appears
   - Visual bar chart
   - Link to specific conflicts
   - Insight: "Feeling heard appears in 71% of your conflicts. This is the core issue."

4. **Next Steps Recommendations**
   - Generated based on current state
   - Prioritized recommendations
   - Estimated impact if addressed

**Design Notes**:
- Color scheme: Green (low risk) → Yellow (medium) → Orange (high) → Red (critical)
- Cards are clickable to dive deeper
- Real-time data (refreshes every 5 mins during active session)

---

### Page 2: Trigger Phrase Analysis

**URL**: `/analytics/triggers`

**Components**:

1. **Most Impactful Phrases Ranking**
   - Table showing:
     - Phrase text
     - Who uses it (Partner A / B)
     - Times used
     - Avg emotional intensity (1-10 scale)
     - Escalation rate (%)
     - Category tag (temporal_reference, passive_aggressive, etc.)
   - Sort by: escalation rate, frequency, intensity
   - Hover tooltips show context

2. **Trigger Phrase Heat Map**
   - Y-axis: Different phrases
   - X-axis: Time (weeks/months)
   - Color intensity: Frequency of use
   - Shows trends (is "You never listen" being used more?)

3. **Speaker-Specific Patterns**
   - Two columns: Partner A vs Partner B
   - Their most-used trigger phrases
   - Comparison of emotional intensity
   - Insight: "You tend to bring up the past when you're stressed"

4. **Phrase Category Distribution**
   - Pie/donut chart showing breakdown:
     - Temporal references (past conflicts)
     - Passive-aggressive statements
     - Blame statements
     - Dismissals
     - Threats

5. **Trigger Learning Center**
   - When you hover on a trigger phrase:
     - Definition of the category
     - Why this escalates conflicts
     - What might be underneath the phrase
     - How to respond differently
   - Example: "Temporal Reference: Bringing up past failures. Underneath: 'I don't believe you'll change'"

---

### Page 3: Conflict Timeline & Chains

**URL**: `/analytics/conflicts/timeline`

**Components**:

1. **Vertical Timeline**
   - Each conflict as a node
   - Showing:
     - Date & main topic
     - Resentment level (visual indicator)
     - Whether it was resolved (checkmark or X)
   - Lines connecting related conflicts (parent → child)
   - Hovering shows: unmet needs, key trigger phrases, status

2. **Conflict Chain View**
   - Groups related conflicts together
   - Shows progression:
     ```
     Root Cause: "Communication breakdown" (Nov 15)
       ↓
     Escalation 1: "Trust issue surfaces" (Nov 22)
       ↓
     Escalation 2: "Door argument" (Dec 1)
       ↓
     Critical: "Big fight" (Dec 10)
     ```
   - Insight below each chain: "This chain never fully resolved. It's built 4 conflicts."
   - CTA: "Work on the root cause"

3. **Days Between Conflicts Chart**
   - Line chart showing days between consecutive conflicts
   - Downward trend = accelerating recurrence
   - Annotation: "Conflicts are happening every 3.5 days (down from 7 days 2 months ago)"
   - Risk indicator: If trend is accelerating, highlight in red

4. **Resolution Rate Tracker**
   - Percentage of conflicts that were fully resolved
   - Comparison to previous month
   - Details on which conflicts remain unresolved

---

### Page 4: Health Dashboard

**URL**: `/analytics/health`

**Components**:

1. **Relationship Health Score** (top, prominent)
   - Scale: 0-100
   - Visual gauge/circular indicator
   - Breakdown of score by factors:
     - Unresolved issues (40% weight)
     - Conflict frequency (30% weight)
     - Escalation risk (20% weight)
     - Resentment level (10% weight)

2. **Key Metrics Cards**
   - Total conflicts this month
   - Avg resentment level
   - Unresolved issues count
   - Days since last conflict
   - Escalation risk score

3. **Historical Trends**
   - 4 sparklines showing 30-day trends:
     - Conflict frequency (down/stable/up)
     - Avg resentment (down/stable/up)
     - Health score (down/stable/up)
     - Resolution rate (down/stable/up)

4. **Actionable Insights Panel**
   - Bulleted list of key insights
   - Generated dynamically based on current data
   - Examples:
     - "Your health score dropped 12 points this month due to 3 unresolved issues"
     - "Conflicts are accelerating (7 days apart → 3.5 days apart)"
     - "The #1 unmet need is 'feeling heard' (appears in 71% of conflicts)"
     - "Your top trigger phrase is 'You never listen' (escalates 85% of the time)"

5. **Recommendations Section**
   - Prioritized list of actions
   - Each with estimated impact
   - Example: "Resolve the Dec 1 conflict about chores. Impact: -15 escalation risk"

---

## 4.2 Component Designs

### Component: Risk Score Card

```tsx
interface RiskScoreCardProps {
  riskScore: number;        // 0.0 - 1.0
  interpretation: string;   // 'low' | 'medium' | 'high' | 'critical'
  daysUntilNextConflict: number;
  recommendations: string[];
}

export const RiskScoreCard: React.FC<RiskScoreCardProps> = ({
  riskScore,
  interpretation,
  daysUntilNextConflict,
  recommendations
}) => {
  const getColor = (score: number) => {
    if (score < 0.25) return 'bg-green-500';
    if (score < 0.50) return 'bg-yellow-500';
    if (score < 0.75) return 'bg-orange-500';
    return 'bg-red-500';
  };

  return (
    <div className="risk-score-card">
      <h3>Escalation Risk</h3>

      <div className={`score-circle ${getColor(riskScore)}`}>
        <span className="score-number">{(riskScore * 100).toFixed(0)}%</span>
        <span className="score-label">{interpretation}</span>
      </div>

      <div className="prediction">
        <p>Next conflict likely in <strong>{daysUntilNextConflict} days</strong></p>
      </div>

      <div className="recommendations">
        <h4>What to do now:</h4>
        <ul>
          {recommendations.map(rec => <li key={rec}>{rec}</li>)}
        </ul>
      </div>

      <button className="primary">Start Mediation with Luna</button>
    </div>
  );
};
```

### Component: Trigger Phrase Table

```tsx
interface TriggerPhrase {
  phrase: string;
  speaker: 'partner_a' | 'partner_b';
  usageCount: number;
  avgIntensity: number;
  escalationRate: number;
  category: string;
}

interface TriggerTableProps {
  phrases: TriggerPhrase[];
  onPhraseCLick: (phrase: TriggerPhrase) => void;
}

export const TriggerPhraseTable: React.FC<TriggerTableProps> = ({
  phrases,
  onPhraseClick
}) => {
  return (
    <table className="trigger-table">
      <thead>
        <tr>
          <th>Phrase</th>
          <th>Speaker</th>
          <th>Used</th>
          <th>Intensity</th>
          <th>Escalation %</th>
          <th>Category</th>
        </tr>
      </thead>
      <tbody>
        {phrases.map(phrase => (
          <tr
            key={phrase.phrase}
            onClick={() => onPhraseClick(phrase)}
            className="hover:bg-gray-100 cursor-pointer"
          >
            <td className="font-medium">"{phrase.phrase}"</td>
            <td>{phrase.speaker === 'partner_a' ? '👤 A' : '👥 B'}</td>
            <td className="text-center">{phrase.usageCount}</td>
            <td>
              <div className="intensity-bar">
                <div
                  style={{
                    width: `${(phrase.avgIntensity / 10) * 100}%`,
                    backgroundColor: `hsl(0, 100%, ${100 - phrase.avgIntensity * 5}%)`
                  }}
                />
              </div>
              <span>{phrase.avgIntensity.toFixed(1)}/10</span>
            </td>
            <td>
              <span className={`escalation-badge ${phrase.escalationRate > 0.7 ? 'high' : 'medium'}`}>
                {(phrase.escalationRate * 100).toFixed(0)}%
              </span>
            </td>
            <td>
              <span className="category-tag">{phrase.category}</span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};
```

### Component: Conflict Timeline Chain

```tsx
interface ConflictChainProps {
  conflicts: ConflictWithContext[];
  rootCause: string;
  chainInsight: string;
}

export const ConflictChain: React.FC<ConflictChainProps> = ({
  conflicts,
  rootCause,
  chainInsight
}) => {
  return (
    <div className="conflict-chain">
      <div className="chain-header">
        <h4>Conflict Chain</h4>
        <span className="count">{conflicts.length} connected conflicts</span>
      </div>

      <div className="chain-nodes">
        {conflicts.map((conflict, idx) => (
          <div key={conflict.id} className="chain-node">
            <div className={`node-badge ${conflict.isResolved ? 'resolved' : 'unresolved'}`}>
              {idx === 0 && '🔴 Root'}
              {idx > 0 && idx < conflicts.length - 1 && '🟡 Escalation'}
              {idx === conflicts.length - 1 && '🔴 Current'}
            </div>

            <div className="node-content">
              <p className="date">{formatDate(conflict.createdAt)}</p>
              <p className="topic">{conflict.topic}</p>
              <p className="needs">
                Unmet: {conflict.unmetNeeds.join(', ')}
              </p>
            </div>

            {idx < conflicts.length - 1 && <div className="chain-arrow">↓</div>}
          </div>
        ))}
      </div>

      <div className="chain-insight">
        <p><strong>Pattern:</strong> {chainInsight}</p>
        <button className="secondary">Resolve Root Cause with Luna</button>
      </div>
    </div>
  );
};
```

---

## 4.3 API Integration

### Frontend Endpoints Used

```javascript
// Escalation risk
GET /api/analytics/escalation-risk

// Trigger phrases
GET /api/analytics/trigger-phrases

// Conflict chains
GET /api/analytics/conflict-chains

// Unmet needs
GET /api/analytics/unmet-needs

// Timeline data
GET /api/conflicts?relationship_id={id}&include_enrichment=true

// Health metrics
GET /api/analytics/health-score
```

### Real-Time Updates

```javascript
// Subscribe to conflict updates via WebSocket
ws://localhost:8000/ws/analytics/{relationship_id}

Message types:
- conflict_created
- trigger_phrase_detected
- escalation_risk_updated
- analysis_complete
```

---

## 4.4 Implementation Checklist

- [ ] Create Escalation Risk Card component
- [ ] Build Unresolved Issues list component
- [ ] Create Chronic Needs visualization
- [ ] Build Trigger Phrase table with sorting/filtering
- [ ] Create Trigger Phrase heat map
- [ ] Build Conflict Timeline component
- [ ] Implement Conflict Chain visualization
- [ ] Create Health Score dashboard
- [ ] Build Metrics cards
- [ ] Create Historical Trends sparklines
- [ ] Implement Insights generation
- [ ] Build Recommendations panel
- [ ] Create navigation between dashboard pages
- [ ] Add responsive design for mobile
- [ ] Wire up to analytics endpoints
- [ ] Add WebSocket real-time updates

---

## 4.5 Page Structure Example

### `/analytics/conflicts` (Main Dashboard)

```
┌─────────────────────────────────────────────────────┐
│ Relationship Health & Conflict Analysis              │
├─────────────────────────────────────────────────────┤
│                                                     │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│ │ Risk Score  │  │ Next Fight  │  │Unresolved   │ │
│ │  72% High   │  │  in 4 days  │  │  Issues: 3  │ │
│ └─────────────┘  └─────────────┘  └─────────────┘ │
│                                                     │
│ ┌─────────────────────────────────────────────────┐│
│ │ Unresolved Issues                              ││
│ ├─────────────────────────────────────────────────┤│
│ │ • Communication (10 days ago, resentment: 7/10)││
│ │ • Trust issues (5 days ago, resentment: 8/10) ││
│ │ • Expectations (2 days ago, resentment: 6/10) ││
│ └─────────────────────────────────────────────────┘│
│                                                     │
│ ┌─────────────────────────────────────────────────┐│
│ │ Chronic Unmet Needs                            ││
│ ├─────────────────────────────────────────────────┤│
│ │ Feeling Heard ████████████░░░░ 71% of conflicts││
│ │ Trust        ███████░░░░░░░░░░ 58% of conflicts││
│ │ Appreciation ██████░░░░░░░░░░░ 45% of conflicts││
│ └─────────────────────────────────────────────────┘│
│                                                     │
│ [Start Mediation]  [View Triggers]  [Timeline]    │
└─────────────────────────────────────────────────────┘
```

---

## 4.6 Styling Guide

### Color Scheme

```css
/* Risk Levels */
--risk-low: #10b981 (green)
--risk-medium: #f59e0b (yellow)
--risk-high: #f97316 (orange)
--risk-critical: #ef4444 (red)

/* Intensity */
--intensity-low: #dbeafe (light blue)
--intensity-high: #dc2626 (dark red)

/* Status */
--resolved: #10b981 (green)
--unresolved: #6b7280 (gray)
--ongoing: #f59e0b (yellow)
```

### Fonts & Spacing

- Headlines: Larger, bold, high contrast
- Body text: Clear, readable, good whitespace
- Cards: Padded, with subtle shadows
- Charts: High data-ink ratio, minimize clutter

---

## 4.7 Testing Strategy

### Unit Tests

```typescript
describe('RiskScoreCard', () => {
  it('displays correct color for risk level', () => {
    const { getByText } = render(
      <RiskScoreCard riskScore={0.8} interpretation="critical" />
    );
    expect(getByText('critical')).toHaveClass('text-red-500');
  });

  it('shows recommendations', () => {
    const recs = ['Resolve unresolved issues'];
    const { getByText } = render(
      <RiskScoreCard recommendations={recs} />
    );
    expect(getByText(recs[0])).toBeInTheDocument();
  });
});
```

### Integration Tests

1. Load dashboard → all components render
2. Update risk score → UI reflects change
3. Click on unresolved issue → navigate to detail
4. WebSocket message received → dashboard updates in real-time

---

## 4.8 Success Criteria

- Couples can identify their top 3 unmet needs within 30 seconds
- Dashboard loads in <2 seconds
- 80%+ of couples report "this explains why we keep fighting"
- Users take action on recommendations within 7 days
- Couples report feeling more optimistic after viewing insights
- Mobile view is responsive and usable

---

## 4.9 Stretch Goals (Phase 4+)

- Predictive alerts: "You're at risk for a fight tomorrow based on patterns"
- Repair plan templates: "Based on your history, here's what might work"
- Cycle correlation: "Your fights cluster around cycle phase X"
- Expert tips: "Partners who struggle with X typically benefit from Y"
- Progress tracking: "You've resolved 40% of chronic needs compared to last month"

---

## Next Steps

Phase 4 is the final phase. After this, you have a complete system for:
1. **Capturing** conflict patterns
2. **Analyzing** escalation risks
3. **Mediating** with awareness
4. **Visualizing** insights

Consider gathering user feedback and planning Phase 5 enhancements based on real usage.
