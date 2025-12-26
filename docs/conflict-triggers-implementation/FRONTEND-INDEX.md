# Frontend Integration Guide - Complete Index

**Overview**: Step-by-step frontend implementation for all 4 phases of Conflict Triggers & Escalation Analysis

---

## Quick Reference

| Phase | Focus | Frontend Work | Timeline | Files |
|-------|-------|---------------|----------|-------|
| **1** | Data Capture | ❌ None | - | `FRONTEND-PHASE-1.md` |
| **2** | Analytics | 📊 Pages & Components | 2-3 weeks | `FRONTEND-PHASE-2.md` |
| **3** | Luna Context | 💬 Enhanced Mediator | 2-3 weeks | `FRONTEND-PHASE-3.md` |
| **4** | Dashboard | 📈 Visualizations | 2-3 weeks | `FRONTEND-PHASE-4.md` |

---

## Phase 1: Data Capture & Enrichment

**Status**: ✅ Complete (Backend)
**Frontend Impact**: None
**User Facing**: No

### What Happens
- Backend enriches conflicts in background
- No UI changes needed
- Data captured silently

### Frontend Checklist
- ✅ No code changes required
- ✅ Existing frontend works unchanged
- ✅ Ready for Phase 2

**See**: `FRONTEND-PHASE-1.md`

---

## Phase 2: Analytics & Pattern Detection

**Status**: 📋 Ready to Build
**Frontend Impact**: New pages and components
**User Facing**: Yes - analytics dashboard

### What Gets Built

#### New Routes
```
/analytics/conflicts        → Risk assessment & unresolved issues
/analytics/triggers         → Trigger phrase analysis & trends
/analytics/timeline         → Conflict timeline & chains
```

#### New Components
- `EscalationRiskCard` - Risk score display
- `TriggerPhraseTable` - Phrase listing with metrics
- `ConflictTimeline` - Visual timeline
- `ConflictChains` - Related conflicts
- `ChronicNeedsList` - Recurring unmet needs

#### API Integration
```typescript
GET /api/analytics/escalation-risk
GET /api/analytics/trigger-phrases
GET /api/analytics/conflict-chains
GET /api/analytics/unmet-needs
```

#### Files to Create
```
src/pages/Analytics/
├── ConflictAnalysis.tsx       (NEW)
├── TriggerPhrases.tsx         (NEW)
└── Timeline.tsx               (NEW)

src/components/analytics/
├── EscalationRiskCard.tsx     (NEW)
├── TriggerPhraseTable.tsx     (NEW)
├── ConflictTimeline.tsx       (NEW)
├── ConflictChains.tsx         (NEW)
└── ChronicNeedsList.tsx       (NEW)

src/types/
└── analytics.ts               (NEW)
```

### Phase 2 Checklist
- [ ] Create 3 new routes
- [ ] Create 5+ analytics components
- [ ] Add TypeScript types
- [ ] Update navigation
- [ ] Integrate analytics APIs
- [ ] Add styling/layout
- [ ] Test all components
- [ ] Mobile responsive

**See**: `FRONTEND-PHASE-2.md`

---

## Phase 3: Luna Context Awareness

**Status**: 📋 Ready to Build
**Frontend Impact**: Enhanced existing component
**User Facing**: Yes - improved Luna mediation

### What Gets Enhanced

#### MediatorModal Updates
```tsx
// Add context display
// Show unresolved issues
// Display chronic needs
// Show escalation warnings
// Enhanced header with context
```

#### New Components
- `MediatorContextPanel` - Shows conflict context
- Updated `MediatorModal` - With context awareness

#### New Hooks
- `useLunaMediator` - Context loading and messaging
- `useConflictContext` - Real-time context updates

#### API Integration
```typescript
GET /api/mediator/context/{conflict_id}
POST /api/mediator/message/{conflict_id}
```

#### Files to Create/Update
```
src/pages/
└── PostFightSession.tsx       (UPDATE - add context display)

src/components/
├── MediatorModal.tsx          (UPDATE - enhanced)
└── MediatorContextPanel.tsx   (NEW)

src/hooks/
├── useLunaMediator.ts         (NEW)
└── useConflictContext.ts      (NEW)

src/types/
└── mediation.ts               (NEW/UPDATE)
```

### Phase 3 Checklist
- [ ] Update MediatorModal component
- [ ] Create context panel component
- [ ] Create mediator hooks
- [ ] Integrate context APIs
- [ ] Add TypeScript types
- [ ] Test Luna context loading
- [ ] Test real-time updates
- [ ] Mobile responsive

**See**: `FRONTEND-PHASE-3.md`

---

## Phase 4: Dashboard Visualizations

**Status**: 📋 Ready to Build
**Frontend Impact**: New main dashboard
**User Facing**: Yes - peak user value

### What Gets Built

#### New Main Route
```
/analytics                      → Main dashboard
```

#### New Components
- `Dashboard` - Main page (wrapper)
- `HealthScore` - 0-100 score with breakdown
- `RiskMetrics` - Risk cards
- `MetricsOverview` - Key numbers
- `ConflictTrends` - Line charts (30 days)
- `TriggerPhraseHeatmap` - Phrase frequency heatmap
- `UnmetNeedsAnalysis` - Core needs with recommendations
- `RecommendationsPanel` - Actionable next steps
- `InsightsPanel` - Auto-generated insights

#### Charts & Visualizations
- Line charts (recharts) - Trends
- Heat maps - Trigger frequency
- Progress bars - Health metrics
- Status indicators - Color-coded risks

#### API Integration
```typescript
GET /api/analytics/health-score
GET /api/analytics/dashboard
GET /api/analytics/escalation-risk
GET /api/analytics/unmet-needs
```

#### Files to Create
```
src/pages/Analytics/
└── Dashboard.tsx              (NEW)

src/components/dashboard/
├── HealthScore.tsx            (NEW)
├── RiskMetrics.tsx            (NEW)
├── MetricsOverview.tsx        (NEW)
├── ConflictTrends.tsx         (NEW)
├── TriggerPhraseHeatmap.tsx   (NEW)
├── UnmetNeedsAnalysis.tsx     (NEW)
└── RecommendationsPanel.tsx   (NEW)

src/hooks/
└── useDashboardData.ts        (NEW)

src/styles/
└── dashboard.css              (NEW)
```

#### Dependencies (New)
```json
{
  "recharts": "^2.x.x"
}
```

### Phase 4 Checklist
- [ ] Create main dashboard page
- [ ] Create 7+ dashboard components
- [ ] Create recharts visualizations
- [ ] Add TypeScript types
- [ ] Create dashboard hook
- [ ] Update main navigation
- [ ] Add CSS styling
- [ ] Test all charts
- [ ] Test data refresh (5 min interval)
- [ ] Mobile responsive
- [ ] Performance optimization

**See**: `FRONTEND-PHASE-4.md`

---

## Implementation Timeline

### Week 1-2: Phase 2 Analytics
- Create analytics pages
- Build analytics components
- Integrate analytics APIs
- Style and test

### Week 3-4: Phase 3 Luna Context
- Enhance MediatorModal
- Create context panel
- Integrate context APIs
- Test integration

### Week 5-6: Phase 4 Dashboard
- Create main dashboard
- Build all components
- Integrate chart library
- Style and optimize

### Week 7: Testing & Polish
- Cross-browser testing
- Mobile optimization
- Performance tuning
- User feedback

---

## Navigation Structure

```
App
├── / (Home/Dashboard)
├── /fight-capture
├── /history
├── /calendar
├── /upload
├── /analytics [NEW - Phase 2+]
│   ├── / (Main Dashboard - Phase 4)
│   ├── /conflicts (Analysis - Phase 2)
│   ├── /triggers (Phrases - Phase 2)
│   └── /timeline (Timeline - Phase 2)
└── /mediation [existing]
```

---

## File Structure Summary

```
src/
├── pages/
│   ├── Analytics/
│   │   ├── Dashboard.tsx           (Phase 4)
│   │   ├── ConflictAnalysis.tsx    (Phase 2)
│   │   ├── TriggerPhrases.tsx      (Phase 2)
│   │   └── Timeline.tsx            (Phase 2)
│   └── PostFightSession.tsx        (Phase 3 update)
│
├── components/
│   ├── analytics/                  (Phase 2)
│   │   ├── EscalationRiskCard.tsx
│   │   ├── TriggerPhraseTable.tsx
│   │   ├── ConflictTimeline.tsx
│   │   ├── ConflictChains.tsx
│   │   ├── ChronicNeedsList.tsx
│   │   └── ... (more)
│   ├── dashboard/                  (Phase 4)
│   │   ├── HealthScore.tsx
│   │   ├── RiskMetrics.tsx
│   │   ├── MetricsOverview.tsx
│   │   ├── ConflictTrends.tsx
│   │   ├── TriggerPhraseHeatmap.tsx
│   │   ├── UnmetNeedsAnalysis.tsx
│   │   ├── RecommendationsPanel.tsx
│   │   └── InsightsPanel.tsx
│   ├── MediatorModal.tsx           (Phase 3 update)
│   └── MediatorContextPanel.tsx    (Phase 3)
│
├── hooks/
│   ├── useLunaMediator.ts          (Phase 3)
│   ├── useConflictContext.ts       (Phase 3)
│   ├── useDashboardData.ts         (Phase 4)
│   └── ... (more)
│
├── types/
│   ├── analytics.ts                (Phase 2)
│   ├── mediation.ts                (Phase 3)
│   └── ... (more)
│
└── styles/
    ├── dashboard.css               (Phase 4)
    └── ... (more)
```

---

## Design System Requirements

### Colors
- Primary: Blue-600
- Success: Green-600
- Warning: Yellow-600
- Danger: Red-600
- Secondary: Purple-600

### Typography
- Headlines: 24-32px, bold
- Body: 14-16px, regular
- Small: 12-14px, regular

### Components
- Cards: White background, shadow, rounded
- Buttons: Rounded, padded, hover states
- Inputs: Border, rounded, focus ring
- Charts: Clear labels, legend, tooltip

---

## Performance Considerations

### Data Fetching
- Parallel API calls with Promise.all()
- 5-minute refresh interval for dashboard
- Real-time updates for context (when mediating)

### Component Optimization
- Memoize expensive components
- Use React.lazy for route splitting
- Optimize chart re-renders

### Bundle Size
- Tree-shake unused recharts components
- Consider lightweight alternatives

---

## Testing Strategy

### Unit Tests
- Component snapshot tests
- Hook tests (useHook...)
- Utility function tests

### Integration Tests
- Full dashboard flow
- Data loading and display
- API integration

### E2E Tests
- User journey from conflict to insights
- Navigation and routing
- Data refreshing

---

## Deployment Considerations

### Frontend Dependencies
```json
{
  "react": "^18.x",
  "react-dom": "^18.x",
  "react-router-dom": "^6.x",
  "recharts": "^2.x"
}
```

### Build & Deploy
- Build: `npm run build`
- Deploy: Vercel, Netlify, or similar
- Environment: Configure API_BASE_URL

### Monitoring
- Error tracking (Sentry)
- Analytics (for usage patterns)
- Performance monitoring

---

## Quick Start

### Phase 2: Start Here
```bash
# Read the guide
cat docs/conflict-triggers-implementation/FRONTEND-PHASE-2.md

# Create files according to guide
# 3 new routes, 5+ components, 1 types file

# Test and iterate
```

### Phase 3: Continue
```bash
# Read the guide
cat docs/conflict-triggers-implementation/FRONTEND-PHASE-3.md

# Update existing component
# Create 2 new components, 2 new hooks

# Test Luna integration
```

### Phase 4: Complete
```bash
# Read the guide
cat docs/conflict-triggers-implementation/FRONTEND-PHASE-4.md

# Create dashboard page and 7+ components
# Add chart library
# Style and optimize

# Deploy to production
```

---

## Resources

| Resource | Location |
|----------|----------|
| Backend Integration | `01-PHASE-1-DATA-ENRICHMENT.md` |
| Phase 2 Analytics | `02-PHASE-2-PATTERN-DETECTION.md` |
| Phase 3 Luna | `03-PHASE-3-LUNA-AWARENESS.md` |
| Phase 4 Dashboard | `04-PHASE-4-DASHBOARD.md` |
| Frontend Phase 1 | `FRONTEND-PHASE-1.md` |
| Frontend Phase 2 | `FRONTEND-PHASE-2.md` |
| Frontend Phase 3 | `FRONTEND-PHASE-3.md` |
| Frontend Phase 4 | `FRONTEND-PHASE-4.md` |
| Overview | `00-OVERVIEW.md` |

---

## Summary

✅ **Phase 1**: No frontend work (backend enrichment only)
📋 **Phase 2**: Analytics pages and components
📋 **Phase 3**: Luna context awareness
📋 **Phase 4**: Dashboard with visualizations

Each phase builds on the previous, delivering user value incrementally.

**Ready to start?** Begin with `FRONTEND-PHASE-2.md` after Phase 1 backend is deployed.
