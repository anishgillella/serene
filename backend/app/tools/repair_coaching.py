"""
Repair coaching tool - generates personalized repair plans
"""
import logging
from datetime import datetime
from typing import Optional
from app.services.llm_service import llm_service
from app.services.embeddings_service import embeddings_service
from app.services.pinecone_service import pinecone_service
from app.models.schemas import RepairPlan, ConflictAnalysis

logger = logging.getLogger(__name__)

async def generate_repair_plan(
    conflict_id: str,
    transcript_text: str,
    partner_requesting_id: str,
    relationship_id: str,
    partner_a_id: str,
    partner_b_id: str,
    analysis: Optional[ConflictAnalysis] = None,
    boyfriend_profile: Optional[str] = None,
    girlfriend_profile: Optional[str] = None
) -> RepairPlan:
    """
    Generate a personalized repair plan for a conflict
    
    Args:
        conflict_id: Unique identifier for the conflict
        transcript_text: Full transcript text
        partner_requesting_id: ID of partner requesting the plan
        relationship_id: Relationship identifier
        partner_a_id: ID of partner A
        partner_b_id: ID of partner B
        analysis: Optional pre-computed analysis (will fetch if not provided)
    
    Returns:
        RepairPlan with actionable steps and apology script
    """
    try:
        logger.info(f"🔧 Generating repair plan for conflict {conflict_id}, partner {partner_requesting_id}")
        
        # Determine partner name (Boyfriend or Girlfriend)
        # For now, assume partner_requesting_id maps to a name
        partner_name = "Boyfriend" if partner_requesting_id == partner_a_id else "Girlfriend"
        
        # Get analysis if not provided
        if not analysis:
            # Try to fetch from Pinecone
            analysis_result = pinecone_service.get_by_conflict_id(
                conflict_id=conflict_id,
                namespace="analysis"
            )
            if analysis_result and analysis_result.metadata:
                # Reconstruct analysis from metadata (simplified)
                analysis_summary = analysis_result.metadata.get("fight_summary", "")
            else:
                analysis_summary = "Conflict analysis not available"
        else:
            analysis_summary = analysis.fight_summary
        
        # Generate repair plan using LLM with partner profiles
        repair_plan = llm_service.generate_repair_plan(
            transcript_text=transcript_text,
            conflict_id=conflict_id,
            partner_requesting=partner_name,
            analysis_summary=analysis_summary,
            response_model=RepairPlan,
            boyfriend_profile=boyfriend_profile,
            girlfriend_profile=girlfriend_profile
        )
        
        # Ensure fields are set
        repair_plan.conflict_id = conflict_id
        repair_plan.partner_requesting = partner_name
        
        logger.info(f"✅ Repair plan generated for conflict {conflict_id}")
        return repair_plan
        
    except Exception as e:
        logger.error(f"❌ Error generating repair plan: {e}")
        raise

