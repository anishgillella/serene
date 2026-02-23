"""
Alert API Routes - Conflict prevention alert endpoints
"""
import logging
from fastapi import APIRouter, Query, HTTPException

from app.services.db_service import db_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("")
async def list_active_alerts(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000"),
):
    """List active (not dismissed, not snoozed) alerts."""
    try:
        alerts = db_service.get_active_alerts(relationship_id)
        return {
            "alerts": [_serialize_alert(a) for a in alerts],
            "total": len(alerts),
        }
    except Exception as e:
        logger.error(f"Error listing alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def list_alert_history(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000"),
    limit: int = Query(default=50, ge=1, le=200),
):
    """List all alerts including dismissed ones."""
    try:
        alerts = db_service.get_alert_history(relationship_id, limit=limit)
        return {
            "alerts": [_serialize_alert(a) for a in alerts],
            "total": len(alerts),
        }
    except Exception as e:
        logger.error(f"Error listing alert history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: str,
    dismissed_by: str = Query(default=None, description="'partner_a' or 'partner_b'"),
):
    """Dismiss an alert."""
    try:
        success = db_service.dismiss_alert(alert_id, dismissed_by)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error dismissing alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{alert_id}/snooze")
async def snooze_alert(
    alert_id: str,
    hours: int = Query(default=4, ge=1, le=72),
):
    """Snooze an alert for N hours."""
    try:
        success = db_service.snooze_alert(alert_id, hours)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        return {"success": True, "snoozed_hours": hours}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error snoozing alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unread-count")
async def get_unread_count(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000"),
):
    """Get count of active (unread) alerts for badge display."""
    try:
        count = db_service.get_unread_alert_count(relationship_id)
        return {"count": count}
    except Exception as e:
        logger.error(f"Error getting unread count: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _serialize_alert(a: dict) -> dict:
    """Serialize an alert dict for JSON response."""
    return {
        "id": str(a.get("id")),
        "relationship_id": str(a.get("relationship_id")),
        "alert_type": a.get("alert_type"),
        "severity": a.get("severity"),
        "title": a.get("title"),
        "message": a.get("message"),
        "context": a.get("context"),
        "is_dismissed": a.get("is_dismissed", False),
        "dismissed_by": a.get("dismissed_by"),
        "snoozed_until": str(a.get("snoozed_until")) if a.get("snoozed_until") else None,
        "delivered_in_chat": a.get("delivered_in_chat", False),
        "created_at": str(a.get("created_at")) if a.get("created_at") else None,
    }
