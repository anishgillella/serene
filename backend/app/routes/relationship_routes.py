"""
Relationship management API endpoints for multi-tenancy support.
Enables multiple couples to use the app with dynamic relationship_id.
"""
import logging
from fastapi import APIRouter, HTTPException, Header, Query, Body
from typing import Optional
from pydantic import BaseModel

from app.services.db_service import db_service, DEFAULT_RELATIONSHIP_ID

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/relationships", tags=["relationships"])


class CreateRelationshipRequest(BaseModel):
    partner_a_name: str
    partner_b_name: str


class UpdateRelationshipRequest(BaseModel):
    partner_a_name: Optional[str] = None
    partner_b_name: Optional[str] = None


@router.post("/create")
async def create_relationship(request: CreateRelationshipRequest):
    """
    Create a new relationship for a couple.
    Returns relationship_id to be stored in localStorage.

    Request body:
    {
        "partner_a_name": "John",
        "partner_b_name": "Jane"
    }
    """
    if not request.partner_a_name or not request.partner_b_name:
        raise HTTPException(
            status_code=400,
            detail="Both partner_a_name and partner_b_name are required"
        )

    try:
        relationship_id = db_service.create_relationship(
            partner_a_name=request.partner_a_name,
            partner_b_name=request.partner_b_name
        )

        logger.info(f"Created new relationship: {relationship_id} for {request.partner_a_name} & {request.partner_b_name}")

        return {
            "success": True,
            "relationship_id": relationship_id,
            "partner_a_name": request.partner_a_name,
            "partner_b_name": request.partner_b_name,
            "message": "Relationship created successfully. Store relationship_id in localStorage."
        }
    except Exception as e:
        logger.error(f"Error creating relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{relationship_id}")
async def get_relationship(relationship_id: str):
    """
    Get relationship details by ID.
    """
    relationship = db_service.get_relationship(relationship_id)

    if not relationship:
        raise HTTPException(status_code=404, detail="Relationship not found")

    return {
        "success": True,
        "relationship": relationship
    }


@router.get("/{relationship_id}/profile")
async def get_couple_profile(relationship_id: str):
    """
    Get couple profile with partner names.
    """
    profile = db_service.get_couple_profile(relationship_id)

    if not profile:
        # Try to get from relationships table as fallback
        relationship = db_service.get_relationship(relationship_id)
        if relationship:
            return {
                "success": True,
                "profile": {
                    "relationship_id": relationship_id,
                    "partner_a_name": relationship.get("partner_a_name", "Partner A"),
                    "partner_b_name": relationship.get("partner_b_name", "Partner B")
                }
            }
        raise HTTPException(status_code=404, detail="Couple profile not found")

    return {
        "success": True,
        "profile": profile
    }


@router.put("/{relationship_id}")
async def update_relationship(
    relationship_id: str,
    request: UpdateRelationshipRequest
):
    """
    Update partner names for a relationship.
    """
    if not db_service.validate_relationship_exists(relationship_id):
        raise HTTPException(status_code=404, detail="Relationship not found")

    success = db_service.update_relationship_names(
        relationship_id=relationship_id,
        partner_a_name=request.partner_a_name,
        partner_b_name=request.partner_b_name
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update relationship")

    return {
        "success": True,
        "message": "Relationship updated successfully"
    }


@router.get("/{relationship_id}/speaker-labels")
async def get_speaker_labels(relationship_id: str):
    """
    Get speaker labels for transcript display.
    Maps partner_a/partner_b to actual names.
    """
    labels = db_service.get_dynamic_speaker_labels(relationship_id)

    return {
        "success": True,
        "labels": labels
    }


@router.get("/validate/{relationship_id}")
async def validate_relationship(relationship_id: str):
    """
    Check if a relationship exists.
    Used by frontend to validate stored relationship_id.
    """
    exists = db_service.validate_relationship_exists(relationship_id)

    return {
        "success": True,
        "exists": exists,
        "relationship_id": relationship_id
    }


@router.get("/default/id")
async def get_default_relationship():
    """
    Get the default relationship ID (Adrian & Elara test data).
    For backward compatibility and testing.
    """
    return {
        "success": True,
        "relationship_id": DEFAULT_RELATIONSHIP_ID,
        "message": "Default test relationship (Adrian & Elara)"
    }
