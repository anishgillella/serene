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
        from app.services.s3_service import s3_service
        from app.services.db_service import db_service
        
        # Get conflict metadata using db_service (bypasses RLS)
        conflict = db_service.get_conflict_by_id(conflict_id)
        
        if not conflict:
            raise HTTPException(status_code=404, detail=f"Conflict {conflict_id} not found")
        
        # Get transcript from Pinecone first, then fallback to S3
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
        
        # Fallback to S3 if not found in Pinecone
        if not transcript_data and conflict.get("transcript_path") and s3_service:
            try:
                s3_key = conflict["transcript_path"]
                if s3_key.startswith(f"s3://{settings.S3_BUCKET_NAME}/"):
                    s3_key = s3_key.replace(f"s3://{settings.S3_BUCKET_NAME}/", "")
                
                file_response = s3_service.download_file(s3_key)
                if file_response:
                    import json
                    stored_transcript = json.loads(file_response.decode('utf-8'))
                    if isinstance(stored_transcript, list):
                        transcript_data = [f"{seg.get('speaker', 'Speaker')}: {seg.get('text', '')}" for seg in stored_transcript if seg.get('text')]
                    elif isinstance(stored_transcript, dict) and stored_transcript.get("transcript_text"):
                        transcript_data = stored_transcript["transcript_text"].split('\n')
                    elif isinstance(stored_transcript, dict) and stored_transcript.get("segments"):
                        transcript_data = [f"{seg.get('speaker', 'Speaker')}: {seg.get('text', '')}" for seg in stored_transcript["segments"] if seg.get('text')]
            except Exception as e:
                print(f"Error retrieving transcript from S3: {e}")
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
        # Try using db_service first (direct PostgreSQL connection, bypasses RLS)
        try:
            from app.services.db_service import db_service
            conflicts_data = db_service.get_all_conflicts(relationship_id=relationship_id)
            return {
                "total": len(conflicts_data),
                "conflicts": conflicts_data
            }
        except ImportError:
            # Fallback to Supabase if db_service not available
            pass
        
        # Fallback to Supabase
        if relationship_id:
            response = supabase.table("conflicts").select("*").eq("relationship_id", relationship_id).execute()
        else:
            response = supabase.table("conflicts").select("*").execute()
        
        # Ensure data is always a list, even if empty or None
        conflicts_data = response.data if response.data is not None else []
        
        return {
            "total": len(conflicts_data),
            "conflicts": conflicts_data
        }
    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Error listing conflicts: {e}")
        logger.error(traceback.format_exc())
        # Return empty list instead of raising error for better UX
        return {
            "total": 0,
            "conflicts": []
        }

@app.post("/api/conflicts/create")
async def create_conflict(relationship_id: str = None):
    """Create a new conflict and return its ID (uses hardcoded default relationship)"""
    import uuid
    from datetime import datetime
    from app.services.db_service import DEFAULT_RELATIONSHIP_ID
    
    try:
        conflict_id = str(uuid.uuid4())
        
        # Always use default relationship ID for MVP
        relationship_id = DEFAULT_RELATIONSHIP_ID
        
        # Use db_service (direct PostgreSQL connection, bypasses RLS)
        try:
            from app.services.db_service import db_service
            db_service.create_conflict(
                conflict_id=conflict_id,
                relationship_id=relationship_id,
                status="active"
            )
            return {
                "success": True,
                "conflict_id": conflict_id,
                "relationship_id": relationship_id
            }
        except ImportError:
            # Fallback to Supabase if db_service not available
            try:
                data = {
                    "id": conflict_id,
                    "relationship_id": relationship_id,
                    "started_at": datetime.now().isoformat(),
                    "status": "active"
                }
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
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Error creating conflict: {e}")
        raise HTTPException(status_code=500, detail=str(e))
