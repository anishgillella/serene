from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.schemas.onboarding import OnboardingSubmission, OnboardingResponse
from app.services.db_service import db_service
from app.services.embeddings_service import embeddings_service
from app.services.pinecone_service import pinecone_service
import logging

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])
logger = logging.getLogger(__name__)

def generate_partner_narrative(data) -> str:
    triggers = ", ".join(data.stress_triggers)
    soothing = ", ".join(data.soothing_mechanisms)
    hobbies = ", ".join(data.hobbies)
    sports = ", ".join(data.favorite_sports)
    books = ", ".join(data.favorite_books)
    celebs = ", ".join(data.favorite_celebrities)
    
    narrative = (
        f"{data.name} is a {data.age or 'unknown'} year old {data.role}. "
        f"Communication style: {data.communication_style}. "
        f"Triggers: {triggers}. "
        f"Soothing mechanisms: {soothing}. "
        f"Background: {data.background_story or ''}. "
    )
    
    if hobbies:
        narrative += f"Hobbies: {hobbies}. "
    if data.favorite_food:
        narrative += f"Favorite Food: {data.favorite_food}. "
    if data.favorite_cuisine:
        narrative += f"Favorite Cuisine: {data.favorite_cuisine}. "
    if sports:
        narrative += f"Favorite Sports: {sports}. "
    if books:
        narrative += f"Favorite Books: {books}. "
    if celebs:
        narrative += f"Favorite Celebrities: {celebs}. "
    if data.traumatic_experiences:
        narrative += f"Traumatic Experiences: {data.traumatic_experiences}. "
    if data.key_life_experiences:
        narrative += f"Key Life Experiences: {data.key_life_experiences}. "
        
    # Perspective on partner
    if data.partner_description:
        narrative += f"Description of Partner: {data.partner_description}. "
    if data.what_i_admire:
        narrative += f"Admires about Partner: {data.what_i_admire}. "
    if data.what_frustrates_me:
        narrative += f"Frustrated by Partner: {data.what_frustrates_me}. "
        
    return narrative

def generate_relationship_narrative(data) -> str:
    args = ", ".join(data.recurring_arguments)
    goals = ", ".join(data.shared_goals)
    return (
        f"Relationship Dynamic: {data.relationship_dynamic or 'Not specified'}. "
        f"Recurring Arguments: {args}. "
        f"Shared Goals: {goals}."
    )

async def process_onboarding_background(submission: OnboardingSubmission):
    try:
        # Define chunks for Partner Profile
        partner_data = submission.partner_profile
        
        chunks = []
        
        # 1. Basic Info Chunk
        basic_text = (
            f"Partner Basic Info: {partner_data.name} is a {partner_data.age or 'unknown'} year old {partner_data.role}. "
            f"Communication style: {partner_data.communication_style}. "
            f"Stress triggers: {', '.join(partner_data.stress_triggers)}. "
            f"Soothing mechanisms: {', '.join(partner_data.soothing_mechanisms)}."
        )
        chunks.append(("basic_info", basic_text))
        
        # 2. Background & History Chunk
        if partner_data.background_story or partner_data.traumatic_experiences or partner_data.key_life_experiences:
            background_text = (
                f"Partner Background & History: {partner_data.background_story or ''}. "
                f"Traumatic Experiences: {partner_data.traumatic_experiences or 'None'}. "
                f"Key Life Experiences: {partner_data.key_life_experiences or 'None'}."
            )
            chunks.append(("background", background_text))
            
        # 3. Preferences & Interests Chunk
        hobbies = ", ".join(partner_data.hobbies)
        sports = ", ".join(partner_data.favorite_sports)
        books = ", ".join(partner_data.favorite_books)
        celebs = ", ".join(partner_data.favorite_celebrities)
        
        if hobbies or sports or books or celebs or partner_data.favorite_food:
            prefs_text = (
                f"Partner Preferences & Interests: Hobbies: {hobbies}. "
                f"Favorite Food: {partner_data.favorite_food}. "
                f"Favorite Cuisine: {partner_data.favorite_cuisine}. "
                f"Favorite Sports: {sports}. "
                f"Favorite Books: {books}. "
                f"Favorite Celebrities: {celebs}."
            )
            chunks.append(("preferences", prefs_text))
            
        # 4. Partner Perspective Chunk
        if partner_data.partner_description or partner_data.what_i_admire or partner_data.what_frustrates_me:
            perspective_text = (
                f"Perspective on Partner: Description: {partner_data.partner_description}. "
                f"Admires: {partner_data.what_i_admire}. "
                f"Frustrations: {partner_data.what_frustrates_me}."
            )
            chunks.append(("perspective", perspective_text))
            
        # Process Partner Chunks
        vectors_to_upsert = []
        
        for chunk_type, text in chunks:
            embedding = embeddings_service.embed_text(text)
            vectors_to_upsert.append({
                "id": f"profile_{submission.relationship_id}_{submission.partner_id}_{chunk_type}",
                "values": embedding,
                "metadata": {
                    "type": "partner_profile",
                    "subtype": chunk_type,
                    "relationship_id": submission.relationship_id,
                    "partner_id": submission.partner_id,
                    "text": text
                }
            })
            
        # Process Relationship Profile (Keep as one chunk for now, usually smaller)
        rel_data = submission.relationship_profile
        rel_text = generate_relationship_narrative(rel_data)
        rel_embedding = embeddings_service.embed_text(rel_text)
        
        vectors_to_upsert.append({
            "id": f"relationship_{submission.relationship_id}",
            "values": rel_embedding,
            "metadata": {
                "type": "relationship_profile",
                "relationship_id": submission.relationship_id,
                "text": rel_text,
                "structured_data": rel_data.model_dump_json()
            }
        })
        
        # Upsert all
        pinecone_service.index.upsert(
            vectors=vectors_to_upsert,
            namespace="profiles"
        )
        
        logger.info(f"✅ Processed onboarding embeddings for {submission.relationship_id} ({len(vectors_to_upsert)} chunks)")
        
    except Exception as e:
        logger.error(f"❌ Error in onboarding background task: {e}")

@router.post("/submit", response_model=OnboardingResponse)
async def submit_onboarding(submission: OnboardingSubmission, background_tasks: BackgroundTasks):
    try:
        # 1. Save to Postgres
        db_service.upsert_partner_profile(
            submission.relationship_id,
            submission.partner_id,
            submission.partner_profile.model_dump()
        )
        
        db_service.upsert_relationship_profile(
            submission.relationship_id,
            submission.relationship_profile.model_dump()
        )
        
        # 2. Trigger Background Processing (Embeddings)
        background_tasks.add_task(process_onboarding_background, submission)
        
        return OnboardingResponse(
            success=True,
            message="Profile saved successfully",
            profile_id=f"{submission.relationship_id}_{submission.partner_id}"
        )
        
    except Exception as e:
        logger.error(f"❌ Error submitting onboarding: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{relationship_id}/{partner_id}")
async def get_onboarding_status(relationship_id: str, partner_id: str):
    """Check if a partner has completed onboarding"""
    try:
        profile = db_service.get_partner_profile(relationship_id, partner_id)
        return {"completed": profile is not None, "profile": profile}
    except Exception as e:
        logger.error(f"❌ Error checking status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
