# Personalized Repair Plan System - Overview

## Vision

Transform generic repair advice into deeply personalized guidance that references:
1. **Partner profiles** - What each person needs, what calms them, what triggers them
2. **Current fight context** - Specific quotes, escalation moments, unmet needs
3. **Past fight intelligence** - What worked before, what failed, recurring patterns

## The Three Context Sources

Every repair plan should draw from all three:

```
┌─────────────────────────────────────────────────────────────────┐
│                    PERSONALIZED REPAIR PLAN                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   PARTNER    │  │   CURRENT    │  │   PAST FIGHT         │  │
│  │   PROFILES   │  │   FIGHT      │  │   INTELLIGENCE       │  │
│  ├──────────────┤  ├──────────────┤  ├──────────────────────┤  │
│  │ • Preferences│  │ • Transcript │  │ • Learned patterns   │  │
│  │ • Triggers   │  │ • Quotes     │  │ • What worked        │  │
│  │ • Soothing   │  │ • Escalation │  │ • What failed        │  │
│  │ • Apology    │  │   points     │  │ • Similar past fights│  │
│  │   style      │  │ • Unmet needs│  │ • Repair outcomes    │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Example Output

**Current (generic):**
> "Approach your partner when they've calmed down and apologize for the miscommunication."

**Target (personalized):**
> "Wait 20 minutes - Sarah's profile says she needs space after conflicts. In the Dec 15 fight (similar topic), waiting worked. Don't say 'calm down' - that phrase escalated 3/4 past fights. Start by acknowledging what she said at 3:42 about feeling dismissed. Make her tea (her profile lists this as a soothing gesture)."

## Development Phases

| Phase | Focus | Key Deliverable |
|-------|-------|-----------------|
| **Phase 1** | Enhanced Onboarding | 4 new repair-focused questions |
| **Phase 2** | Profile Retrieval & Prompt | Fetch ALL profile data, rewrite LLM prompt |
| **Phase 3** | Fight Debrief System | Post-fight analysis with Pydantic models |
| **Phase 4** | Cross-Fight Intelligence | Pattern learning, similar fight retrieval |

## Guiding Principles

1. **LLM-driven, not rule-based** - All inference through GPT with Pydantic structured output
2. **No user feedback required** - Infer what worked from transcript analysis and fight sequences
3. **Explicit citations** - Every suggestion must reference its source (profile, transcript, past fight)
4. **Both partners required** - Repair plan for A→B needs B's preferences

## Documentation Structure

```
docs/repair/
├── 00-overview.md              # This file
├── 01-phase-1-onboarding.md    # Enhanced onboarding questions
├── 02-phase-2-retrieval.md     # Profile retrieval & prompt rewrite
├── 03-phase-3-fight-debrief.md # Post-fight analysis system
├── 04-phase-4-intelligence.md  # Cross-fight pattern learning
├── 05-pydantic-models.md       # All data models
└── 06-observations.md          # Additional recommendations
```

## Current State vs Target State

| Aspect | Current | Target |
|--------|---------|--------|
| Profile retrieval | RAG by transcript similarity | Fetch ALL profile data |
| Onboarding | No repair-specific questions | 4 dedicated repair questions |
| LLM prompt | "Consider their profiles" | Explicit requirements with validation |
| Past fights | Not used | FightDebrief stored, patterns extracted |
| Repair outcomes | Not tracked | Inferred from subsequent fights |
| Citations | Sometimes quotes transcript | Always cites source (profile/transcript/history) |
