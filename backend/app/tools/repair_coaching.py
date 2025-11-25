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

# Import calendar service for timing awareness
try:
    from app.services.calendar_service import calendar_service
except ImportError:
    calendar_service = None
    logger.warning("Calendar service not available - repair plans won't include cycle awareness")

async def generate_repair_plan(
    conflict_id: str,
    transcript_text: str,
    partner_requesting_id: str,
    relationship_id: str,
    partner_a_id: str,
    partner_b_id: str,
    analysis: Optional[ConflictAnalysis] = None,
    boyfriend_profile: Optional[str] = None,
    girlfriend_profile: Optional[str] = None,
    include_calendar: bool = True  # NEW: Include calendar context
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
        boyfriend_profile: Optional boyfriend profile text
        girlfriend_profile: Optional girlfriend profile text
        include_calendar: Whether to include calendar/cycle context for timing
    
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
        
        # NEW: Get calendar context for timing-aware repair plans
        calendar_context = None
        if include_calendar and calendar_service:
            try:
                logger.info("📅 Fetching calendar insights for repair plan timing...")
                calendar_context = calendar_service.get_calendar_insights_for_llm(
                    relationship_id=relationship_id
                )
                if calendar_context and calendar_context != "No calendar insights available.":
                    logger.info(f"   ✅ Calendar context retrieved ({len(calendar_context)} chars)")
                else:
                    calendar_context = None
            except Exception as e:
                logger.warning(f"   ⚠️ Error fetching calendar context (non-fatal): {e}")
                calendar_context = None
        
        # Generate repair plan using LLM with partner profiles and calendar context
        repair_plan = llm_service.generate_repair_plan(
            transcript_text=transcript_text,
            conflict_id=conflict_id,
            partner_requesting=partner_name,
            analysis_summary=analysis_summary,
            response_model=RepairPlan,
            boyfriend_profile=boyfriend_profile,
            girlfriend_profile=girlfriend_profile,
            calendar_context=calendar_context  # NEW: Pass calendar context
        )
        
        # Ensure fields are set
        repair_plan.conflict_id = conflict_id
        repair_plan.partner_requesting = partner_name
        
        logger.info(f"✅ Repair plan generated for conflict {conflict_id}")
        return repair_plan
        
    except Exception as e:
        logger.error(f"❌ Error generating repair plan: {e}")
        raise

