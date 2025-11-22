from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from livekit import api
from .config import settings
from supabase import create_client
from .routes import transcription
import json

app = FastAPI(title="HeartSync API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(transcription.router)
from .routes import realtime_transcription
app.include_router(realtime_transcription.router)
from .routes import post_fight
app.include_router(post_fight.router)
from .routes import pdf_upload
app.include_router(pdf_upload.router)

# Initialize Supabase client
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

@app.get("/")
async def root():
    return {"message": "HeartSync API is running"}

@app.post("/api/token")
async def get_token(room_name: str, participant_name: str):
    token = api.AccessToken(
        settings.LIVEKIT_API_KEY,
        settings.LIVEKIT_API_SECRET
    )
    token.with_identity(participant_name)
    token.with_name(participant_name)
    token.with_grants(api.VideoGrants(
        room_join=True,
        room=room_name,
    ))
    return {"token": token.to_jwt()}

@app.get("/api/conflicts/{conflict_id}")
async def get_conflict(conflict_id: str):
    """Retrieve conflict data including transcript"""
    try:
        # Get conflict metadata
        response = supabase.table("conflicts").select("*").eq("id", conflict_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Conflict {conflict_id} not found")
        
        conflict = response.data[0]
        
        # If transcript_path is stored, try to retrieve it from Storage
        transcript_data = None
        if conflict.get("transcript_path"):
            try:
                transcript_content = supabase.storage.from_("transcripts").download(conflict["transcript_path"])
                transcript_data = json.loads(transcript_content.decode('utf-8'))
            except Exception as e:
                print(f"Error retrieving transcript from storage: {e}")
        
        return {
            "conflict": conflict,
            "transcript": transcript_data,
            "message": "Conflict data retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session info from LiveKit"""
    try:
        # For now, return info about the session
        # In production, you'd query LiveKit Analytics API
        return {
            "session_id": session_id,
            "room_name": "voice-test",
            "message": "Session info retrieved. To get full analytics, check LiveKit Cloud dashboard"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conflicts")
async def list_conflicts(relationship_id: str = None):
    """List all conflicts, optionally filtered by relationship"""
    try:
        if relationship_id:
            response = supabase.table("conflicts").select("*").eq("relationship_id", relationship_id).execute()
        else:
            response = supabase.table("conflicts").select("*").execute()
        
        return {
            "total": len(response.data),
            "conflicts": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/conflicts/create")
async def create_conflict(relationship_id: str = "00000000-0000-0000-0000-000000000000"):
    """Create a new conflict and return its ID"""
    import uuid
    from datetime import datetime
    
    try:
        conflict_id = str(uuid.uuid4())
        data = {
            "id": conflict_id,
            "relationship_id": relationship_id,
            "started_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        try:
            supabase.table("conflicts").insert(data).execute()
            return {
                "success": True,
                "conflict_id": conflict_id,
                "relationship_id": relationship_id
            }
        except Exception as e:
            # If DB insert fails, still return conflict_id for frontend use
            return {
                "success": True,
                "conflict_id": conflict_id,
                "relationship_id": relationship_id,
                "warning": f"Database insert failed: {str(e)}"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
