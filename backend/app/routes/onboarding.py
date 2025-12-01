from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import json
import logging
from datetime import datetime

from app.services.pinecone_service import pinecone_service
from app.services.embeddings_service import embeddings_service
from app.services.s3_service import s3_service
from app.services.db_service import db_service

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])
logger = logging.getLogger(__name__)

# --- Pydantic Models ---

class PartnerProfile(BaseModel):
    name: str
    role: str # 'boyfriend' | 'girlfriend'
    age: int
    communication_style: str
    stress_triggers: List[str]
    soothing_mechanisms: List[str]
    background_story: str
    hobbies: List[str]
    favorite_food: str
    favorite_cuisine: str
    favorite_sports: List[str]
    favorite_books: List[str]
    favorite_celebrities: List[str]
    traumatic_experiences: Optional[str] = ""
    key_life_experiences: str
    partner_description: str
    what_i_admire: str
    what_frustrates_me: str

class RelationshipProfile(BaseModel):
    recurring_arguments: List[str]
    shared_goals: List[str]
    relationship_dynamic: str

class OnboardingSubmission(BaseModel):
    relationship_id: str
    partner_id: str
    partner_profile: PartnerProfile
    relationship_profile: RelationshipProfile

# --- Helper Functions ---

def generate_narrative(data: OnboardingSubmission) -> str:
    """
    Convert structured onboarding data into a narrative text for RAG.
    """
    p = data.partner_profile
    r = data.relationship_profile
    
    lines = []
    lines.append(f"--- ONBOARDING PROFILE: {p.name} ({p.role}) ---")
    lines.append(f"Name: {p.name}")
    lines.append(f"Age: {p.age}")
    lines.append(f"Role: {p.role}")
    
    lines.append(f"\n## Background & Life Story")
    lines.append(f"{p.background_story}")
    lines.append(f"Key Life Experiences: {p.key_life_experiences}")
    if p.traumatic_experiences:
        lines.append(f"Traumatic Experiences: {p.traumatic_experiences}")
        
    lines.append(f"\n## Inner World & Personality")
    lines.append(f"Communication Style: {p.communication_style}")
    lines.append(f"Stress Triggers: {', '.join(p.stress_triggers)}")
    lines.append(f"Soothing Mechanisms: {', '.join(p.soothing_mechanisms)}")
    
    lines.append(f"\n## Interests & Favorites")
    lines.append(f"Hobbies: {', '.join(p.hobbies)}")
    lines.append(f"Favorite Food: {p.favorite_food} ({p.favorite_cuisine})")
    lines.append(f"Favorite Books: {', '.join(p.favorite_books)}")
    lines.append(f"Favorite Sports: {', '.join(p.favorite_sports)}")
    lines.append(f"Favorite Celebrities: {', '.join(p.favorite_celebrities)}")
    
    lines.append(f"\n## View on Partner")
    lines.append(f"Description of Partner: {p.partner_description}")
    lines.append(f"Admired Qualities: {p.what_i_admire}")
    lines.append(f"Frustrations: {p.what_frustrates_me}")
    
    lines.append(f"\n## Relationship Dynamics")
    lines.append(f"Dynamic: {r.relationship_dynamic}")
    lines.append(f"Recurring Arguments: {', '.join(r.recurring_arguments)}")
    lines.append(f"Shared Goals: {', '.join(r.shared_goals)}")
    
    return "\n".join(lines)

async def process_onboarding_task(data: OnboardingSubmission, pdf_id: str):
    """
    Background task to process onboarding data:
    1. Generate narrative text
    2. Embed and upsert to Pinecone
    3. Upload raw JSON to S3
    4. Update DB record
    """
    try:
        logger.info(f"🚀 Processing onboarding for {data.partner_profile.name} ({data.partner_id})")
        
        # 1. Generate Narrative
        narrative_text = generate_narrative(data)
        logger.info(f"📝 Generated narrative ({len(narrative_text)} chars)")
        
        # 2. Parallelize Pinecone Upsert and S3 Upload
        import asyncio
        
        async def upsert_pinecone():
            embedding = embeddings_service.embed_text(narrative_text)
            metadata = {
                "pdf_id": pdf_id,
                "relationship_id": data.relationship_id,
                "partner_id": data.partner_id,
                "pdf_type": "onboarding_profile",
                "filename": "onboarding_questionnaire.json",
                "text_length": len(narrative_text),
                "extracted_text": narrative_text,
                "name": data.partner_profile.name,
                "role": data.partner_profile.role
            }
            pinecone_service.index.upsert(
                vectors=[{
                    "id": f"onboarding_{pdf_id}",
                    "values": embedding,
                    "metadata": metadata
                }],
                namespace="profiles"
            )
            logger.info(f"✅ Upserted to Pinecone (profiles namespace)")

        async def upload_s3_and_update_db():
            json_content = data.model_dump_json(indent=2).encode('utf-8')
            s3_path = f"profiles/{data.relationship_id}/{pdf_id}_onboarding.json"
            
            s3_url = s3_service.upload_file(
                file_path=s3_path,
                file_content=json_content,
                content_type="application/json"
            )
            logger.info(f"☁️ Uploaded JSON to S3: {s3_url}")
            
            if db_service:
                updates = {
                    "extracted_text_length": len(narrative_text),
                    "file_path": s3_url or ""
                }
                db_service.update_profile(pdf_id, updates)
                logger.info("✅ Updated DB record")

        # Run both tasks concurrently
        await asyncio.gather(upsert_pinecone(), upload_s3_and_update_db())

    except Exception as e:
        logger.error(f"❌ Error in onboarding background task: {e}")
        import traceback
        logger.error(traceback.format_exc())

# --- Endpoints ---

@router.post("/submit")
async def submit_onboarding(
    submission: OnboardingSubmission,
    background_tasks: BackgroundTasks
):
    """
    Submit onboarding questionnaire.
    Processes in background: S3 upload, Pinecone embedding, DB record.
    """
    try:
        # Generate ID
        pdf_id = str(uuid.uuid4())
        
        # Create initial DB record
        # We treat this as a "profile" document
        if db_service:
            try:
                db_service.create_profile(
                    relationship_id=submission.relationship_id,
                    pdf_type="onboarding_profile",
                    partner_id=submission.partner_id,
                    filename="onboarding_questionnaire.json",
                    file_path="", # Will update later
                    pdf_id=pdf_id,
                    extracted_text_length=0 # Indicates processing
                )
            except Exception as e:
                logger.error(f"❌ Error creating initial DB record: {e}")
                # Continue anyway
        
        # Start background task
        background_tasks.add_task(process_onboarding_task, submission, pdf_id)
        
        return {
            "success": True,
            "message": "Onboarding submitted successfully",
            "pdf_id": pdf_id
        }
        
    except Exception as e:
        logger.error(f"❌ Error submitting onboarding: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profile")
async def get_profile(relationship_id: str = "00000000-0000-0000-0000-000000000000"):
    """
    Get the onboarding profile for a relationship.
    """
    try:
        if not db_service:
            raise HTTPException(status_code=503, detail="Database service unavailable")
            
        # Find the onboarding profile record
        profiles = db_service.get_profiles(relationship_id, pdf_type="onboarding_profile")
        if not profiles:
            return {"exists": False}
            
        profile_record = profiles[0]
        s3_url = profile_record.get("file_path")
        
        if not s3_url:
            return {"exists": False, "error": "No file path in record"}
            
        # Download JSON from S3
        # s3_url format: s3://bucket-name/key OR https://bucket.s3.region.amazonaws.com/key
        try:
            key = s3_url
            if "s3://" in s3_url:
                # Remove s3://bucket-name/
                parts = s3_url.replace("s3://", "").split("/", 1)
                if len(parts) > 1:
                    key = parts[1]
            elif ".com/" in s3_url:
                key = s3_url.split(".com/")[-1]
                
            content = s3_service.download_file(key)
            if not content:
                raise ValueError("Empty content from S3")
                
            data = json.loads(content)
            return {"exists": True, "data": data, "pdf_id": profile_record["pdf_id"]}
            
        except Exception as e:
            logger.error(f"❌ Error fetching S3 profile: {e}")
            return {"exists": False, "error": str(e)}
            
    except Exception as e:
        logger.error(f"❌ Error getting profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/profile")
async def update_profile(
    update_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    relationship_id: str = "00000000-0000-0000-0000-000000000000"
):
    """
    Update specific fields in the profile.
    Regenerates narrative and updates Vector DB.
    """
    try:
        # 1. Fetch existing data
        current_result = await get_profile(relationship_id)
        if not current_result.get("exists"):
            raise HTTPException(status_code=404, detail="Profile not found")
            
        current_data = current_result["data"]
        pdf_id = current_result["pdf_id"]
        
        # 2. Merge updates
        # update_data structure expected: {"partner_profile": {...}, "relationship_profile": {...}}
        if "partner_profile" in update_data:
            current_data["partner_profile"].update(update_data["partner_profile"])
        if "relationship_profile" in update_data:
            current_data["relationship_profile"].update(update_data["relationship_profile"])
            
        # Validate with Pydantic
        try:
            submission = OnboardingSubmission(**current_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid update data: {e}")
            
        # 3. Process updates (S3, Pinecone, DB) in background
        background_tasks.add_task(process_onboarding_task, submission, pdf_id)
        
        return {"success": True, "message": "Profile updating in background"}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"❌ Error updating profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))
