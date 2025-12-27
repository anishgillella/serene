# Priority 1: Text Messaging

Real-time text messaging between partners with full analysis capabilities.

## Overview

Text messaging is the foundation of the communication platform. It provides:
- Instant message delivery
- Read receipts and typing indicators
- Push notifications
- Full message history
- Real-time tone/sentiment analysis

## Tech Stack

| Component | Technology | Why |
|-----------|------------|-----|
| Real-time sync | Supabase Realtime | Built-in PostgreSQL, easy setup, scales well |
| Push notifications | Firebase Cloud Messaging (FCM) + APNs | Cross-platform, reliable |
| Message storage | PostgreSQL (via Supabase) | Structured queries, full-text search |
| Encryption | Signal Protocol or libsodium | End-to-end encryption |

### Alternative: Firebase
- Firestore for real-time sync
- Simpler setup but less SQL flexibility
- Good for MVP, may need migration later

## Database Schema

```sql
-- Conversations (one per couple)
CREATE TABLE conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  relationship_id UUID REFERENCES relationships(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  last_message_at TIMESTAMPTZ,
  last_message_preview TEXT
);

-- Messages
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id),
  sender_id UUID REFERENCES users(id),
  content TEXT NOT NULL,
  content_type TEXT DEFAULT 'text', -- 'text', 'image', 'voice', 'link'

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  delivered_at TIMESTAMPTZ,
  read_at TIMESTAMPTZ,

  -- Analysis results (populated async)
  sentiment_score FLOAT,        -- -1 to 1
  emotion_labels JSONB,         -- {angry: 0.2, sad: 0.1, ...}
  trigger_detected BOOLEAN,
  escalation_risk FLOAT,        -- 0 to 1

  -- For replies/threads
  reply_to_id UUID REFERENCES messages(id),

  -- Soft delete
  deleted_at TIMESTAMPTZ
);

-- Typing indicators (ephemeral, use Realtime presence)
-- Read receipts (update read_at on messages table)

-- Indexes
CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at DESC);
CREATE INDEX idx_messages_sender ON messages(sender_id);
CREATE INDEX idx_messages_unread ON messages(conversation_id, read_at) WHERE read_at IS NULL;
```

## API Endpoints

```
POST   /api/messages                    Send a message
GET    /api/messages?conversation_id=x  Get message history (paginated)
PATCH  /api/messages/:id/read           Mark message as read
DELETE /api/messages/:id                Soft delete message

GET    /api/conversations               List conversations
GET    /api/conversations/:id           Get conversation with recent messages

WS     /api/realtime                    WebSocket for real-time updates
```

## Real-time Flow

```
Partner A types message
        │
        ▼
┌───────────────────┐
│  Frontend sends   │
│  via WebSocket    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Backend saves    │
│  to PostgreSQL    │
└─────────┬─────────┘
          │
          ├──────────────────────────┐
          │                          │
          ▼                          ▼
┌───────────────────┐    ┌───────────────────┐
│ Supabase Realtime │    │ Analysis Pipeline │
│ broadcasts to     │    │ (async worker)    │
│ Partner B         │    │ - Sentiment       │
└───────────────────┘    │ - Triggers        │
                         │ - Escalation      │
                         └───────────────────┘
```

## Frontend Components

### ChatScreen
```tsx
// Main chat interface
- Message list (virtualized for performance)
- Input bar with send button
- Typing indicator
- Pull-to-load-more history
```

### MessageBubble
```tsx
// Individual message display
- Sender alignment (left/right)
- Timestamp
- Read receipt indicator
- Reply preview (if replying)
- Long-press for reactions/reply/delete
```

### ChatInput
```tsx
// Message composition
- Text input with auto-resize
- Send button
- Attachment button (for media)
- Voice message button
- Typing indicator broadcast
```

## Analysis Pipeline

Every message triggers async analysis:

```python
async def analyze_message(message_id: str):
    message = await get_message(message_id)
    conversation = await get_recent_context(message.conversation_id, limit=10)

    # 1. Sentiment analysis
    sentiment = await analyze_sentiment(message.content)

    # 2. Emotion detection
    emotions = await detect_emotions(message.content)

    # 3. Trigger detection (based on partner's known triggers)
    partner_triggers = await get_partner_triggers(message.recipient_id)
    trigger_detected = await check_triggers(message.content, partner_triggers)

    # 4. Escalation risk (based on conversation context)
    escalation_risk = await assess_escalation(conversation, message)

    # 5. Update message with analysis
    await update_message_analysis(message_id, {
        "sentiment_score": sentiment,
        "emotion_labels": emotions,
        "trigger_detected": trigger_detected,
        "escalation_risk": escalation_risk
    })

    # 6. If high escalation risk, notify Luna for potential intervention
    if escalation_risk > 0.7:
        await trigger_luna_intervention(message.conversation_id)
```

## Luna Intervention

When escalation is detected, Luna can:

1. **Passive**: Add insight to dashboard ("Tension detected in recent conversation")
2. **Gentle nudge**: Push notification ("Luna noticed things getting heated. Need a moment?")
3. **Active**: In-app prompt ("Would you like me to help rephrase that?")
4. **Emergency**: Suggest cool-down break

Intervention level is configurable by user preferences.

## Push Notifications

```typescript
// Notification payload
{
  title: "Partner Name",
  body: "Message preview...",
  data: {
    type: "new_message",
    conversation_id: "xxx",
    message_id: "yyy"
  }
}
```

Requirements:
- iOS: APNs certificate, request permission
- Android: FCM setup, notification channel
- Web: Service worker for background notifications

## Encryption (E2E)

For sensitive conversations:

1. Generate key pair per device
2. Exchange public keys during pairing
3. Encrypt message content client-side before sending
4. Server stores encrypted blob
5. Recipient decrypts with private key

Trade-off: E2E encryption prevents server-side analysis. Options:
- Analyze on-device before encryption
- User opts into server analysis (decrypted for analysis, then deleted)
- Hybrid: Metadata analyzed, content encrypted

## Implementation Steps

### Phase 1: Basic Chat (MVP)
- [ ] Database schema setup
- [ ] Send/receive messages API
- [ ] Supabase Realtime subscription
- [ ] Basic chat UI
- [ ] Message history with pagination

### Phase 2: Polish
- [ ] Typing indicators
- [ ] Read receipts
- [ ] Push notifications
- [ ] Offline queue (send when back online)

### Phase 3: Analysis
- [ ] Async analysis pipeline
- [ ] Sentiment scoring
- [ ] Trigger detection
- [ ] Escalation alerts

### Phase 4: Luna Integration
- [ ] Intervention triggers
- [ ] Suggested responses
- [ ] Cool-down prompts

## Testing Considerations

- Simulate slow network (message queuing)
- Test with 10,000+ messages (performance)
- Multi-device sync (same user, multiple devices)
- Notification delivery rates
- Message ordering (handle out-of-order delivery)
