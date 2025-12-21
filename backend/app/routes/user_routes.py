from fastapi import APIRouter, HTTPException, Body, Depends
from typing import Optional
from pydantic import BaseModel

from app.services.db_service import db_service
from app.middleware.auth import get_current_user, get_current_user_optional, UserContext

router = APIRouter(prefix="/api/users", tags=["users"])


class UserSyncRequest(BaseModel):
    auth0_id: str
    email: str
    name: str = None
    picture: str = None


class CreateProfileRequest(BaseModel):
    display_name: str


@router.post("/sync")
async def sync_user(user: UserSyncRequest):
    """
    Sync user from Auth0 to local database.
    Creates user if not exists, updates if exists.
    """
    try:
        user_id = db_service.upsert_user(
            auth0_id=user.auth0_id,
            email=user.email,
            name=user.name,
            picture=user.picture
        )
        return {"success": True, "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me")
async def get_current_user_profile(
    current_user: UserContext = Depends(get_current_user)
):
    """
    Get current user's profile and relationship context.
    Returns user info and relationship details if they have one.
    """
    return {
        "user_id": current_user.user_id,
        "auth0_id": current_user.auth0_id,
        "email": current_user.email,
        "name": current_user.name,
        "relationship_id": current_user.relationship_id,
        "display_name": current_user.display_name,
        "partner_display_name": current_user.partner_display_name,
        "has_relationship": current_user.relationship_id is not None,
        "needs_onboarding": not current_user.user_id or not current_user.relationship_id
    }


@router.post("/profile")
async def create_user_profile(
    request: CreateProfileRequest,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Create user profile with a new relationship (during onboarding).
    This is called when a new user completes onboarding.
    """
    # Check if user already has a relationship
    if current_user.relationship_id:
        raise HTTPException(
            status_code=400,
            detail="User already has a relationship"
        )

    try:
        user_id, relationship_id = db_service.create_user_with_relationship(
            auth0_id=current_user.auth0_id,
            email=current_user.email,
            name=current_user.name,
            display_name=request.display_name
        )

        return {
            "success": True,
            "user_id": user_id,
            "relationship_id": relationship_id,
            "display_name": request.display_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relationship")
async def get_user_relationship(
    current_user: UserContext = Depends(get_current_user)
):
    """
    Get current user's relationship details including partner info.
    """
    if not current_user.relationship_id:
        return {
            "has_relationship": False,
            "relationship_id": None,
            "display_name": None,
            "partner_display_name": None
        }

    # Get speaker labels for the relationship
    speaker_labels = db_service.get_speaker_labels(current_user.relationship_id)

    return {
        "has_relationship": True,
        "relationship_id": current_user.relationship_id,
        "display_name": current_user.display_name,
        "partner_display_name": current_user.partner_display_name,
        "speaker_labels": speaker_labels
    }
