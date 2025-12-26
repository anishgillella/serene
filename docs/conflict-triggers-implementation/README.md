# Conflict Triggers & Escalation Analysis - Complete Implementation Guide

## Quick Start

This folder contains a comprehensive, phase-by-phase implementation plan for adding conflict trigger detection and escalation pattern analysis to Serene.

**Start here:** Read `00-OVERVIEW.md` for the big picture, then proceed phase by phase.

## Document Structure

```
├── 00-OVERVIEW.md                    # Vision, roadmap, key principles
├── 01-PHASE-1-DATA-ENRICHMENT.md    # Database schema, LLM integration
├── 02-PHASE-2-PATTERN-DETECTION.md  # Analytics, pattern recognition
├── 03-PHASE-3-LUNA-AWARENESS.md     # Context-aware mediation
├── 04-PHASE-4-DASHBOARD.md          # User-facing visualizations
└── README.md                         # This file
```

## The Problem We're Solving

Current state:
- Conflicts are stored as isolated incidents
- Couples don't see why they keep fighting
- Luna doesn't understand that today's "door fight" is actually about yesterday's unresolved "trust issue"
- Surface complaints hide deeper unmet needs

Target state:
- Understand that conflicts are interconnected
- Identify trigger phrases that escalate fights
- See the root causes beneath surface complaints
- Luna mediates based on actual patterns, not just the current argument

## Example: How This Works

**Scenario:** Couple has a fight about the door not being closed.

**Without this system:**
- Fight logged as "Door not closed"
- No connection to yesterday's communication issue
- Luna mediates about the door mechanism
- Root issue (not feeling heard) never addressed
- Resentment accumulates for next fight

**With this system:**
- Fight identified as continuation of yesterday's unresolved issue
- Trigger phrase detected: "You didn't do that yesterday"
- System identifies root need: "Feeling heard"
- Luna says: "I notice you keep bringing up yesterday. Let's actually resolve that communication issue."
- Couples address real problem, feel heard, resentment decreases

## Implementation Timeline

- **Phase 1 (Data)**: 1-2 weeks
- **Phase 2 (Analytics)**: 2-3 weeks
- **Phase 3 (Luna)**: 2-3 weeks
- **Phase 4 (Dashboard)**: 2-3 weeks

**Total: ~8-11 weeks** for complete implementation

Each phase delivers independent value and can be stopped/pivoted after completion.

## Key Design Principles

1. **Non-Breaking**: All changes are additive; existing functionality continues to work
2. **Data-Driven**: Patterns are discovered from actual transcript analysis, not hardcoded
3. **LLM-Powered**: Use existing GPT-4o-mini for intelligent extraction
4. **Privacy-Focused**: All analysis stays within relationship context
5. **Incremental Value**: Each phase delivers benefit before moving to next

## Phase Overview

### Phase 1: Data Capture & Enrichment
**What**: Capture richer conflict metadata
- Link conflicts to previous conflicts
- Extract trigger phrases from transcripts
- Identify unmet needs beneath surface complaints
- Score resentment level

**Why**: Can't analyze patterns we don't capture

**Outputs**:
- Enhanced `conflicts` table
- New `trigger_phrases` table
- New `unmet_needs` table
- Updated LLM analysis prompts

### Phase 2: Intelligence & Pattern Detection
**What**: Build analytics on enriched data
- Calculate escalation risk scores
- Identify trigger phrase patterns
- Trace conflict chains
- Find chronic unmet needs

**Why**: Make the data actionable and insightful

**Outputs**:
- `pattern_analysis_service.py`
- Analytics endpoints
- Risk prediction algorithms
- Pattern detection functions

### Phase 3: Luna's Awareness
**What**: Integrate insights into mediation
- Pre-load context when mediation starts
- Luna aware of unresolved issues
- Real-time escalation detection
- Intelligent interventions

**Why**: Luna becomes smarter and more helpful

**Outputs**:
- Context injection system
- Enhanced Luna system prompts
- Real-time pattern detection
- Personalized repair plans

### Phase 4: Dashboard Visualization
**What**: Show couples what's really happening
- Risk assessment dashboard
- Trigger phrase analytics
- Conflict timeline visualization
- Health metrics

**Why**: Couples can see patterns and take action

**Outputs**:
- New dashboard pages
- React components
- Data visualizations
- Actionable insights UI

## Technology Stack

- **Backend**: FastAPI, Python, PostgreSQL
- **Frontend**: React, TypeScript, TailwindCSS
- **LLM**: GPT-4o-mini (existing)
- **Vector DB**: Pinecone (for RAG)
- **Voice**: LiveKit Agents (existing)

## Critical Database Changes

### New Tables
- `trigger_phrases` - Extracted phrases with analysis
- `unmet_needs` - Identified underlying needs
- Migration file: `migration_conflict_triggers.sql`

### Modified Tables
- `conflicts` - Add parent_conflict_id, resentment_level, etc.

**Important**: All changes are backwards compatible. Existing conflicts continue to work.

## Success Metrics (End-to-End)

1. **Data Quality**: 90%+ of conflicts have trigger phrases extracted
2. **Pattern Accuracy**: Couples identify 3+ unmet needs in their history
3. **Prediction**: System predicts escalation with 70%+ accuracy
4. **Luna Quality**: Luna references past conflicts correctly 80%+ of the time
5. **User Impact**: Couples reduce conflict recurrence by 30% after using insights

## Getting Started

1. **Read `00-OVERVIEW.md`** - Understand the vision
2. **Review `01-PHASE-1-DATA-ENRICHMENT.md`** - Understand what data to capture
3. **Set up database migrations** - Create new tables
4. **Implement Phase 1** - Start enriching conflict data
5. **Proceed phase by phase** - Each phase builds on previous

## Key Files to Create/Modify

### Backend
- `app/services/pattern_analysis_service.py` (Phase 2)
- `app/routes/analytics_pattern.py` (Phase 2)
- `app/tools/conflict_analysis.py` (Phase 1 - enhance)
- `migrations/migration_conflict_triggers.sql` (Phase 1)

### Frontend
- `src/pages/Analytics/ConflictAnalysis.tsx` (Phase 4)
- `src/pages/Analytics/TriggerPhrases.tsx` (Phase 4)
- `src/pages/Analytics/Timeline.tsx` (Phase 4)
- `src/components/analytics/RiskScoreCard.tsx` (Phase 4)
- And many more component files...

## Common Questions

**Q: Do we need to reanalyze existing conflicts?**
A: Optional. Phase 1 enrichment applies to new conflicts. Backfilling existing conflicts is a nice-to-have but not required.

**Q: Will this slow down conflict analysis?**
A: Minimally. LLM analysis already happens; we're just extracting more from it.

**Q: Can we do this in a different order?**
A: Not really. Data (Phase 1) is foundational. You can skip Phase 4 (dashboard) but not 1-3.

**Q: How do we measure if it's working?**
A: Track the success metrics at the end of each phase. User feedback is critical.

## Next Steps

1. **Discuss with team**: Does this approach align with product vision?
2. **Estimate effort**: Do timeline estimates feel accurate?
3. **Prioritize**: Start with Phase 1 when ready
4. **Create tickets**: Break each phase into implementable tasks

## Questions or Changes?

This is a living document. As you implement, you may:
- Find better ways to detect patterns
- Discover new metrics worth tracking
- Realize some phases are more complex than estimated

Update this guide accordingly. The goal is to ship value incrementally, not to follow the plan perfectly.

---

**Ready to start?** Go read `00-OVERVIEW.md`, then tackle Phase 1.
