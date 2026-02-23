"""
Digest API Routes - Weekly relationship digest endpoints
"""
import logging
from fastapi import APIRouter, Query, HTTPException

from app.services.db_service import db_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/digests", tags=["digests"])


@router.get("")
async def list_digests(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000"),
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    """List digests for a relationship (paginated, newest first)."""
    try:
        digests = db_service.get_digests(relationship_id, limit=limit, offset=offset)
        return {
            "digests": [_serialize_digest(d) for d in digests],
            "total": len(digests),
        }
    except Exception as e:
        logger.error(f"Error listing digests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_digest(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000"),
):
    """Get the most recent digest for a relationship."""
    try:
        digest = db_service.get_latest_digest(relationship_id)
        if not digest:
            return {"digest": None, "has_digest": False}
        return {"digest": _serialize_digest(digest), "has_digest": True}
    except Exception as e:
        logger.error(f"Error getting latest digest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{digest_id}")
async def get_digest(digest_id: str):
    """Get a single digest by ID."""
    try:
        digest = db_service.get_digest_by_id(digest_id)
        if not digest:
            raise HTTPException(status_code=404, detail="Digest not found")
        return _serialize_digest(digest)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting digest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{digest_id}/read")
async def mark_digest_read(
    digest_id: str,
    partner: str = Query(..., description="'partner_a' or 'partner_b'"),
):
    """Mark a digest as read for a specific partner."""
    if partner not in ("partner_a", "partner_b"):
        raise HTTPException(status_code=400, detail="partner must be 'partner_a' or 'partner_b'")
    try:
        success = db_service.mark_digest_read(digest_id, partner)
        if not success:
            raise HTTPException(status_code=404, detail="Digest not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking digest read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def manually_generate_digest(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000"),
):
    """Manually trigger digest generation (for testing)."""
    try:
        from app.services.digest_service import digest_service
        result = await digest_service.generate_weekly_digest(relationship_id)
        if not result:
            raise HTTPException(status_code=500, detail="Digest generation failed")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating digest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _serialize_digest(d: dict) -> dict:
    """Serialize a digest dict for JSON response."""
    return {
        "id": str(d.get("id")),
        "relationship_id": str(d.get("relationship_id")),
        "week_start": str(d.get("week_start")),
        "week_end": str(d.get("week_end")),
        "metrics": d.get("metrics"),
        "narrative": d.get("narrative"),
        "highlights": d.get("highlights"),
        "recommendations": d.get("recommendations"),
        "is_read_partner_a": d.get("is_read_partner_a", False),
        "is_read_partner_b": d.get("is_read_partner_b", False),
        "created_at": str(d.get("created_at")) if d.get("created_at") else None,
    }
