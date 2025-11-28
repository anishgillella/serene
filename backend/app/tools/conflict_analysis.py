"""
Conflict analysis tool - analyzes transcripts and extracts insights
"""
import logging
import time
from datetime import datetime
from typing import Optional
from app.services.llm_service import llm_service
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
    girlfriend_profile: Optional[str] = None,
    use_rag_context: bool = False
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
        analysis_start = time.time()
        logger.info(f"🔍 Analyzing conflict {conflict_id}")
        
        # Use LLM to extract structured analysis with partner profiles, personalized from partner's POV
        llm_start = time.time()
        # Run synchronous LLM call in a separate thread to avoid blocking the event loop
        import asyncio
        analysis = await asyncio.to_thread(
            llm_service.analyze_conflict,
            transcript_text=transcript_text,
            conflict_id=conflict_id,
            response_model=ConflictAnalysis,
            partner_id=partner_id,  # Pass partner_id for POV personalization
            boyfriend_profile=boyfriend_profile,
            girlfriend_profile=girlfriend_profile,
            use_rag_context=use_rag_context
        )
        llm_time = time.time() - llm_start
        
        # Ensure conflict_id is set
        analysis.conflict_id = conflict_id
        
        # NOTE: Storage (embedding + Pinecone + S3 + DB) happens ASYNCHRONOUSLY in background
        # after the response is sent to the frontend. This ensures results appear on screen immediately.
        # See: backend/app/routes/post_fight.py -> store_analysis_background()
        
        total_analysis_time = time.time() - analysis_start
        
        timing_breakdown = f"⏱️ Analysis timing breakdown: LLM API={llm_time:.2f}s, Total={total_analysis_time:.2f}s (Storage happens in background after response)"
        logger.info(timing_breakdown)
        print(timing_breakdown)  # Also print to stdout for visibility
        
        logger.info(f"✅ Analysis complete for conflict {conflict_id} (will be stored in background)")
        return analysis
        
    except Exception as e:
        logger.error(f"❌ Error analyzing conflict: {e}")
        raise

