# Connection Gestures - Overview

Connection Gestures enables partners to send emotional expressions (hugs, kisses, "thinking of you") with AI-generated personalized messages based on relationship context.

## Purpose

This feature creates **micro-moments of connection** between partners through:
- Quick emotional gestures that require minimal effort to send
- AI-generated personalized messages based on past context (conflicts, conversations, profiles)
- A unique, celebratory receiving experience that demands acknowledgment
- Analytics on affection patterns over time

## Key Principles

### 1. AI-Assisted Personalization
When a partner sends a gesture, Luna drafts a contextual message:
- Uses RAG to pull from recent conflicts, chat history, partner profiles
- Partner can edit, regenerate, or write their own
- Creates meaningful connection with minimal effort

### 2. Celebration, Not Notification
Receiving a gesture is a **full-screen celebration moment**:
- Animated emoji particles floating upward
- Personalized message prominently displayed
- Must be explicitly acknowledged (can't miss it)
- Option to immediately send one back

### 3. Low Friction, High Impact
- One tap to select gesture type
- AI drafts the message automatically
- Real-time delivery via WebSocket
- Tracks patterns for relationship analytics

## Gesture Types

| Type | Emoji | Use Case |
|------|-------|----------|
| Hug | 🤗 | Comfort, "I'm here for you", warmth |
| Kiss | 💋 | Affection, love, making up |
| Thinking of You | 💚 | Random connection, "you're on my mind" |

## Feature Phases

| Phase | Feature | Description |
|-------|---------|-------------|
| [Phase 1](./01-phase-database-backend.md) | Database & Backend | Schema, API endpoints, service methods |
| [Phase 2](./02-phase-ai-message-generation.md) | AI Message Generation | RAG-powered personalized messages |
| [Phase 3](./03-phase-frontend-sending.md) | Frontend - Sending | FAB, gesture picker, send modal |
| [Phase 4](./04-phase-frontend-receiving.md) | Frontend - Receiving | Celebration modal, animations, acknowledgment |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Partner Chat UI                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Gesture     │  │ Send        │  │ Receive             │  │
│  │ FAB         │  │ Modal       │  │ Celebration Modal   │  │
│  │             │  │ (AI msg)    │  │                     │  │
│  └──────┬──────┘  └──────┬──────┘  └─────────────────────┘  │
└─────────┼────────────────┼──────────────────────────────────┘
          │                │
          ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│                    WebSocket Layer                           │
│         (Real-time gesture delivery & acknowledgment)        │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend Services                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │ Gesture         │  │ Gesture         │  │ Gesture     │  │
│  │ Routes          │  │ Message         │  │ Analytics   │  │
│  │                 │  │ Service (AI)    │  │ Service     │  │
│  └────────┬────────┘  └────────┬────────┘  └──────┬──────┘  │
│           │                    │                   │         │
│           ▼                    ▼                   ▼         │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    Database Service                      ││
│  │              (connection_gestures table)                 ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  Existing RAG Services                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │ Transcript      │  │ Partner         │  │ Conflict    │  │
│  │ RAG             │  │ Profiles        │  │ History     │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

### Backend

| Component | Technology | Notes |
|-----------|------------|-------|
| Web Framework | FastAPI | Async Python |
| Database | PostgreSQL | Via Supabase |
| Real-time | WebSocket | Existing partner messaging WebSocket |
| LLM | Gemini 2.5 Flash | Via OpenRouter for message generation |
| RAG | Existing services | transcript_rag, pinecone_service |

### Frontend

| Component | Technology | Notes |
|-----------|------------|-------|
| Framework | React 18 | With TypeScript |
| Styling | Tailwind CSS | Custom animations |
| Animations | CSS Keyframes | Float-up particles, heartbeat |
| State | React Hooks | useGestures custom hook |

## Database Schema Overview

| Table | Purpose |
|-------|---------|
| `connection_gestures` | Gesture records with message, acknowledgment status |

Key fields:
- `gesture_type`: 'hug', 'kiss', 'thinking_of_you'
- `sent_by`: 'partner_a' or 'partner_b'
- `message`: AI-generated or custom personalized note
- `ai_generated`: Whether message was AI-generated
- `acknowledged_at`: When recipient saw it
- `response_gesture_id`: If they sent one back

## Files to Create/Modify

### Backend Files

| File | Action | Phase | Description |
|------|--------|-------|-------------|
| `migrations/011_connection_gestures.sql` | Create | 1 | Database schema |
| `services/db_service.py` | Modify | 1 | Add gesture CRUD methods |
| `routes/gestures_routes.py` | Create | 1 | REST API endpoints |
| `routes/partner_messaging_websocket.py` | Modify | 1 | Add gesture message handling |
| `main.py` | Modify | 1 | Register gestures router |
| `models/schemas.py` | Modify | 1 | Add Pydantic models |
| `services/gesture_message_service.py` | Create | 2 | AI message generation |

### Frontend Files

| File | Action | Phase | Description |
|------|--------|-------|-------------|
| `components/gestures/gestureConfig.ts` | Create | 3 | Gesture types & styling |
| `components/gestures/GestureFAB.tsx` | Create | 3 | Floating action button |
| `components/gestures/SendGestureModal.tsx` | Create | 3 | Send modal with AI message |
| `hooks/useGestures.ts` | Create | 3 | Gesture state management |
| `components/gestures/ReceiveGestureModal.tsx` | Create | 4 | Celebration modal |
| `pages/PartnerChat.tsx` | Modify | 4 | Integrate all components |

## User Flow

### Sending Flow
```
1. Partner taps heart FAB (bottom-right of Partner Chat)
2. FAB expands → 3 gesture options appear
3. Partner selects gesture (e.g., 🤗 Hug)
4. Modal opens with:
   - AI-generated message based on context
   - "Regenerate" button for different suggestion
   - Editable textarea (can modify or write own)
   - Toggle: "Write my own" to start blank
5. Partner taps "Send"
6. Real-time delivery via WebSocket
```

### Receiving Flow
```
1. Full-screen celebration modal appears
2. Features:
   - Gradient background (gesture-specific color)
   - Large animated emoji (heartbeat effect)
   - 30 floating emoji particles rising up
   - Sender's personalized message in card
3. Partner reads message
4. Actions:
   - "Send One Back" → inline gesture picker + message
   - "Close" → acknowledges and dismisses
5. Sender notified that gesture was acknowledged
```

## AI Message Generation

When a partner selects a gesture, Luna generates a personalized message using:

### Context Sources (via existing RAG)
1. **Recent conflicts** (last 7 days) - "I know the discussion about finances was hard..."
2. **Recent chat messages** (last 10) - "Thinking about what you said earlier..."
3. **Partner profiles** - Communication style, love language hints
4. **Calendar/cycle insights** - "I know this week has been tough..."

### Generation Options
- **Use suggested message** - Send AI-generated as-is
- **Edit message** - Modify the AI suggestion
- **Regenerate** - Get a different AI suggestion
- **Write my own** - Start with blank textarea

### Example Generated Messages

| Context | Gesture | Generated Message |
|---------|---------|-------------------|
| Recent conflict about dishes | Hug | "I know we've been frustrated about the kitchen stuff. I love you and we'll figure it out together." |
| Partner had hard day (from chat) | Thinking of You | "Been thinking about your meeting today. You've got this, and I'm so proud of you." |
| No specific context | Kiss | "Just wanted to remind you how much I love you. You make every day better." |
| Recent makeup after fight | Hug | "I'm grateful we worked through that together. You mean everything to me." |

## Privacy & Data

- Gestures are stored with relationship_id for multi-tenancy
- Message content stored for analytics (patterns over time)
- No external sharing of gesture data
- Partner profiles used only for personalization

## Success Metrics

1. **Adoption**: % of active couples sending gestures
2. **Frequency**: Average gestures per couple per week
3. **AI Usage**: % of gestures using AI-generated messages
4. **Reciprocation**: % of gestures that receive a gesture back
5. **Time to Acknowledge**: Average time between send and acknowledgment
6. **Post-Conflict Usage**: Gestures sent within 24h of conflict resolution
