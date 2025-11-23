"""
Conflict analysis tool - analyzes transcripts and extracts insights
"""
import logging
from datetime import datetime
from typing import Optional
from app.services.llm_service import llm_service
from app.services.embeddings_service import embeddings_service
from app.services.pinecone_service import pinecone_service
from app.services.reranker_service import reranker_service
from app.models.schemas import ConflictAnalysis

logger = logging.getLogger(__name__)

async def analyze_conflict_transcript(
    conflict_id: str,
    transcript_text: str,
    relationship_id: str,
    partner_a_id: str,
    partner_b_id: str,
    speaker_labels: dict,
    duration: float,
    timestamp: datetime,
    partner_id: Optional[str] = None,
    boyfriend_profile: Optional[str] = None,
    girlfriend_profile: Optional[str] = None
) -> ConflictAnalysis:
    """
    Analyze a conflict transcript and extract structured insights
    
    Args:
        conflict_id: Unique identifier for the conflict
        transcript_text: Full transcript text
        relationship_id: Relationship identifier
        partner_a_id: ID of partner A
        partner_b_id: ID of partner B
        speaker_labels: Mapping of speaker IDs to names
        duration: Duration in seconds
        timestamp: When the conflict occurred
        partner_id: Optional partner ID for personalized analysis
    
    Returns:
        ConflictAnalysis with structured insights
    """
    try:
        logger.info(f"🔍 Analyzing conflict {conflict_id}")
        
        # Use LLM to extract structured analysis with partner profiles, personalized from partner's POV
        analysis = llm_service.analyze_conflict(
            transcript_text=transcript_text,
            conflict_id=conflict_id,
            response_model=ConflictAnalysis,
            partner_id=partner_id,  # Pass partner_id for POV personalization
            boyfriend_profile=boyfriend_profile,
            girlfriend_profile=girlfriend_profile
        )
        
        # Ensure conflict_id is set
        analysis.conflict_id = conflict_id
        
        # Generate embedding for the analysis
        analysis_text = f"{analysis.fight_summary} {' '.join(analysis.root_causes)}"
        embedding = embeddings_service.embed_text(analysis_text)
        
        # Store analysis in Pinecone
        analysis_dict = analysis.model_dump()
        analysis_dict["analyzed_at"] = datetime.now()
        pinecone_service.upsert_analysis(
            conflict_id=conflict_id,
            embedding=embedding,
            analysis_data=analysis_dict,
            namespace="analysis"
        )
        
        logger.info(f"✅ Analysis complete for conflict {conflict_id}")
        return analysis
        
    except Exception as e:
        logger.error(f"❌ Error analyzing conflict: {e}")
        raise

