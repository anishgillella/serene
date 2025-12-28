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
    role: str # 'partner_a' | 'partner_b' (gender-neutral)
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
    # NEW: Repair-specific fields (Phase 1)
    apology_preferences: Optional[str] = ""
    post_conflict_need: Optional[str] = ""  # 'space' | 'connection' | 'depends'
    repair_gestures: Optional[List[str]] = []
    escalation_triggers: Optional[List[str]] = []

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

def generate_semantic_chunks(data: OnboardingSubmission) -> List[Dict[str, str]]:
    """
    Convert structured onboarding data into semantic chunks for RAG.
    Returns a list of dicts with 'section' and 'text'.
    """
    p = data.partner_profile
    r = data.relationship_profile
    
    chunks = []
    
    # Chunk 1: Identity & Basic Info
    identity_lines = []
    identity_lines.append(f"--- ONBOARDING PROFILE: {p.name} ({p.role}) ---")
    identity_lines.append(f"Name: {p.name}")
    identity_lines.append(f"Age: {p.age}")
    identity_lines.append(f"Role: {p.role}")
    chunks.append({"section": "identity", "text": "\n".join(identity_lines)})
    
    # Chunk 2: Background & Life Story
    background_lines = []
    background_lines.append(f"## Background & Life Story ({p.name})")
    background_lines.append(f"{p.background_story}")
    background_lines.append(f"Key Life Experiences: {p.key_life_experiences}")
    if p.traumatic_experiences:
        background_lines.append(f"Traumatic Experiences: {p.traumatic_experiences}")
    chunks.append({"section": "background", "text": "\n".join(background_lines)})
        
    # Chunk 3: Inner World & Personality
    personality_lines = []
    personality_lines.append(f"## Inner World & Personality ({p.name})")
    personality_lines.append(f"Communication Style: {p.communication_style}")
    personality_lines.append(f"Stress Triggers: {', '.join(p.stress_triggers)}")
    personality_lines.append(f"Soothing Mechanisms: {', '.join(p.soothing_mechanisms)}")
    chunks.append({"section": "personality", "text": "\n".join(personality_lines)})
    
    # Chunk 4: Interests & Favorites
    interests_lines = []
    interests_lines.append(f"## Interests & Favorites ({p.name})")
    interests_lines.append(f"Hobbies: {', '.join(p.hobbies)}")
    interests_lines.append(f"Favorite Food: {p.favorite_food} ({p.favorite_cuisine})")
    interests_lines.append(f"Favorite Books: {', '.join(p.favorite_books)}")
    interests_lines.append(f"Favorite Sports: {', '.join(p.favorite_sports)}")
    interests_lines.append(f"Favorite Celebrities: {', '.join(p.favorite_celebrities)}")
    chunks.append({"section": "interests", "text": "\n".join(interests_lines)})
    
    # Chunk 5: View on Partner
    partner_view_lines = []
    partner_view_lines.append(f"## View on Partner ({p.name})")
    partner_view_lines.append(f"Description of Partner: {p.partner_description}")
    partner_view_lines.append(f"Admired Qualities: {p.what_i_admire}")
    partner_view_lines.append(f"Frustrations: {p.what_frustrates_me}")
    chunks.append({"section": "partner_view", "text": "\n".join(partner_view_lines)})
    
    # Chunk 6: Relationship Dynamics
    dynamics_lines = []
    dynamics_lines.append(f"## Relationship Dynamics ({p.name})")
    dynamics_lines.append(f"Dynamic: {r.relationship_dynamic}")
    dynamics_lines.append(f"Recurring Arguments: {', '.join(r.recurring_arguments)}")
    dynamics_lines.append(f"Shared Goals: {', '.join(r.shared_goals)}")
    chunks.append({"section": "relationship", "text": "\n".join(dynamics_lines)})

    # Chunk 7: Repair & Conflict Preferences (NEW - Phase 1)
    repair_lines = []
    repair_lines.append(f"## Repair & Conflict Preferences ({p.name})")
    if p.apology_preferences:
        repair_lines.append(f"What makes an apology genuine to {p.name}: {p.apology_preferences}")
    if p.post_conflict_need:
        need_description = {
            'space': 'needs time alone to cool down and process',
            'connection': 'needs to feel close again right away',
            'depends': 'it depends on the situation'
        }.get(p.post_conflict_need, p.post_conflict_need)
        repair_lines.append(f"After a conflict, {p.name} {need_description}")
    if p.repair_gestures:
        repair_lines.append(f"Gestures that help {p.name} feel better: {', '.join(p.repair_gestures)}")
    if p.escalation_triggers:
        repair_lines.append(f"Things that make fights WORSE for {p.name}: {', '.join(p.escalation_triggers)}")
    # Also include existing soothing mechanisms and stress triggers for context
    if p.soothing_mechanisms:
        repair_lines.append(f"What calms {p.name} down: {', '.join(p.soothing_mechanisms)}")
    if p.stress_triggers:
        repair_lines.append(f"Stress triggers for {p.name}: {', '.join(p.stress_triggers)}")

    if len(repair_lines) > 1:  # More than just the header
        chunks.append({"section": "repair_preferences", "text": "\n".join(repair_lines)})

    return chunks

async def process_onboarding_task(data: OnboardingSubmission, pdf_id: str):
    """
    Background task to process onboarding data:
    1. Generate semantic chunks
    2. Embed and upsert to Pinecone (multiple vectors)
    3. Upload raw JSON to S3
    4. Update DB record
    """
    try:
        logger.info(f"🚀 Processing onboarding for {data.partner_profile.name} ({data.partner_id})")
        
        # 1. Generate Semantic Chunks
        chunks = generate_semantic_chunks(data)
        full_text_length = sum(len(c["text"]) for c in chunks)
        logger.info(f"📝 Generated {len(chunks)} semantic chunks (total {full_text_length} chars)")
        
        # 2. Parallelize Pinecone Upsert and S3 Upload
        import asyncio
        
        async def upsert_pinecone():
            vectors = []
            
            # Embed all chunks in batch (if supported) or loop
            # For simplicity and robustness, we'll loop here, but batching is better for perf
            for chunk in chunks:
                section = chunk["section"]
                text = chunk["text"]
                
                embedding = embeddings_service.embed_text(text)
                
                metadata = {
                    "pdf_id": pdf_id,
                    "relationship_id": data.relationship_id,
                    "partner_id": data.partner_id,
                    "pdf_type": "onboarding_profile",
                    "filename": "onboarding_questionnaire.json",
                    "text_length": len(text),
                    "extracted_text": text,
                    "name": data.partner_profile.name,
                    "role": data.partner_profile.role,
                    "section": section # Add section to metadata
                }
                
                vectors.append({
                    "id": f"onboarding_{pdf_id}_{section}",
                    "values": embedding,
                    "metadata": metadata
                })
            
            # Batch upsert
            if vectors:
                pinecone_service.index.upsert(
                    vectors=vectors,
                    namespace="profiles"
                )
                logger.info(f"✅ Upserted {len(vectors)} chunks to Pinecone (profiles namespace)")

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
                    "extracted_text_length": full_text_length,
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
