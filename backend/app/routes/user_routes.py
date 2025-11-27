from fastapi import APIRouter, HTTPException, Body, Depends
from app.services.db_service import db_service
from pydantic import BaseModel

router = APIRouter(prefix="/api/users", tags=["users"])

class UserSyncRequest(BaseModel):
    auth0_id: str
    email: str
    name: str = None
    picture: str = None

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
