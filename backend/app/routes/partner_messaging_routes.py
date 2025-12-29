"""
Partner Messaging API Routes

Handles partner-to-partner messaging within Luna.
Includes Phase 3 Luna suggestion endpoints.
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

from app.services.db_service import db_service
from app.services.message_suggestion_service import message_suggestion_service
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


# ============================================
# PYDANTIC MODELS FOR LUNA SUGGESTIONS
# ============================================

class LunaSuggestionRequest(BaseModel):
    """Request for Luna to analyze a draft message"""
    conversation_id: str
    sender_id: str = Field(..., pattern='^(partner_a|partner_b)$')
    draft_message: str = Field(..., min_length=1, max_length=5000)


class SuggestionAlternative(BaseModel):
    """An alternative message suggestion"""
    text: str
    tone: str
    rationale: str


class LunaSuggestionResponse(BaseModel):
    """Luna's analysis and suggestions for a draft message"""
    suggestion_id: Optional[str] = None
    original_message: str
    risk_assessment: str  # 'safe', 'risky', 'high_risk'
    detected_issues: List[str] = Field(default_factory=list)
    primary_suggestion: str
    suggestion_rationale: str
    alternatives: List[SuggestionAlternative] = Field(default_factory=list)
    underlying_need: Optional[str] = None
    historical_context: Optional[str] = None


class SuggestionResponseRequest(BaseModel):
    """Record user's response to a Luna suggestion"""
    action: str = Field(..., pattern='^(accepted|rejected|modified|ignored)$')
    final_message_id: Optional[str] = None
    selected_alternative_index: Optional[int] = None


# ============================================
# CONVERSATION ROUTES
# ============================================

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


# ============================================
# MESSAGE SENDING
# ============================================

async def embed_message_async(
    message_id: str,
    conversation_id: str,
    relationship_id: str,
    sender_id: str,
    content: str,
    sent_at: str
):
    """Background task to embed a message in Pinecone for RAG."""
    try:
        await message_suggestion_service.embed_and_store_message(
            message_id=message_id,
            conversation_id=conversation_id,
            relationship_id=relationship_id,
            sender_id=sender_id,
            content=content,
            sent_at=sent_at,
            sentiment=None,  # Will be added in Phase 4
            had_conflict=False,  # Will be analyzed in Phase 4
            trigger_phrases=[]
        )
    except Exception as e:
        logger.error(f"Background embed error: {e}")


@router.post("/send", response_model=SendMessageResponse)
async def send_message(
    request: SendMessageRequest,
    background_tasks: BackgroundTasks
):
    """
    Send a message to the partner.

    If luna_intervened is True, the original_content field should contain
    what the user originally typed before accepting Luna's suggestion.
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

        # Get conversation to find relationship_id for embedding
        conversation = db_service.get_conversation_by_id(request.conversation_id)
        if conversation:
            # Queue async embedding for RAG (fire-and-forget)
            background_tasks.add_task(
                embed_message_async,
                message_id=message["id"],
                conversation_id=request.conversation_id,
                relationship_id=conversation["relationship_id"],
                sender_id=request.sender_id,
                content=request.content,
                sent_at=message["sent_at"]
            )

        return SendMessageResponse(
            message=PartnerMessage(**message),
            luna_suggestion=None
        )
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# MESSAGE STATUS
# ============================================

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


# ============================================
# LUNA SUGGESTIONS (Phase 3)
# ============================================

@router.post("/suggest", response_model=LunaSuggestionResponse)
async def get_luna_suggestion(request: LunaSuggestionRequest):
    """
    Get Luna's suggestion for a draft message before sending.

    Luna analyzes the message for:
    - Potential escalation triggers
    - Accusatory language ("you always", "you never")
    - Known trigger phrases for this relationship
    - Gottman's Four Horsemen markers
    - Message length anomalies

    Returns the original message if it's safe, or suggestions for improvement.
    """
    try:
        # Get conversation to find relationship_id
        conversation = db_service.get_conversation_by_id(request.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Get user's sensitivity preference
        preferences = db_service.get_messaging_preferences(
            relationship_id=conversation['relationship_id'],
            partner_id=request.sender_id
        )

        # Check if Luna suggestions are enabled
        if not preferences.get('luna_assistance_enabled', True):
            return LunaSuggestionResponse(
                suggestion_id=None,
                original_message=request.draft_message,
                risk_assessment="safe",
                detected_issues=[],
                primary_suggestion=request.draft_message,
                suggestion_rationale="Luna suggestions are disabled.",
                alternatives=[],
                underlying_need=None,
                historical_context=None
            )

        sensitivity = preferences.get('intervention_sensitivity', 'medium')

        # Get Luna's analysis and suggestions
        result = await message_suggestion_service.analyze_and_suggest(
            draft_message=request.draft_message,
            conversation_id=request.conversation_id,
            sender_id=request.sender_id,
            relationship_id=conversation['relationship_id'],
            sensitivity=sensitivity
        )

        # Convert alternatives to Pydantic models
        alternatives = [
            SuggestionAlternative(**alt) for alt in result.get('alternatives', [])
        ]

        return LunaSuggestionResponse(
            suggestion_id=result.get('suggestion_id'),
            original_message=result['original_message'],
            risk_assessment=result['risk_assessment'],
            detected_issues=result.get('detected_issues', []),
            primary_suggestion=result['primary_suggestion'],
            suggestion_rationale=result['suggestion_rationale'],
            alternatives=alternatives,
            underlying_need=result.get('underlying_need'),
            historical_context=result.get('historical_context')
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting suggestion: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggestion/{suggestion_id}/respond")
async def respond_to_suggestion(
    suggestion_id: str,
    request: SuggestionResponseRequest
):
    """
    Record how the user responded to a Luna suggestion.

    Actions:
    - accepted: User sent Luna's suggestion
    - rejected: User sent their original message
    - modified: User edited the suggestion before sending
    - ignored: User cancelled/didn't send anything
    """
    try:
        success = message_suggestion_service.record_suggestion_response(
            suggestion_id=suggestion_id,
            action=request.action,
            final_message_id=request.final_message_id,
            selected_index=request.selected_alternative_index
        )
        return {"success": success}
    except Exception as e:
        logger.error(f"Error recording response: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestion-stats")
async def get_suggestion_stats(
    relationship_id: str = Query(...),
    days: int = Query(default=30, ge=1, le=365)
):
    """Get Luna suggestion acceptance statistics for analytics."""
    try:
        stats = db_service.get_suggestion_acceptance_rate(
            relationship_id=relationship_id,
            days=days
        )
        return stats
    except Exception as e:
        logger.error(f"Error getting suggestion stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# PREFERENCES
# ============================================

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
        if updates is None:
            # No updates provided, return current preferences
            prefs = db_service.get_messaging_preferences(relationship_id, partner_id)
        else:
            # Apply updates
            prefs = db_service.update_messaging_preferences(
                relationship_id,
                partner_id,
                updates.model_dump(exclude_none=True)
            )
        return MessagingPreferences(**prefs)
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))
