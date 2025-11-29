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
        # 1. Generate Narratives
        partner_text = generate_partner_narrative(submission.partner_profile)
        relationship_text = generate_relationship_narrative(submission.relationship_profile)
        
        # 2. Generate Embeddings
        partner_embedding = embeddings_service.embed_text(partner_text)
        relationship_embedding = embeddings_service.embed_text(relationship_text)
        
        # 3. Store in Pinecone (Namespace: profiles)
        # Partner Vector
        pinecone_service.index.upsert(
            vectors=[{
                "id": f"profile_{submission.relationship_id}_{submission.partner_id}",
                "values": partner_embedding,
                "metadata": {
                    "type": "partner_profile",
                    "relationship_id": submission.relationship_id,
                    "partner_id": submission.partner_id,
                    "text": partner_text,
                    "structured_data": submission.partner_profile.model_dump_json()
                }
            }],
            namespace="profiles"
        )
        
        # Relationship Vector (Overwrite is fine, or merge? For now overwrite)
        pinecone_service.index.upsert(
            vectors=[{
                "id": f"relationship_{submission.relationship_id}",
                "values": relationship_embedding,
                "metadata": {
                    "type": "relationship_profile",
                    "relationship_id": submission.relationship_id,
                    "text": relationship_text,
                    "structured_data": submission.relationship_profile.model_dump_json()
                }
            }],
            namespace="profiles"
        )
        
        logger.info(f"✅ Processed onboarding embeddings for {submission.relationship_id}")
        
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
