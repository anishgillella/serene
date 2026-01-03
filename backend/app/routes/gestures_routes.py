"""
Connection Gestures API Routes

Handles emotional gesture sending and receiving between partners.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging
import asyncio

from pydantic import BaseModel, Field

from app.services.db_service import db_service
from app.services.gesture_message_service import gesture_message_service
from app.models.schemas import (
    ConnectionGesture,
    SendGestureRequest,
    SendGestureResponse,
    AcknowledgeGestureRequest,
    AcknowledgeGestureResponse,
    PendingGesturesResponse,
    GenerateGestureMessageRequest,
    GenerateGestureMessageResponse,
    GestureType
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
            ai_generated=request.ai_generated,
            ai_context_used=request.ai_context
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


# ============================================
# AI MESSAGE GENERATION ENDPOINTS
# ============================================

@router.post("/generate-message", response_model=GenerateGestureMessageResponse)
async def generate_gesture_message(request: GenerateGestureMessageRequest):
    """
    Generate a personalized AI message for a gesture.

    Luna uses relationship context (recent conflicts, chat history,
    partner profiles) to craft a meaningful message.

    The partner can:
    - Use the generated message as-is
    - Edit the message before sending
    - Request a different message (regenerate)
    - Write their own message instead
    """
    try:
        result = await gesture_message_service.generate_message(
            relationship_id=request.relationship_id,
            sender_id=request.sender_id,
            gesture_type=request.gesture_type.value
        )

        return GenerateGestureMessageResponse(
            message=result["message"],
            context_used=result["context_used"]
        )
    except Exception as e:
        logger.error(f"Error generating gesture message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RegenerateMessageRequest(BaseModel):
    """Request to regenerate a gesture message"""
    relationship_id: str
    sender_id: str = Field(..., pattern='^(partner_a|partner_b)$')
    gesture_type: GestureType
    previous_message: str


@router.post("/regenerate-message", response_model=GenerateGestureMessageResponse)
async def regenerate_gesture_message(request: RegenerateMessageRequest):
    """
    Generate a different message than the previous one.

    Use this when the partner wants an alternative suggestion.
    """
    try:
        result = await gesture_message_service.regenerate_message(
            relationship_id=request.relationship_id,
            sender_id=request.sender_id,
            gesture_type=request.gesture_type.value,
            previous_message=request.previous_message
        )

        return GenerateGestureMessageResponse(
            message=result["message"],
            context_used=result["context_used"]
        )
    except Exception as e:
        logger.error(f"Error regenerating gesture message: {e}")
        raise HTTPException(status_code=500, detail=str(e))
