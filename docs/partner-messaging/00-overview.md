# Partner-to-Partner Messaging - Overview

Luna's partner messaging feature enables couples to communicate directly within the app, with optional AI assistance that helps them communicate more effectively.

## Purpose

This feature **supplements** (not replaces) existing communication channels. It's designed for:
- Daily check-ins between partners
- Conflict-related communication where Luna's guidance is valuable
- Moments when partners want AI-assisted communication coaching

## Key Principles

### 1. Luna Assistance is Optional & Configurable
Partners can choose their assistance level:
- **Always**: Luna reviews every message before sending
- **On Request**: Manual Luna review with a button tap
- **High Risk Only**: Luna only intervenes for potentially harmful messages
- **Off**: No Luna involvement

### 2. Suggestions are Private
When Luna suggests a message improvement:
- Only the **typing partner** sees the suggestion
- The receiving partner **never knows** Luna intervened
- This preserves authenticity while enabling growth

### 3. Passive Intelligence
All messages are analyzed (with consent) to:
- Detect communication patterns
- Identify triggers and escalation risks
- Feed relationship health insights to the dashboard
- Help Luna provide better personalized advice

## Feature Phases

| Phase | Feature | Description |
|-------|---------|-------------|
| [Phase 1](./01-phase-basic-messaging.md) | Basic Messaging | Send/receive messages, history, real-time sync |
| [Phase 2](./02-phase-read-receipts-typing.md) | Read Receipts & Typing | Delivery status, typing indicators, preferences |
| [Phase 3](./03-phase-luna-suggestions.md) | Luna Suggestions | Pre-send review, active intervention, configurable sensitivity |
| [Phase 4](./04-phase-passive-analysis.md) | Passive Analysis | Sentiment tracking, trigger detection, dashboard integration |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Partner Chat UI                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Message     │  │ Luna        │  │ Settings &          │  │
│  │ Input       │  │ Suggestion  │  │ Preferences         │  │
│  │             │  │ Overlay     │  │                     │  │
│  └──────┬──────┘  └──────┬──────┘  └─────────────────────┘  │
└─────────┼────────────────┼──────────────────────────────────┘
          │                │
          ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│                    WebSocket Layer                           │
│         (Real-time message delivery, typing, receipts)       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend Services                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │ Partner         │  │ Message         │  │ Message     │  │
│  │ Messaging       │  │ Suggestion      │  │ Analysis    │  │
│  │ Routes          │  │ Service         │  │ Service     │  │
│  └────────┬────────┘  └────────┬────────┘  └──────┬──────┘  │
│           │                    │                   │         │
│           ▼                    ▼                   ▼         │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    Database Service                      ││
│  │  (partner_conversations, partner_messages, suggestions) ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  Existing Services Integration               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │ Conflict        │  │ Gottman         │  │ Pattern     │  │
│  │ Enrichment      │  │ Analysis        │  │ Analysis    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

### Backend

| Component | Technology | Version | Notes |
|-----------|------------|---------|-------|
| Web Framework | FastAPI | 0.104+ | Async Python web framework |
| Database | PostgreSQL | 15+ | Via Supabase |
| Database Driver | psycopg2-binary | 2.9+ | Direct SQL queries |
| Real-time | WebSocket | Native FastAPI | Following `realtime_transcription.py` pattern |
| LLM Provider | OpenRouter | API | Gemini 2.5 Flash via `llm_service.py` |
| Background Tasks | FastAPI BackgroundTasks | Built-in | For async message analysis |
| Structured Output | Pydantic | 2.0+ | For LLM response parsing |

### Frontend

| Component | Technology | Version | Notes |
|-----------|------------|---------|-------|
| Framework | React | 18.3.1 | With TypeScript 5.5+ |
| Build Tool | Vite | 5.2.0 | Fast dev server |
| Styling | Tailwind CSS | 3.4.17 | Custom theme in `tailwind.config.js` |
| State Management | React Context | Built-in | RelationshipContext, AuthContext |
| Icons | Lucide React | 0.522+ | Consistent icon library |
| Markdown | react-markdown | 10.1+ | For rich text in messages |

### Infrastructure

| Component | Technology | Notes |
|-----------|------------|-------|
| Hosting | Supabase | PostgreSQL + Auth + Realtime ready |
| API URL | Environment Variable | `VITE_API_URL` for frontend |
| WebSocket | Same origin as API | `ws://` or `wss://` based on protocol |

### Configuration Files

| File | Purpose |
|------|---------|
| `backend/app/config.py` | API keys, database URL, settings |
| `frontend/.env` | `VITE_API_URL` environment variable |
| `frontend/tailwind.config.js` | Custom theme colors and components |

## Database Schema Overview

See [Database Schema](./05-database-schema.md) for complete details.

| Table | Purpose |
|-------|---------|
| `partner_conversations` | One per relationship, tracks conversation metadata |
| `partner_messages` | Individual messages with analysis fields |
| `message_suggestions` | Luna's pre-send suggestions (private) |
| `partner_messaging_preferences` | Per-user assistance settings |

---

## Files to Create/Modify

### Backend Files

| File | Action | Phase | Description |
|------|--------|-------|-------------|
| `backend/app/models/migrations/009_partner_messaging.sql` | Create | 1 | Database migration |
| `backend/app/services/db_service.py` | Modify | 1-4 | Add messaging DB methods |
| `backend/app/models/schemas.py` | Modify | 1-4 | Add Pydantic models |
| `backend/app/routes/partner_messaging_routes.py` | Create | 1 | REST API endpoints |
| `backend/app/routes/partner_messaging_websocket.py` | Create | 1 | WebSocket handler |
| `backend/app/main.py` | Modify | 1 | Register new routers |
| `backend/app/services/message_suggestion_service.py` | Create | 3 | Luna suggestion logic |
| `backend/app/services/message_analysis_service.py` | Create | 4 | Async analysis pipeline |

### Frontend Files

| File | Action | Phase | Description |
|------|--------|-------|-------------|
| `frontend/src/pages/PartnerChat.tsx` | Create | 1 | Main chat page |
| `frontend/src/components/partner-chat/ConversationView.tsx` | Create | 1 | Message list |
| `frontend/src/components/partner-chat/MessageBubble.tsx` | Create | 1 | Single message |
| `frontend/src/components/partner-chat/MessageInput.tsx` | Create | 1 | Input with Luna |
| `frontend/src/components/partner-chat/TypingIndicator.tsx` | Create | 2 | Typing animation |
| `frontend/src/components/partner-chat/MessageStatus.tsx` | Create | 2 | Read/delivered icons |
| `frontend/src/pages/MessagingSettings.tsx` | Create | 2 | Preferences page |
| `frontend/src/components/partner-chat/LunaSuggestionOverlay.tsx` | Create | 3 | Suggestion UI |
| `frontend/src/components/analytics/MessagingInsights.tsx` | Create | 4 | Dashboard widget |
| `frontend/src/components/navigation/BottomNav.tsx` | Modify | 1 | Add Chat nav item |
| `frontend/src/App.tsx` | Modify | 1 | Add routes |

### Configuration Files

| File | Action | Description |
|------|--------|-------------|
| `frontend/.env` | Verify | Ensure `VITE_API_URL` is set |
| `backend/app/config.py` | Verify | Ensure DB and LLM config exists |

## Implementation Order

**Backend First, Then Frontend**

1. Database migration with all tables
2. Backend services and APIs (Phases 1-4)
3. Frontend components and pages (Phases 1-4)

This allows testing the API independently before building UI.

## Privacy & Security

- **No E2E Encryption (MVP)**: Luna analyzes messages server-side
- **Future**: Option for on-device analysis before E2E encryption
- **Data Retention**: Messages stored indefinitely for relationship intelligence
- **Access Control**: Only relationship members can access their conversation

## Success Metrics

1. **Adoption**: % of active couples using partner messaging
2. **Luna Engagement**: % of messages reviewed by Luna before sending
3. **Suggestion Acceptance**: % of Luna suggestions accepted vs rejected
4. **Escalation Prevention**: Reduction in detected escalation patterns
5. **Relationship Health**: Improvement in dashboard health scores
