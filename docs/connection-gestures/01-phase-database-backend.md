# Phase 1: Database & Backend

Foundation phase - database schema, API endpoints, and service methods for connection gestures.

## Goals

- Create `connection_gestures` table with proper schema
- Implement CRUD operations in db_service
- Create REST API endpoints for sending/acknowledging gestures
- Add WebSocket support for real-time delivery
- Add Pydantic models for request/response validation

---

## Database Migration

**File**: `backend/app/models/migrations/011_connection_gestures.sql`

```sql
-- ============================================
-- CONNECTION GESTURES SCHEMA
-- Migration: 011_connection_gestures
-- Description: Partner-to-partner emotional gestures
-- ============================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- TABLE: connection_gestures
-- Emotional gestures between partners
-- ============================================
CREATE TABLE IF NOT EXISTS connection_gestures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,

    -- Gesture details
    gesture_type TEXT NOT NULL CHECK (gesture_type IN ('hug', 'kiss', 'thinking_of_you')),
    sent_by TEXT NOT NULL CHECK (sent_by IN ('partner_a', 'partner_b')),

    -- Message content
    message TEXT,  -- Personalized note (max 280 chars enforced in API)
    ai_generated BOOLEAN DEFAULT false,  -- Whether message was AI-generated
    ai_context_used JSONB DEFAULT '{}'::jsonb,  -- What context AI used (for debugging)

    -- Timestamps
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    delivered_at TIMESTAMP WITH TIME ZONE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by TEXT CHECK (acknowledged_by IN ('partner_a', 'partner_b')),

    -- Response tracking
    response_gesture_id UUID REFERENCES connection_gestures(id),

    -- Metadata for analytics
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================

-- Primary query: get gestures for a relationship
CREATE INDEX IF NOT EXISTS idx_gestures_relationship
    ON connection_gestures(relationship_id);

-- Sender filtering
CREATE INDEX IF NOT EXISTS idx_gestures_sent_by
    ON connection_gestures(sent_by);

-- Type filtering for analytics
CREATE INDEX IF NOT EXISTS idx_gestures_type
    ON connection_gestures(gesture_type);

-- Chronological ordering
CREATE INDEX IF NOT EXISTS idx_gestures_sent_at
    ON connection_gestures(sent_at DESC);

-- Pending gestures (unacknowledged) - partial index
CREATE INDEX IF NOT EXISTS idx_gestures_unacknowledged
    ON connection_gestures(relationship_id, sent_by, sent_at)
    WHERE acknowledged_at IS NULL;

-- Analytics queries
CREATE INDEX IF NOT EXISTS idx_gestures_analytics
    ON connection_gestures(relationship_id, gesture_type, sent_at DESC);

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================

ALTER TABLE connection_gestures ENABLE ROW LEVEL SECURITY;

-- Open policy for MVP (will be tightened with multi-tenancy)
DROP POLICY IF EXISTS "Allow public access to connection_gestures" ON connection_gestures;
CREATE POLICY "Allow public access to connection_gestures"
    ON connection_gestures FOR ALL USING (true);
```

---

## Pydantic Models

**File**: `backend/app/models/schemas.py` (add these models)

```python
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

# ============================================
# CONNECTION GESTURES MODELS
# ============================================

class GestureType(str, Enum):
    """Types of connection gestures"""
    HUG = "hug"
    KISS = "kiss"
    THINKING_OF_YOU = "thinking_of_you"


class ConnectionGesture(BaseModel):
    """A connection gesture between partners"""
    id: str
    relationship_id: str
    gesture_type: GestureType
    sent_by: str  # 'partner_a' or 'partner_b'
    message: Optional[str] = None
    ai_generated: bool = False
    sent_at: Optional[str] = None
    delivered_at: Optional[str] = None
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    response_gesture_id: Optional[str] = None


class SendGestureRequest(BaseModel):
    """Request to send a connection gesture"""
    relationship_id: str
    gesture_type: GestureType
    sender_id: str = Field(..., pattern='^(partner_a|partner_b)$')
    message: Optional[str] = Field(default=None, max_length=280)
    ai_generated: bool = False


class SendGestureResponse(BaseModel):
    """Response after sending a gesture"""
    gesture: ConnectionGesture
    recipient_online: bool


class AcknowledgeGestureRequest(BaseModel):
    """Request to acknowledge a received gesture"""
    gesture_id: str
    acknowledged_by: str = Field(..., pattern='^(partner_a|partner_b)$')
    send_back: bool = False
    send_back_type: Optional[GestureType] = None
    send_back_message: Optional[str] = Field(default=None, max_length=280)


class AcknowledgeGestureResponse(BaseModel):
    """Response after acknowledging a gesture"""
    acknowledged: bool
    response_gesture: Optional[ConnectionGesture] = None


class PendingGesturesResponse(BaseModel):
    """Response with pending gestures for a partner"""
    gestures: List[ConnectionGesture]
    count: int


class GenerateGestureMessageRequest(BaseModel):
    """Request to generate AI message for a gesture"""
    relationship_id: str
    sender_id: str = Field(..., pattern='^(partner_a|partner_b)$')
    gesture_type: GestureType


class GenerateGestureMessageResponse(BaseModel):
    """Response with AI-generated message"""
    message: str
    context_used: List[str]  # What context sources were used
```

---

## Database Service Methods

**File**: `backend/app/services/db_service.py` (add these methods)

```python
# ============================================
# CONNECTION GESTURES METHODS
# ============================================

def save_gesture(
    self,
    relationship_id: str,
    gesture_type: str,
    sent_by: str,
    message: str = None,
    ai_generated: bool = False,
    ai_context_used: dict = None
) -> Dict[str, Any]:
    """Save a new connection gesture."""
    try:
        with self.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    INSERT INTO connection_gestures
                        (relationship_id, gesture_type, sent_by, message,
                         ai_generated, ai_context_used)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, relationship_id, gesture_type, sent_by,
                              message, ai_generated, sent_at, delivered_at,
                              acknowledged_at, acknowledged_by, response_gesture_id
                """, (
                    relationship_id, gesture_type, sent_by, message,
                    ai_generated, json.dumps(ai_context_used or {})
                ))

                row = cursor.fetchone()
                conn.commit()

                return {
                    "id": str(row["id"]),
                    "relationship_id": str(row["relationship_id"]),
                    "gesture_type": row["gesture_type"],
                    "sent_by": row["sent_by"],
                    "message": row["message"],
                    "ai_generated": row["ai_generated"],
                    "sent_at": row["sent_at"].isoformat() if row["sent_at"] else None,
                    "delivered_at": row["delivered_at"].isoformat() if row["delivered_at"] else None,
                    "acknowledged_at": row["acknowledged_at"].isoformat() if row["acknowledged_at"] else None,
                    "acknowledged_by": row["acknowledged_by"],
                    "response_gesture_id": str(row["response_gesture_id"]) if row["response_gesture_id"] else None
                }
    except Exception as e:
        print(f"Error saving gesture: {e}")
        raise e


def mark_gesture_delivered(self, gesture_id: str) -> bool:
    """Mark a gesture as delivered."""
    try:
        with self.get_db_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE connection_gestures
                    SET delivered_at = NOW()
                    WHERE id = %s AND delivered_at IS NULL
                """, (gesture_id,))
                conn.commit()
                return cursor.rowcount > 0
    except Exception as e:
        print(f"Error marking gesture delivered: {e}")
        return False


def acknowledge_gesture(
    self,
    gesture_id: str,
    acknowledged_by: str,
    response_gesture_id: str = None
) -> bool:
    """Mark a gesture as acknowledged, optionally linking a response gesture."""
    try:
        with self.get_db_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE connection_gestures
                    SET acknowledged_at = NOW(),
                        acknowledged_by = %s,
                        response_gesture_id = %s
                    WHERE id = %s AND acknowledged_at IS NULL
                """, (acknowledged_by, response_gesture_id, gesture_id))
                conn.commit()
                return cursor.rowcount > 0
    except Exception as e:
        print(f"Error acknowledging gesture: {e}")
        return False


def get_pending_gestures(
    self,
    relationship_id: str,
    partner_id: str
) -> List[Dict[str, Any]]:
    """Get all unacknowledged gestures sent TO a specific partner."""
    try:
        with self.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, relationship_id, gesture_type, sent_by,
                           message, ai_generated, sent_at, delivered_at
                    FROM connection_gestures
                    WHERE relationship_id = %s
                      AND sent_by != %s
                      AND acknowledged_at IS NULL
                    ORDER BY sent_at ASC
                """, (relationship_id, partner_id))

                gestures = []
                for row in cursor.fetchall():
                    gestures.append({
                        "id": str(row["id"]),
                        "relationship_id": str(row["relationship_id"]),
                        "gesture_type": row["gesture_type"],
                        "sent_by": row["sent_by"],
                        "message": row["message"],
                        "ai_generated": row["ai_generated"],
                        "sent_at": row["sent_at"].isoformat() if row["sent_at"] else None,
                        "delivered_at": row["delivered_at"].isoformat() if row["delivered_at"] else None
                    })
                return gestures
    except Exception as e:
        print(f"Error getting pending gestures: {e}")
        return []


def get_gesture_by_id(self, gesture_id: str) -> Optional[Dict[str, Any]]:
    """Get a gesture by its ID."""
    try:
        with self.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, relationship_id, gesture_type, sent_by,
                           message, ai_generated, sent_at, delivered_at,
                           acknowledged_at, acknowledged_by, response_gesture_id
                    FROM connection_gestures
                    WHERE id = %s
                """, (gesture_id,))

                row = cursor.fetchone()
                if not row:
                    return None

                return {
                    "id": str(row["id"]),
                    "relationship_id": str(row["relationship_id"]),
                    "gesture_type": row["gesture_type"],
                    "sent_by": row["sent_by"],
                    "message": row["message"],
                    "ai_generated": row["ai_generated"],
                    "sent_at": row["sent_at"].isoformat() if row["sent_at"] else None,
                    "delivered_at": row["delivered_at"].isoformat() if row["delivered_at"] else None,
                    "acknowledged_at": row["acknowledged_at"].isoformat() if row["acknowledged_at"] else None,
                    "acknowledged_by": row["acknowledged_by"],
                    "response_gesture_id": str(row["response_gesture_id"]) if row["response_gesture_id"] else None
                }
    except Exception as e:
        print(f"Error getting gesture: {e}")
        return None


def get_recent_gestures(
    self,
    relationship_id: str,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Get recent gestures for a relationship."""
    try:
        with self.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, relationship_id, gesture_type, sent_by,
                           message, ai_generated, sent_at, acknowledged_at
                    FROM connection_gestures
                    WHERE relationship_id = %s
                    ORDER BY sent_at DESC
                    LIMIT %s
                """, (relationship_id, limit))

                return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error getting recent gestures: {e}")
        return []
```

---

## API Routes

**File**: `backend/app/routes/gestures_routes.py` (create new)

```python
"""
Connection Gestures API Routes

Handles emotional gesture sending and receiving between partners.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging
import asyncio

from app.services.db_service import db_service
from app.models.schemas import (
    ConnectionGesture,
    SendGestureRequest,
    SendGestureResponse,
    AcknowledgeGestureRequest,
    AcknowledgeGestureResponse,
    PendingGesturesResponse
)

# Import WebSocket manager for real-time delivery
from app.routes.partner_messaging_websocket import manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/gestures", tags=["gestures"])


@router.post("/send", response_model=SendGestureResponse)
async def send_gesture(request: SendGestureRequest):
    """
    Send a connection gesture to your partner.

    Gesture types:
    - hug: A warm virtual hug
    - kiss: A loving kiss
    - thinking_of_you: Let them know they're on your mind

    Optionally include a personalized message (max 280 chars).
    """
    try:
        # Save gesture to database
        gesture = db_service.save_gesture(
            relationship_id=request.relationship_id,
            gesture_type=request.gesture_type.value,
            sent_by=request.sender_id,
            message=request.message,
            ai_generated=request.ai_generated
        )

        # Determine recipient
        recipient_id = "partner_b" if request.sender_id == "partner_a" else "partner_a"

        # Get conversation for this relationship to check WebSocket connection
        conversation = db_service.get_or_create_partner_conversation(request.relationship_id)
        conversation_id = conversation["id"]

        # Check if recipient is online and send real-time notification
        recipient_online = manager.is_partner_connected(conversation_id, recipient_id)

        if recipient_online:
            # Send gesture via WebSocket for instant delivery
            await manager.send_to_partner(
                conversation_id,
                recipient_id,
                {
                    "type": "gesture_received",
                    "gesture": gesture
                }
            )
            # Mark as delivered
            db_service.mark_gesture_delivered(gesture["id"])

        return SendGestureResponse(
            gesture=ConnectionGesture(**gesture),
            recipient_online=recipient_online
        )
    except Exception as e:
        logger.error(f"Error sending gesture: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/acknowledge", response_model=AcknowledgeGestureResponse)
async def acknowledge_gesture(request: AcknowledgeGestureRequest):
    """
    Acknowledge a received gesture.

    Optionally send a gesture back in the same request.
    """
    try:
        # Get the original gesture to find relationship_id
        original_gesture = db_service.get_gesture_by_id(request.gesture_id)
        if not original_gesture:
            raise HTTPException(status_code=404, detail="Gesture not found")

        response_gesture = None
        response_gesture_id = None

        # If sending back, create the response gesture first
        if request.send_back and request.send_back_type:
            response_data = db_service.save_gesture(
                relationship_id=original_gesture["relationship_id"],
                gesture_type=request.send_back_type.value,
                sent_by=request.acknowledged_by,
                message=request.send_back_message
            )
            response_gesture_id = response_data["id"]
            response_gesture = ConnectionGesture(**response_data)

            # Send the response gesture via WebSocket
            conversation = db_service.get_or_create_partner_conversation(
                original_gesture["relationship_id"]
            )
            recipient_id = original_gesture["sent_by"]

            if manager.is_partner_connected(conversation["id"], recipient_id):
                await manager.send_to_partner(
                    conversation["id"],
                    recipient_id,
                    {
                        "type": "gesture_received",
                        "gesture": response_data
                    }
                )
                db_service.mark_gesture_delivered(response_gesture_id)

        # Acknowledge the original gesture
        success = db_service.acknowledge_gesture(
            gesture_id=request.gesture_id,
            acknowledged_by=request.acknowledged_by,
            response_gesture_id=response_gesture_id
        )

        # Notify sender that their gesture was acknowledged
        conversation = db_service.get_or_create_partner_conversation(
            original_gesture["relationship_id"]
        )
        sender_id = original_gesture["sent_by"]

        if manager.is_partner_connected(conversation["id"], sender_id):
            await manager.send_to_partner(
                conversation["id"],
                sender_id,
                {
                    "type": "gesture_acknowledged",
                    "gesture_id": request.gesture_id,
                    "acknowledged_by": request.acknowledged_by,
                    "response_gesture": response_gesture.model_dump() if response_gesture else None
                }
            )

        return AcknowledgeGestureResponse(
            acknowledged=success,
            response_gesture=response_gesture
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging gesture: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending", response_model=PendingGesturesResponse)
async def get_pending_gestures(
    relationship_id: str = Query(...),
    partner_id: str = Query(..., pattern='^(partner_a|partner_b)$')
):
    """
    Get all pending (unacknowledged) gestures for a partner.

    Call this on app load to show any gestures received while offline.
    """
    try:
        gestures = db_service.get_pending_gestures(relationship_id, partner_id)
        return PendingGesturesResponse(
            gestures=[ConnectionGesture(**g) for g in gestures],
            count=len(gestures)
        )
    except Exception as e:
        logger.error(f"Error getting pending gestures: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{gesture_id}", response_model=ConnectionGesture)
async def get_gesture(gesture_id: str):
    """Get a specific gesture by ID."""
    try:
        gesture = db_service.get_gesture_by_id(gesture_id)
        if not gesture:
            raise HTTPException(status_code=404, detail="Gesture not found")
        return ConnectionGesture(**gesture)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting gesture: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## WebSocket Integration

**File**: `backend/app/routes/partner_messaging_websocket.py` (add to existing)

Add gesture handling to the WebSocket message handler. In the `websocket_partner_chat` function, add a new case:

```python
# Add this case in the message type switch
elif msg_type == "gesture":
    # Handle gesture sent via WebSocket (alternative to REST)
    gesture_type = data.get("gesture_type")
    message = data.get("message")
    ai_generated = data.get("ai_generated", False)

    if gesture_type not in ["hug", "kiss", "thinking_of_you"]:
        await websocket.send_json({
            "type": "error",
            "message": "Invalid gesture type"
        })
        continue

    try:
        # Save gesture
        gesture = await asyncio.to_thread(
            db_service.save_gesture,
            relationship_id=relationship_id,
            gesture_type=gesture_type,
            sent_by=partner_id,
            message=message,
            ai_generated=ai_generated
        )

        # Confirm to sender
        await websocket.send_json({
            "type": "gesture_sent",
            "gesture": gesture
        })

        # Send to recipient
        other_partner = manager.get_other_partner(partner_id)
        await manager.send_to_partner(
            conversation_id,
            other_partner,
            {
                "type": "gesture_received",
                "gesture": gesture
            }
        )

        # Mark as delivered if recipient is online
        if manager.is_partner_connected(conversation_id, other_partner):
            asyncio.create_task(asyncio.to_thread(
                db_service.mark_gesture_delivered,
                gesture["id"]
            ))

    except Exception as e:
        logger.error(f"Error saving gesture: {e}")
        await websocket.send_json({
            "type": "error",
            "message": "Failed to send gesture"
        })

elif msg_type == "gesture_acknowledge":
    # Handle gesture acknowledgment via WebSocket
    gesture_id = data.get("gesture_id")
    send_back = data.get("send_back", False)
    send_back_type = data.get("send_back_type")
    send_back_message = data.get("send_back_message")

    try:
        original_gesture = await asyncio.to_thread(
            db_service.get_gesture_by_id,
            gesture_id
        )

        if not original_gesture:
            await websocket.send_json({
                "type": "error",
                "message": "Gesture not found"
            })
            continue

        response_gesture_id = None
        response_gesture = None

        # Create response gesture if sending back
        if send_back and send_back_type:
            response_gesture = await asyncio.to_thread(
                db_service.save_gesture,
                relationship_id=relationship_id,
                gesture_type=send_back_type,
                sent_by=partner_id,
                message=send_back_message
            )
            response_gesture_id = response_gesture["id"]

            # Send response to original sender
            other_partner = manager.get_other_partner(partner_id)
            await manager.send_to_partner(
                conversation_id,
                other_partner,
                {
                    "type": "gesture_received",
                    "gesture": response_gesture
                }
            )

        # Acknowledge original gesture
        await asyncio.to_thread(
            db_service.acknowledge_gesture,
            gesture_id=gesture_id,
            acknowledged_by=partner_id,
            response_gesture_id=response_gesture_id
        )

        # Notify original sender
        other_partner = manager.get_other_partner(partner_id)
        await manager.send_to_partner(
            conversation_id,
            other_partner,
            {
                "type": "gesture_acknowledged",
                "gesture_id": gesture_id,
                "acknowledged_by": partner_id,
                "response_gesture": response_gesture
            }
        )

        # Confirm to acknowledger
        await websocket.send_json({
            "type": "gesture_acknowledged_confirm",
            "gesture_id": gesture_id,
            "response_gesture": response_gesture
        })

    except Exception as e:
        logger.error(f"Error acknowledging gesture: {e}")
        await websocket.send_json({
            "type": "error",
            "message": "Failed to acknowledge gesture"
        })
```

---

## Register Routes

**File**: `backend/app/main.py` (add import and registration)

```python
# Add import
from app.routes.gestures_routes import router as gestures_router

# Add router registration (near other router includes)
app.include_router(gestures_router)
```

---

## WebSocket Message Types Summary

### Client → Server

| Type | Payload | Description |
|------|---------|-------------|
| `gesture` | `{gesture_type, message?, ai_generated?}` | Send a gesture |
| `gesture_acknowledge` | `{gesture_id, send_back?, send_back_type?, send_back_message?}` | Acknowledge + optionally send back |

### Server → Client

| Type | Payload | Description |
|------|---------|-------------|
| `gesture_sent` | `{gesture}` | Confirmation of sent gesture |
| `gesture_received` | `{gesture}` | New gesture received |
| `gesture_acknowledged` | `{gesture_id, acknowledged_by, response_gesture?}` | Your gesture was acknowledged |
| `gesture_acknowledged_confirm` | `{gesture_id, response_gesture?}` | Confirmation of your acknowledgment |

---

## Testing Checklist

### Database Tests
- [ ] Migration runs without errors
- [ ] `connection_gestures` table created with correct schema
- [ ] Indexes created properly
- [ ] RLS policy applied

### Service Tests
- [ ] `save_gesture` creates gesture and returns correct format
- [ ] `get_pending_gestures` returns only unacknowledged gestures for recipient
- [ ] `acknowledge_gesture` updates acknowledged_at and links response
- [ ] `mark_gesture_delivered` sets delivered_at
- [ ] `get_gesture_by_id` returns gesture or None

### API Tests
- [ ] `POST /api/gestures/send` creates gesture
- [ ] `POST /api/gestures/send` returns recipient_online status
- [ ] `POST /api/gestures/acknowledge` marks acknowledged
- [ ] `POST /api/gestures/acknowledge` with send_back creates response gesture
- [ ] `GET /api/gestures/pending` returns pending gestures
- [ ] `GET /api/gestures/{id}` returns gesture

### WebSocket Tests
- [ ] Gesture sent via WebSocket reaches recipient
- [ ] Acknowledgment sent via WebSocket notifies sender
- [ ] Delivered status updated when recipient is online
- [ ] Response gesture delivered in real-time
