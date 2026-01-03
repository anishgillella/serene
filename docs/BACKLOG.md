# Serene Feature Backlog

Central tracking document for all planned and in-progress features.

---

## Status Legend

| Status | Meaning |
|--------|---------|
| **Completed** | Fully implemented and deployed |
| **In Progress** | Currently being worked on |
| **Documented** | Has full documentation, ready to implement |
| **Planned** | Identified as needed, documentation exists |
| **Idea** | Concept only, needs documentation |

---

## Feature Categories

### 1. Core Features (Completed)

| Feature | Status | Documentation |
|---------|--------|---------------|
| Fight Recording & Transcription | Completed | `/docs/phases/` |
| Conflict Analysis (Gottman, Triggers) | Completed | `/docs/repair/` |
| Luna Voice Mediation | Completed | `/docs/phases/` |
| Post-Fight Session & Repair Plans | Completed | `/docs/repair/` |
| Analytics Dashboard | Completed | `/docs/phases/` |
| Calendar & Cycle Tracking | Completed | `/docs/phases/` |
| Partner Messaging (Text) | Completed | `/docs/partner-messaging/` |
| Luna Chat Suggestions (Pre-send) | Completed | `/docs/partner-messaging/03-phase-luna-suggestions.md` |
| Message Passive Analysis | Completed | `/docs/partner-messaging/04-phase-passive-analysis.md` |

---

### 2. Connection & Affection Features

| Feature | Status | Documentation | Priority |
|---------|--------|---------------|----------|
| **Connection Gestures** (Hugs, Kisses, Thinking of You) | Documented | `/docs/connection-gestures/` | **P1 - Next** |
| Partner Availability Status | Idea | Needs docs | P3 |
| Gratitude Journal (shared) | Idea | Needs docs | P3 |
| Love Language Integration | Idea | Needs docs | P3 |
| Relationship Milestones & Celebrations | Idea | Needs docs | P4 |

---

### 3. Communication Platform

Expanding beyond text messaging to voice and video.

| Feature | Status | Documentation | Priority |
|---------|--------|---------------|----------|
| Voice Messages | Documented | `/docs/communication-platform/02-voice-messages.md` | P2 |
| Voice Calls | Documented | `/docs/communication-platform/03-voice-calls.md` | P2 |
| Video Calls | Documented | `/docs/communication-platform/04-video-calls.md` | P3 |
| Photo/Video Sharing | Documented | `/docs/communication-platform/05-media-sharing.md` | P3 |

---

### 4. Multi-Tenancy & Auth

Enabling multiple couples to use the platform.

| Feature | Status | Documentation | Priority |
|---------|--------|---------------|----------|
| Auth Foundation (Auth0) | Documented | `/docs/multi-tenancy/01-phase-auth-foundation.md` | P1 |
| Multi-Tenancy Core | Documented | `/docs/multi-tenancy/02-phase-multi-tenancy-core.md` | P1 |
| Partner Invitation Flow | Documented | `/docs/multi-tenancy/03-phase-partner-invitation.md` | P1 |
| Data Model Cleanup | Documented | `/docs/multi-tenancy/04-phase-data-model-cleanup.md` | P2 |
| Security Hardening | Documented | `/docs/multi-tenancy/05-phase-security-hardening.md` | P2 |

---

### 5. Performance & Infrastructure

| Feature | Status | Documentation | Priority |
|---------|--------|---------------|----------|
| Redis Caching Layer | Documented | `/docs/multi-tenancy/06-phase-future-optimizations.md` | P2 |
| Database Connection Pooling | Documented | `/docs/multi-tenancy/06-phase-future-optimizations.md` | P2 |
| Background Job Queue (Celery) | Documented | `/docs/multi-tenancy/06-phase-future-optimizations.md` | P2 |
| Read Replicas | Documented | `/docs/multi-tenancy/06-phase-future-optimizations.md` | P3 |
| CDN for Static Assets | Documented | `/docs/multi-tenancy/06-phase-future-optimizations.md` | P3 |
| Pinecone Index Sharding | Documented | `/docs/multi-tenancy/06-phase-future-optimizations.md` | P3 |

---

### 6. Monetization & Billing

| Feature | Status | Documentation | Priority |
|---------|--------|---------------|----------|
| Subscription Plans (Free/Premium/Therapy) | Documented | `/docs/multi-tenancy/06-phase-future-optimizations.md` | P2 |
| Stripe Integration | Documented | `/docs/multi-tenancy/06-phase-future-optimizations.md` | P2 |
| Usage Tracking & Limits | Documented | `/docs/multi-tenancy/06-phase-future-optimizations.md` | P2 |

---

### 7. Monitoring & Observability

| Feature | Status | Documentation | Priority |
|---------|--------|---------------|----------|
| Application Metrics (Prometheus) | Documented | `/docs/multi-tenancy/06-phase-future-optimizations.md` | P2 |
| Error Tracking (Sentry) | Documented | `/docs/multi-tenancy/06-phase-future-optimizations.md` | P2 |
| Structured Logging | Documented | `/docs/multi-tenancy/06-phase-future-optimizations.md` | P3 |

---

### 8. Internationalization & Accessibility

| Feature | Status | Documentation | Priority |
|---------|--------|---------------|----------|
| Multi-Language Support (i18n) | Documented | `/docs/multi-tenancy/06-phase-future-optimizations.md` | P3 |
| Offline Mode with Sync | Documented | `/docs/multi-tenancy/06-phase-future-optimizations.md` | P3 |
| Accessibility (WCAG) | Idea | Needs docs | P3 |

---

### 9. Technical Debt

Tracked separately in documentation folder.

| Item | Documentation |
|------|---------------|
| Backend Technical Debt | `/docs/documentation/BACKEND-TECHNICAL-DEBT.md` |
| Frontend Technical Debt | `/docs/documentation/FRONTEND-TECHNICAL-DEBT.md` |
| Optimization Recommendations | `/docs/documentation/OPTIMIZATION-RECOMMENDATIONS.md` |

---

## Priority Definitions

| Priority | Meaning | Timeline |
|----------|---------|----------|
| **P0** | Critical blocker | This sprint |
| **P1** | High priority | Next 2-4 weeks |
| **P2** | Medium priority | Next 1-2 months |
| **P3** | Low priority | Backlog |
| **P4** | Nice to have | Future consideration |

---

## Recommended Implementation Order

### Phase A: Quick Wins (1-2 weeks)
1. **Connection Gestures** - Adds emotional value, uses existing infrastructure

### Phase B: Multi-Tenancy (2-4 weeks)
1. Auth Foundation
2. Multi-Tenancy Core
3. Partner Invitation Flow

### Phase C: Communication Platform (4-8 weeks)
1. Voice Messages
2. Voice Calls
3. Video Calls

### Phase D: Monetization (2-3 weeks)
1. Stripe Integration
2. Subscription Plans
3. Usage Tracking

### Phase E: Scale & Polish (Ongoing)
1. Performance optimizations
2. Monitoring
3. Internationalization

---

## Documentation Status Summary

| Category | Total Features | Documented | Needs Docs |
|----------|---------------|------------|------------|
| Connection & Affection | 5 | 1 | 4 |
| Communication Platform | 4 | 4 | 0 |
| Multi-Tenancy & Auth | 5 | 5 | 0 |
| Performance & Infrastructure | 6 | 6 | 0 |
| Monetization & Billing | 3 | 3 | 0 |
| Monitoring & Observability | 3 | 3 | 0 |
| Internationalization | 3 | 2 | 1 |
| **Total** | **29** | **24** | **5** |

---

## Features Needing Documentation

These features are identified but need full documentation before implementation:

1. **Partner Availability Status** - Show when partner is online/offline
2. **Gratitude Journal** - Shared space for appreciation notes
3. **Love Language Integration** - Tailor suggestions to love languages
4. **Relationship Milestones** - Track and celebrate anniversaries, firsts
5. **Accessibility (WCAG)** - Screen reader support, keyboard navigation

---

## How to Add a New Feature

1. Create a folder in `/docs/` with the feature name
2. Add `00-overview.md` with purpose, architecture, tech stack
3. Add phase files (`01-phase-xxx.md`, etc.) for implementation steps
4. Update this BACKLOG.md with the new feature
5. Set appropriate priority based on user value and dependencies

---

## Last Updated

2025-01-03
