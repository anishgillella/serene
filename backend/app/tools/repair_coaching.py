"""
Repair coaching tool - generates personalized repair plans

ENHANCED: Now integrates messaging context from partner-to-partner messaging
for more personalized repair recommendations.
"""
import logging
import asyncio
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

# Import db_service for messaging context
try:
    from app.services.db_service import db_service
except ImportError:
    db_service = None
    logger.warning("DB service not available - repair plans won't include messaging context")

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
    include_calendar: bool = True,
    include_messaging: bool = True  # NEW: Include messaging context
) -> RepairPlan:
    """
    Generate a personalized repair plan for a conflict

    ENHANCED: Now integrates messaging context for more personalized recommendations.

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
        include_messaging: Whether to include messaging context (sentiment trends, patterns)

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
        # Fetch calendar context (cycle-aware timing recommendations)
        if include_calendar: # Only attempt if include_calendar is True
            logger.info(f"📅 Fetching calendar insights for repair plan timing...")
            calendar_context = ""
            if calendar_service:
                try:
                    # Add timeout to prevent blocking (calendar can be slow)
                    calendar_context = await asyncio.wait_for(
                        asyncio.to_thread(
                            calendar_service.get_calendar_insights_for_llm,
                            relationship_id or "00000000-0000-0000-0000-000000000000"
                        ),
                        timeout=3.0  # 3-second timeout (with caching, should be <0.1s on cache hit)
                    )
                    if calendar_context: # Only log if context was actually retrieved
                        logger.info(f"   ✅ Calendar context retrieved ({len(calendar_context)} chars)")
                    else:
                        logger.info(f"   ℹ️ No calendar context available.")
                except asyncio.TimeoutError:
                    logger.warning(f"   ⚠️ Calendar fetch timed out after 3s, proceeding without calendar context")
                    calendar_context = ""
                except Exception as e:
                    logger.warning(f"   ⚠️ Error fetching calendar context: {e}")
                    calendar_context = ""

        # NEW: Get messaging context for communication-aware repair plans
        messaging_context = None
        if include_messaging and db_service:
            logger.info(f"💬 Fetching messaging insights for repair plan...")
            try:
                # Get messaging analytics (last 30 days)
                messaging_analytics = await asyncio.wait_for(
                    asyncio.to_thread(
                        db_service.get_messaging_analytics,
                        relationship_id,
                        30  # days
                    ),
                    timeout=2.0
                )

                if messaging_analytics:
                    # Format messaging context for LLM
                    messaging_context = _format_messaging_context(messaging_analytics)
                    if messaging_context:
                        logger.info(f"   ✅ Messaging context retrieved ({len(messaging_context)} chars)")
                else:
                    logger.info(f"   ℹ️ No messaging analytics available.")
            except asyncio.TimeoutError:
                logger.warning(f"   ⚠️ Messaging analytics fetch timed out after 2s")
                messaging_context = None
            except Exception as e:
                logger.warning(f"   ⚠️ Error fetching messaging context: {e}")
                messaging_context = None

        # Generate repair plan using LLM with partner profiles, calendar, and messaging context
        repair_plan = await asyncio.to_thread(
            llm_service.generate_repair_plan,
            transcript_text=transcript_text,
            conflict_id=conflict_id,
            partner_requesting=partner_name,
            analysis_summary=analysis_summary,
            response_model=RepairPlan,
            boyfriend_profile=boyfriend_profile,
            girlfriend_profile=girlfriend_profile,
            calendar_context=calendar_context,
            messaging_context=messaging_context  # NEW: Pass messaging context
        )
        
        # Ensure fields are set
        repair_plan.conflict_id = conflict_id
        repair_plan.partner_requesting = partner_name
        
        logger.info(f"✅ Repair plan generated for conflict {conflict_id}")
        return repair_plan
        
    except Exception as e:
        logger.error(f"❌ Error generating repair plan: {e}")
        raise


def _format_messaging_context(analytics: dict) -> Optional[str]:
    """
    Format messaging analytics into a context string for the LLM.

    Args:
        analytics: Messaging analytics from db_service.get_messaging_analytics()

    Returns:
        Formatted context string, or None if no meaningful data
    """
    if not analytics:
        return None

    parts = []

    # Message counts
    total_messages = analytics.get("total_messages", 0)
    if total_messages > 0:
        parts.append(f"Total messages in last 30 days: {total_messages}")

    # Sentiment distribution
    sentiment = analytics.get("sentiment_distribution", {})
    if sentiment:
        positive = sentiment.get("positive", 0)
        negative = sentiment.get("negative", 0)
        neutral = sentiment.get("neutral", 0)
        total = positive + negative + neutral
        if total > 0:
            positive_pct = (positive / total) * 100
            negative_pct = (negative / total) * 100
            parts.append(f"Message sentiment: {positive_pct:.0f}% positive, {negative_pct:.0f}% negative")

            # Interpretation
            if positive_pct > 70:
                parts.append("Recent communication has been predominantly positive.")
            elif negative_pct > 40:
                parts.append("Recent communication has been tense - approach carefully.")

    # Top emotions
    emotions = analytics.get("top_emotions", [])
    if emotions:
        emotion_list = ", ".join(emotions[:5])
        parts.append(f"Common emotions in messages: {emotion_list}")

    # Escalation events
    escalation_count = analytics.get("escalation_count", 0)
    if escalation_count > 0:
        parts.append(f"Escalation events in messages: {escalation_count}")
        if escalation_count > 3:
            parts.append("Multiple escalation events detected - be gentle in approach.")

    # Gottman markers
    gottman = analytics.get("gottman_markers", {})
    if gottman:
        concerning = []
        if gottman.get("criticism_count", 0) > 2:
            concerning.append("criticism")
        if gottman.get("contempt_count", 0) > 0:
            concerning.append("contempt")
        if gottman.get("defensiveness_count", 0) > 2:
            concerning.append("defensiveness")
        if gottman.get("stonewalling_count", 0) > 0:
            concerning.append("stonewalling")

        if concerning:
            parts.append(f"Communication patterns to address: {', '.join(concerning)}")

    # Repair attempts
    repair_count = analytics.get("repair_attempt_count", 0)
    bid_count = analytics.get("bid_for_connection_count", 0)
    if repair_count > 0 or bid_count > 0:
        parts.append(f"Positive signs: {repair_count} repair attempts, {bid_count} bids for connection")

    if not parts:
        return None

    return "\n".join(parts)
