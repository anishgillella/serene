# Phase 1: Basic Messaging

Foundation phase - enables partners to send and receive text messages in real-time.

## Goals

- Partners can send text messages to each other
- Messages delivered in real-time via WebSocket
- Message history persisted and paginated
- Basic chat UI following existing patterns

---

## Tech Stack & Dependencies

### Backend Dependencies

No new dependencies required - uses existing packages:

```txt
# Already in requirements.txt
fastapi>=0.104.0
uvicorn>=0.24.0
psycopg2-binary>=2.9.9
pydantic>=2.0.0
```

### Frontend Dependencies

No new dependencies required - uses existing packages:

```json
// Already in package.json
{
  "react": "^18.3.1",
  "lucide-react": "^0.522.0",
  "react-markdown": "^10.1.0"
}
```

### Configuration Required

**Backend** (`backend/app/main.py`):
```python
# Add router imports and registrations (shown in implementation below)
```

**Frontend** (`frontend/.env`):
```bash
# Ensure this is set (should already exist)
VITE_API_URL=http://localhost:8000
```

---

## Backend Implementation

### 1. Database Migration

**File**: `backend/app/models/migrations/009_partner_messaging.sql`

```sql
-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- PARTNER CONVERSATIONS
-- One conversation per relationship
-- ============================================
CREATE TABLE IF NOT EXISTS partner_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_message_at TIMESTAMP WITH TIME ZONE,
    last_message_preview TEXT,
    message_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- One conversation per relationship
    CONSTRAINT uq_partner_conversations_relationship UNIQUE (relationship_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_partner_conversations_relationship
    ON partner_conversations(relationship_id);
CREATE INDEX IF NOT EXISTS idx_partner_conversations_last_message
    ON partner_conversations(last_message_at DESC);

-- RLS (open for MVP)
ALTER TABLE partner_conversations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public access to partner_conversations"
    ON partner_conversations FOR ALL USING (true);


-- ============================================
-- PARTNER MESSAGES
-- Individual messages between partners
-- ============================================
CREATE TABLE IF NOT EXISTS partner_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES partner_conversations(id) ON DELETE CASCADE,
    sender_id TEXT NOT NULL CHECK (sender_id IN ('partner_a', 'partner_b')),
    content TEXT NOT NULL,

    -- Message status
    status TEXT DEFAULT 'sent' CHECK (status IN ('sent', 'delivered', 'read')),
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    delivered_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,

    -- Analysis fields (populated async in Phase 4)
    sentiment_score FLOAT,
    sentiment_label TEXT CHECK (sentiment_label IN ('positive', 'neutral', 'negative', 'mixed')),
    emotions JSONB DEFAULT '[]'::jsonb,
    detected_triggers JSONB DEFAULT '[]'::jsonb,
    escalation_risk TEXT CHECK (escalation_risk IN ('low', 'medium', 'high', 'critical')),
    gottman_markers JSONB DEFAULT '{}'::jsonb,

    -- Luna intervention tracking (Phase 3)
    luna_intervened BOOLEAN DEFAULT false,
    intervention_type TEXT CHECK (intervention_type IN ('suggestion', 'warning', 'reframe')),
    intervention_accepted BOOLEAN,
    original_content TEXT,  -- stored if Luna suggestion was accepted

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Soft delete
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_partner_messages_conversation
    ON partner_messages(conversation_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_partner_messages_sender
    ON partner_messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_partner_messages_status
    ON partner_messages(status);
CREATE INDEX IF NOT EXISTS idx_partner_messages_sent_at
    ON partner_messages(sent_at DESC);

-- RLS (open for MVP)
ALTER TABLE partner_messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public access to partner_messages"
    ON partner_messages FOR ALL USING (true);


-- ============================================
-- FUNCTION: Update conversation on new message
-- ============================================
CREATE OR REPLACE FUNCTION update_conversation_on_message()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE partner_conversations
    SET
        last_message_at = NEW.sent_at,
        last_message_preview = LEFT(NEW.content, 100),
        message_count = message_count + 1,
        updated_at = NOW()
    WHERE id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_conversation_on_message
    AFTER INSERT ON partner_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_on_message();
```

### 2. Database Service Methods

**File**: `backend/app/services/db_service.py` (add these methods)

```python
# ============================================
# PARTNER MESSAGING METHODS
# ============================================

def get_or_create_partner_conversation(self, relationship_id: str) -> dict:
    """Get existing conversation or create new one for relationship."""
    with self.get_connection() as conn:
        with conn.cursor() as cur:
            # Try to get existing
            cur.execute("""
                SELECT id, relationship_id, created_at, last_message_at,
                       last_message_preview, message_count
                FROM partner_conversations
                WHERE relationship_id = %s
            """, (relationship_id,))

            row = cur.fetchone()
            if row:
                return {
                    "id": str(row[0]),
                    "relationship_id": str(row[1]),
                    "created_at": row[2].isoformat() if row[2] else None,
                    "last_message_at": row[3].isoformat() if row[3] else None,
                    "last_message_preview": row[4],
                    "message_count": row[5]
                }

            # Create new
            cur.execute("""
                INSERT INTO partner_conversations (relationship_id)
                VALUES (%s)
                RETURNING id, relationship_id, created_at
            """, (relationship_id,))

            row = cur.fetchone()
            conn.commit()

            return {
                "id": str(row[0]),
                "relationship_id": str(row[1]),
                "created_at": row[2].isoformat() if row[2] else None,
                "last_message_at": None,
                "last_message_preview": None,
                "message_count": 0
            }


def save_partner_message(
    self,
    conversation_id: str,
    sender_id: str,
    content: str,
    original_content: str = None,
    luna_intervened: bool = False,
    intervention_type: str = None
) -> dict:
    """Save a new partner message."""
    with self.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO partner_messages
                    (conversation_id, sender_id, content, original_content,
                     luna_intervened, intervention_type)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, conversation_id, sender_id, content, status,
                          sent_at, luna_intervened, original_content
            """, (
                conversation_id, sender_id, content, original_content,
                luna_intervened, intervention_type
            ))

            row = cur.fetchone()
            conn.commit()

            return {
                "id": str(row[0]),
                "conversation_id": str(row[1]),
                "sender_id": row[2],
                "content": row[3],
                "status": row[4],
                "sent_at": row[5].isoformat() if row[5] else None,
                "luna_intervened": row[6],
                "original_content": row[7]
            }


def get_partner_messages(
    self,
    conversation_id: str,
    limit: int = 50,
    before_timestamp: str = None
) -> list:
    """Get paginated messages for a conversation."""
    with self.get_connection() as conn:
        with conn.cursor() as cur:
            if before_timestamp:
                cur.execute("""
                    SELECT id, conversation_id, sender_id, content, status,
                           sent_at, delivered_at, read_at, sentiment_label,
                           emotions, escalation_risk, luna_intervened
                    FROM partner_messages
                    WHERE conversation_id = %s
                      AND sent_at < %s
                      AND deleted_at IS NULL
                    ORDER BY sent_at DESC
                    LIMIT %s
                """, (conversation_id, before_timestamp, limit))
            else:
                cur.execute("""
                    SELECT id, conversation_id, sender_id, content, status,
                           sent_at, delivered_at, read_at, sentiment_label,
                           emotions, escalation_risk, luna_intervened
                    FROM partner_messages
                    WHERE conversation_id = %s
                      AND deleted_at IS NULL
                    ORDER BY sent_at DESC
                    LIMIT %s
                """, (conversation_id, limit))

            rows = cur.fetchall()

            messages = []
            for row in rows:
                messages.append({
                    "id": str(row[0]),
                    "conversation_id": str(row[1]),
                    "sender_id": row[2],
                    "content": row[3],
                    "status": row[4],
                    "sent_at": row[5].isoformat() if row[5] else None,
                    "delivered_at": row[6].isoformat() if row[6] else None,
                    "read_at": row[7].isoformat() if row[7] else None,
                    "sentiment_label": row[8],
                    "emotions": row[9] or [],
                    "escalation_risk": row[10],
                    "luna_intervened": row[11]
                })

            # Return in chronological order
            return list(reversed(messages))


def update_message_status(
    self,
    message_id: str,
    status: str,
    timestamp_field: str = None
) -> bool:
    """Update message status (delivered, read)."""
    with self.get_connection() as conn:
        with conn.cursor() as cur:
            if timestamp_field:
                cur.execute(f"""
                    UPDATE partner_messages
                    SET status = %s, {timestamp_field} = NOW()
                    WHERE id = %s
                """, (status, message_id))
            else:
                cur.execute("""
                    UPDATE partner_messages
                    SET status = %s
                    WHERE id = %s
                """, (status, message_id))

            conn.commit()
            return cur.rowcount > 0


def get_conversation_by_relationship(self, relationship_id: str) -> dict:
    """Get conversation for a relationship."""
    with self.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, relationship_id, created_at, last_message_at,
                       last_message_preview, message_count
                FROM partner_conversations
                WHERE relationship_id = %s
            """, (relationship_id,))

            row = cur.fetchone()
            if not row:
                return None

            return {
                "id": str(row[0]),
                "relationship_id": str(row[1]),
                "created_at": row[2].isoformat() if row[2] else None,
                "last_message_at": row[3].isoformat() if row[3] else None,
                "last_message_preview": row[4],
                "message_count": row[5]
            }
```

### 3. Pydantic Models

**File**: `backend/app/models/schemas.py` (add these models)

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# ============================================
# PARTNER MESSAGING MODELS
# ============================================

class PartnerConversation(BaseModel):
    id: str
    relationship_id: str
    created_at: Optional[str] = None
    last_message_at: Optional[str] = None
    last_message_preview: Optional[str] = None
    message_count: int = 0


class PartnerMessage(BaseModel):
    id: str
    conversation_id: str
    sender_id: str  # 'partner_a' or 'partner_b'
    content: str
    status: str = 'sent'
    sent_at: Optional[str] = None
    delivered_at: Optional[str] = None
    read_at: Optional[str] = None
    sentiment_label: Optional[str] = None
    emotions: List[str] = []
    escalation_risk: Optional[str] = None
    luna_intervened: bool = False


class SendMessageRequest(BaseModel):
    conversation_id: str
    sender_id: str = Field(..., pattern='^(partner_a|partner_b)$')
    content: str = Field(..., min_length=1, max_length=5000)
    request_luna_review: bool = False


class SendMessageResponse(BaseModel):
    message: PartnerMessage
    luna_suggestion: Optional['LunaSuggestion'] = None  # Phase 3


class GetMessagesRequest(BaseModel):
    conversation_id: str
    limit: int = Field(default=50, ge=1, le=100)
    before: Optional[str] = None  # ISO timestamp for pagination


class GetMessagesResponse(BaseModel):
    messages: List[PartnerMessage]
    has_more: bool
    oldest_timestamp: Optional[str] = None
```

### 4. REST API Routes

**File**: `backend/app/routes/partner_messaging_routes.py` (create new)

```python
"""
Partner Messaging API Routes

Handles partner-to-partner messaging within Luna.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from app.services.db_service import db_service
from app.models.schemas import (
    PartnerConversation,
    PartnerMessage,
    SendMessageRequest,
    SendMessageResponse,
    GetMessagesResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/partner-messages", tags=["partner-messaging"])


@router.get("/conversation", response_model=PartnerConversation)
async def get_or_create_conversation(
    relationship_id: str = Query(..., description="Relationship UUID")
):
    """
    Get or create the conversation for a relationship.
    Each relationship has exactly one partner conversation.
    """
    try:
        conversation = db_service.get_or_create_partner_conversation(relationship_id)
        return PartnerConversation(**conversation)
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages", response_model=GetMessagesResponse)
async def get_messages(
    conversation_id: str = Query(..., description="Conversation UUID"),
    limit: int = Query(default=50, ge=1, le=100),
    before: Optional[str] = Query(default=None, description="ISO timestamp for pagination")
):
    """
    Get paginated messages for a conversation.
    Returns messages in chronological order (oldest first).
    Use 'before' parameter for pagination (pass oldest_timestamp from previous response).
    """
    try:
        messages = db_service.get_partner_messages(
            conversation_id=conversation_id,
            limit=limit + 1,  # Fetch one extra to check if more exist
            before_timestamp=before
        )

        has_more = len(messages) > limit
        if has_more:
            messages = messages[1:]  # Remove the extra one

        oldest_timestamp = messages[0]["sent_at"] if messages else None

        return GetMessagesResponse(
            messages=[PartnerMessage(**m) for m in messages],
            has_more=has_more,
            oldest_timestamp=oldest_timestamp
        )
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest):
    """
    Send a message to the partner.

    If request_luna_review is True (Phase 3), Luna will analyze the message
    and potentially suggest improvements before sending.
    """
    try:
        # For Phase 1, just save and return
        message = db_service.save_partner_message(
            conversation_id=request.conversation_id,
            sender_id=request.sender_id,
            content=request.content
        )

        # TODO Phase 3: If request_luna_review, call suggestion service

        return SendMessageResponse(
            message=PartnerMessage(**message),
            luna_suggestion=None
        )
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/messages/{message_id}/delivered")
async def mark_delivered(message_id: str):
    """Mark a message as delivered."""
    try:
        success = db_service.update_message_status(
            message_id=message_id,
            status="delivered",
            timestamp_field="delivered_at"
        )
        if not success:
            raise HTTPException(status_code=404, detail="Message not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking delivered: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/messages/{message_id}/read")
async def mark_read(message_id: str):
    """Mark a message as read."""
    try:
        success = db_service.update_message_status(
            message_id=message_id,
            status="read",
            timestamp_field="read_at"
        )
        if not success:
            raise HTTPException(status_code=404, detail="Message not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking read: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### 5. WebSocket for Real-Time

**File**: `backend/app/routes/partner_messaging_websocket.py` (create new)

```python
"""
Partner Messaging WebSocket

Real-time message delivery between partners.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Set
import json
import logging
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()

# Active connections: {conversation_id: {partner_id: websocket}}
active_connections: Dict[str, Dict[str, WebSocket]] = {}


class ConnectionManager:
    """Manages WebSocket connections for partner messaging."""

    def __init__(self):
        self.connections: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        conversation_id: str,
        partner_id: str
    ):
        """Accept and store a new connection."""
        await websocket.accept()

        if conversation_id not in self.connections:
            self.connections[conversation_id] = {}

        self.connections[conversation_id][partner_id] = websocket
        logger.info(f"Partner {partner_id} connected to conversation {conversation_id}")

    def disconnect(self, conversation_id: str, partner_id: str):
        """Remove a connection."""
        if conversation_id in self.connections:
            if partner_id in self.connections[conversation_id]:
                del self.connections[conversation_id][partner_id]
                logger.info(f"Partner {partner_id} disconnected from {conversation_id}")

            # Clean up empty conversations
            if not self.connections[conversation_id]:
                del self.connections[conversation_id]

    async def send_to_partner(
        self,
        conversation_id: str,
        recipient_partner_id: str,
        message: dict
    ):
        """Send a message to a specific partner."""
        if conversation_id in self.connections:
            if recipient_partner_id in self.connections[conversation_id]:
                websocket = self.connections[conversation_id][recipient_partner_id]
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to {recipient_partner_id}: {e}")

    async def broadcast_to_conversation(
        self,
        conversation_id: str,
        message: dict,
        exclude_partner: str = None
    ):
        """Broadcast a message to all partners in a conversation."""
        if conversation_id in self.connections:
            for partner_id, websocket in self.connections[conversation_id].items():
                if partner_id != exclude_partner:
                    try:
                        await websocket.send_json(message)
                    except Exception as e:
                        logger.error(f"Error broadcasting to {partner_id}: {e}")

    def get_other_partner(self, partner_id: str) -> str:
        """Get the other partner's ID."""
        return "partner_b" if partner_id == "partner_a" else "partner_a"


manager = ConnectionManager()


@router.websocket("/api/realtime/partner-chat")
async def websocket_partner_chat(
    websocket: WebSocket,
    conversation_id: str = Query(...),
    partner_id: str = Query(...)
):
    """
    WebSocket endpoint for real-time partner messaging.

    Connect with: ws://host/api/realtime/partner-chat?conversation_id=xxx&partner_id=partner_a

    Client -> Server messages:
    - {"type": "message", "content": "Hello"}
    - {"type": "typing", "is_typing": true}
    - {"type": "read", "message_id": "xxx"}

    Server -> Client messages:
    - {"type": "new_message", "message": {...}}
    - {"type": "typing", "partner_id": "partner_b", "is_typing": true}
    - {"type": "read_receipt", "message_id": "xxx", "read_at": "..."}
    - {"type": "delivered", "message_id": "xxx"}
    - {"type": "error", "message": "..."}
    """
    from app.services.db_service import db_service

    await manager.connect(websocket, conversation_id, partner_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "message":
                # Save message to database
                content = data.get("content", "").strip()
                if not content:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Message content cannot be empty"
                    })
                    continue

                message = db_service.save_partner_message(
                    conversation_id=conversation_id,
                    sender_id=partner_id,
                    content=content
                )

                # Send confirmation to sender
                await websocket.send_json({
                    "type": "message_sent",
                    "message": message
                })

                # Send to recipient
                other_partner = manager.get_other_partner(partner_id)
                await manager.send_to_partner(
                    conversation_id,
                    other_partner,
                    {
                        "type": "new_message",
                        "message": message
                    }
                )

                # If recipient is connected, mark as delivered
                if conversation_id in manager.connections:
                    if other_partner in manager.connections[conversation_id]:
                        db_service.update_message_status(
                            message_id=message["id"],
                            status="delivered",
                            timestamp_field="delivered_at"
                        )
                        await websocket.send_json({
                            "type": "delivered",
                            "message_id": message["id"]
                        })

            elif msg_type == "typing":
                # Broadcast typing indicator to other partner
                is_typing = data.get("is_typing", False)
                other_partner = manager.get_other_partner(partner_id)
                await manager.send_to_partner(
                    conversation_id,
                    other_partner,
                    {
                        "type": "typing",
                        "partner_id": partner_id,
                        "is_typing": is_typing
                    }
                )

            elif msg_type == "read":
                # Mark message as read
                message_id = data.get("message_id")
                if message_id:
                    db_service.update_message_status(
                        message_id=message_id,
                        status="read",
                        timestamp_field="read_at"
                    )

                    # Notify sender their message was read
                    other_partner = manager.get_other_partner(partner_id)
                    await manager.send_to_partner(
                        conversation_id,
                        other_partner,
                        {
                            "type": "read_receipt",
                            "message_id": message_id,
                            "read_by": partner_id
                        }
                    )

    except WebSocketDisconnect:
        manager.disconnect(conversation_id, partner_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(conversation_id, partner_id)
```

### 6. Register Routes in main.py

**File**: `backend/app/main.py` (add these imports and includes)

```python
# Add imports
from app.routes.partner_messaging_routes import router as partner_messaging_router
from app.routes.partner_messaging_websocket import router as partner_ws_router

# Add router registrations (near other router includes)
app.include_router(partner_messaging_router)
app.include_router(partner_ws_router)
```

---

## Frontend Implementation

### 1. Partner Chat Page

**File**: `frontend/src/pages/PartnerChat.tsx`

```tsx
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useRelationship } from '@/contexts/RelationshipContext';
import ConversationView from '@/components/partner-chat/ConversationView';
import MessageInput from '@/components/partner-chat/MessageInput';
import { Loader2 } from 'lucide-react';

interface Message {
    id: string;
    conversation_id: string;
    sender_id: string;
    content: string;
    status: string;
    sent_at: string;
    delivered_at?: string;
    read_at?: string;
}

interface Conversation {
    id: string;
    relationship_id: string;
    last_message_at?: string;
    message_count: number;
}

const PartnerChat: React.FC = () => {
    const { relationshipId, partnerId, partnerNames } = useRelationship();
    const [conversation, setConversation] = useState<Conversation | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [partnerTyping, setPartnerTyping] = useState(false);

    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    // Get or create conversation
    useEffect(() => {
        const initConversation = async () => {
            if (!relationshipId) return;

            try {
                const response = await fetch(
                    `${apiUrl}/api/partner-messages/conversation?relationship_id=${relationshipId}`
                );
                if (!response.ok) throw new Error('Failed to load conversation');

                const data = await response.json();
                setConversation(data);
            } catch (err) {
                setError('Failed to load conversation');
                console.error(err);
            }
        };

        initConversation();
    }, [relationshipId, apiUrl]);

    // Load messages
    useEffect(() => {
        const loadMessages = async () => {
            if (!conversation?.id) return;

            try {
                const response = await fetch(
                    `${apiUrl}/api/partner-messages/messages?conversation_id=${conversation.id}&limit=50`
                );
                if (!response.ok) throw new Error('Failed to load messages');

                const data = await response.json();
                setMessages(data.messages);
            } catch (err) {
                setError('Failed to load messages');
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        loadMessages();
    }, [conversation?.id, apiUrl]);

    // WebSocket connection
    useEffect(() => {
        if (!conversation?.id || !partnerId) return;

        const wsUrl = apiUrl.replace('http://', 'ws://').replace('https://', 'wss://');
        const ws = new WebSocket(
            `${wsUrl}/api/realtime/partner-chat?conversation_id=${conversation.id}&partner_id=${partnerId}`
        );

        ws.onopen = () => {
            setIsConnected(true);
            console.log('WebSocket connected');
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            switch (data.type) {
                case 'new_message':
                    setMessages(prev => [...prev, data.message]);
                    break;
                case 'message_sent':
                    setMessages(prev => [...prev, data.message]);
                    break;
                case 'typing':
                    setPartnerTyping(data.is_typing);
                    break;
                case 'delivered':
                    setMessages(prev => prev.map(m =>
                        m.id === data.message_id
                            ? { ...m, status: 'delivered' }
                            : m
                    ));
                    break;
                case 'read_receipt':
                    setMessages(prev => prev.map(m =>
                        m.id === data.message_id
                            ? { ...m, status: 'read' }
                            : m
                    ));
                    break;
            }
        };

        ws.onclose = () => {
            setIsConnected(false);
            console.log('WebSocket disconnected');
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        wsRef.current = ws;

        return () => {
            ws.close();
        };
    }, [conversation?.id, partnerId, apiUrl]);

    const handleSendMessage = useCallback((content: string) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
            setError('Not connected. Please refresh.');
            return;
        }

        wsRef.current.send(JSON.stringify({
            type: 'message',
            content
        }));
    }, []);

    const handleTyping = useCallback((isTyping: boolean) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

        wsRef.current.send(JSON.stringify({
            type: 'typing',
            is_typing: isTyping
        }));
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <Loader2 className="animate-spin" size={32} />
            </div>
        );
    }

    const otherPartnerName = partnerId === 'partner_a'
        ? partnerNames?.partner_b
        : partnerNames?.partner_a;

    return (
        <div className="flex flex-col h-full bg-surface-base">
            {/* Header */}
            <div className="p-4 border-b border-border-subtle bg-surface-card">
                <h2 className="font-semibold text-text-primary">
                    {otherPartnerName || 'Your Partner'}
                </h2>
                <p className="text-xs text-text-tertiary">
                    {isConnected ? 'Connected' : 'Connecting...'}
                </p>
            </div>

            {/* Messages */}
            <ConversationView
                messages={messages}
                currentPartnerId={partnerId}
                partnerTyping={partnerTyping}
            />

            {/* Input */}
            <MessageInput
                onSend={handleSendMessage}
                onTyping={handleTyping}
                disabled={!isConnected}
            />
        </div>
    );
};

export default PartnerChat;
```

### 2. Additional Frontend Components

See the complete component implementations in the appendix of this document or implement following the patterns from `LunaChatPanel.tsx`.

**Components needed**:
- `frontend/src/components/partner-chat/ConversationView.tsx`
- `frontend/src/components/partner-chat/MessageBubble.tsx`
- `frontend/src/components/partner-chat/MessageInput.tsx`

---

## Testing Checklist

### Backend Tests
- [ ] Database migration runs without errors
- [ ] `GET /conversation` creates new conversation if none exists
- [ ] `GET /conversation` returns existing conversation
- [ ] `POST /send` saves message correctly
- [ ] `GET /messages` returns paginated messages
- [ ] `GET /messages?before=timestamp` paginates correctly
- [ ] WebSocket connects successfully
- [ ] WebSocket broadcasts messages to partner
- [ ] WebSocket handles disconnection gracefully

### Frontend Tests
- [ ] Chat page loads conversation
- [ ] Messages display in chronological order
- [ ] New messages appear in real-time
- [ ] Sending message shows immediately
- [ ] Scroll to bottom on new message
- [ ] Load more messages on scroll up

### Integration Tests
- [ ] Partner A sends, Partner B receives in real-time
- [ ] Message persists after page refresh
- [ ] Reconnection after network interruption
