from fastapi import FastAPI, HTTPException, Body
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

@app.post("/api/mediator/token")
async def get_mediator_token(request: dict = Body(...)):
    """
    Generate a token for mediator room.
    Room name format: mediator-{conflict_id}
    
    Request body:
    {
        "conflict_id": "string",
        "participant_name": "string" (optional, defaults to "user")
    }
    """
    conflict_id = request.get("conflict_id")
    participant_name = request.get("participant_name", "user")
    
    if not conflict_id:
        raise HTTPException(status_code=400, detail="conflict_id is required")
    
    room_name = f"mediator-{conflict_id}"
    token = api.AccessToken(
        settings.LIVEKIT_API_KEY,
        settings.LIVEKIT_API_SECRET
    )
    token.with_identity(participant_name)
    token.with_name(participant_name)
    token.with_grants(api.VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=True,
        can_subscribe=True,
    ))
    return {
        "token": token.to_jwt(),
        "room": room_name,
        "url": settings.LIVEKIT_URL
    }

@app.get("/api/conflicts/{conflict_id}")
async def get_conflict(conflict_id: str):
    """Retrieve conflict data including transcript"""
    try:
        from app.services.pinecone_service import pinecone_service
        
        # Get conflict metadata
        response = supabase.table("conflicts").select("*").eq("id", conflict_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Conflict {conflict_id} not found")
        
        conflict = response.data[0]
        
        # Get transcript from Pinecone (where it's actually stored)
        transcript_data = None
        try:
            transcript_result = pinecone_service.get_by_conflict_id(
                conflict_id=conflict_id,
                namespace="transcripts"
            )
            
            if transcript_result and transcript_result.metadata:
                metadata = transcript_result.metadata
                transcript_text = metadata.get("transcript_text", "")
                
                # Convert transcript text to array format for frontend
                if transcript_text:
                    # Split by newlines and filter empty lines
                    transcript_lines = [line.strip() for line in transcript_text.split('\n') if line.strip()]
                    transcript_data = transcript_lines
                else:
                    # Try to get segments if available
                    segments = metadata.get("segments", [])
                    if segments:
                        transcript_data = [
                            f"{seg.get('speaker', 'Speaker')}: {seg.get('text', '')}"
                            for seg in segments
                        ]
        except Exception as e:
            print(f"Error retrieving transcript from Pinecone: {e}")
            import traceback
            traceback.print_exc()
        
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
