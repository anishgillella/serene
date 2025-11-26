from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from livekit import api
from .config import settings
from supabase import create_client
from .routes import transcription
import json
import logging

# Configure logging to show INFO level and above
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

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
from .routes import calendar
app.include_router(calendar.router)
from .routes import analytics
app.include_router(analytics.router)

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
    Generate a token for mediator room and PRE-CREATE agent dispatch.
    Room name format: mediator-{conflict_id}
    
    IMPORTANT: For trial accounts/local dev agents, we create the dispatch
    BEFORE the user connects, as automatic assignment may not work.
    
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
    
    # Verify API credentials are set
    if not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
        raise HTTPException(
            status_code=500,
            detail="LiveKit API credentials not configured. Please check LIVEKIT_API_KEY and LIVEKIT_API_SECRET in .env"
        )
    
    room_name = f"mediator-{conflict_id}"
    
    # Generate token with embedded dispatch
    # Token-based dispatch should work for cloud-deployed agents
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
        can_publish_data=True,  # Required for agent communication
    ))
    
    
    return {
        "token": token.to_jwt(),
        "room": room_name,
        "url": settings.LIVEKIT_URL
    }

@app.post("/api/dispatch-agent")
async def dispatch_agent(request: dict = Body(...)):
    """
    Create explicit agent dispatch for local development.
    With AgentServer pattern, agents auto-join, but explicit dispatch may be needed for local dev.
    """
    room_name = request.get("room_name")
    
    if not room_name:
        raise HTTPException(status_code=400, detail="room_name is required")
    
    try:
        lkapi = api.LiveKitAPI(
            settings.LIVEKIT_URL,
            settings.LIVEKIT_API_KEY,
            settings.LIVEKIT_API_SECRET
        )
        
        try:
            req = api.CreateAgentDispatchRequest(room=room_name)
            dispatch = await lkapi.agent_dispatch.create_dispatch(req)
            
            return {
                "success": True,
                "dispatch_id": dispatch.id,
                "room": room_name,
                "message": "Dispatch created. Agent should join via AgentServer pattern."
            }
        finally:
            await lkapi.aclose()
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Dispatch failed but agent may auto-join: {str(e)}"
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
            logger.error(f"Error retrieving transcript from Pinecone: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
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
                logger.error(f"Error retrieving transcript from S3: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        return {
            "conflict": conflict,
            "transcript": transcript_data,
            "message": "Conflict data retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conflicts")
async def list_conflicts(relationship_id: str = None):
    """List all conflicts, optionally filtered by relationship"""
    import asyncio
    import logging
    import concurrent.futures
    logger = logging.getLogger(__name__)
    
    async def fetch_conflicts():
        """Fetch conflicts with timeout protection"""
        try:
            # Try using db_service first (direct PostgreSQL connection, bypasses RLS)
            try:
                from app.services.db_service import db_service
                # Run database query in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    conflicts_data = await loop.run_in_executor(
                        executor,
                        lambda: db_service.get_all_conflicts(relationship_id=relationship_id)
                    )
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
            logger.error(f"❌ Error fetching conflicts: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    try:
        # Add 10 second timeout to prevent hanging
        result = await asyncio.wait_for(fetch_conflicts(), timeout=10.0)
        return result
    except asyncio.TimeoutError:
        logger.error("⏱️ Timeout fetching conflicts (10s), returning empty list")
        return {
            "total": 0,
            "conflicts": []
        }
    except Exception as e:
        logger.error(f"❌ Error listing conflicts: {e}")
        import traceback
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
