"""
Partner Messaging API Routes

Handles partner-to-partner messaging within Luna.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import logging

from app.services.db_service import db_service
from app.models.schemas import (
    PartnerConversation,
    PartnerMessage,
    SendMessageRequest,
    SendMessageResponse,
    GetMessagesResponse,
    MessagingPreferences,
    UpdatePreferencesRequest
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
            messages = messages[1:]  # Remove the extra one (oldest)

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
        # Save message
        message = db_service.save_partner_message(
            conversation_id=request.conversation_id,
            sender_id=request.sender_id,
            content=request.content,
            original_content=request.original_content,
            luna_intervened=request.luna_intervened
        )

        # TODO Phase 3: If request_luna_review, call suggestion service
        # TODO Phase 4: Queue async analysis via BackgroundTasks

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


@router.get("/preferences", response_model=MessagingPreferences)
async def get_preferences(
    relationship_id: str = Query(...),
    partner_id: str = Query(..., pattern='^(partner_a|partner_b)$')
):
    """Get messaging preferences for a partner."""
    try:
        prefs = db_service.get_messaging_preferences(relationship_id, partner_id)
        return MessagingPreferences(**prefs)
    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/preferences", response_model=MessagingPreferences)
async def update_preferences(
    relationship_id: str = Query(...),
    partner_id: str = Query(..., pattern='^(partner_a|partner_b)$'),
    updates: UpdatePreferencesRequest = None
):
    """Update messaging preferences for a partner."""
    try:
        # For Phase 1, just return current preferences
        # TODO Phase 2: Implement update logic
        prefs = db_service.get_messaging_preferences(relationship_id, partner_id)
        return MessagingPreferences(**prefs)
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))
