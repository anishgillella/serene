"""
Mediator Context Routes - Phase 3
Provides context for Luna's mediation
"""
import logging
from fastapi import APIRouter, HTTPException, Path, Body
from typing import Optional

from app.services.pattern_analysis_service import pattern_analysis_service
from app.services.db_service import db_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mediator", tags=["mediator"])


@router.get("/context/{conflict_id}")
async def get_mediation_context(conflict_id: str = Path(...)):
    """
    Get enriched context for Luna's mediation
    
    Returns:
    - current_conflict: current fight details
    - unresolved_issues: list of unresolved conflicts
    - chronic_needs: core recurring needs
    - high_impact_triggers: escalation triggers
    - escalation_risk: risk assessment
    """
    try:
        logger.info(f"🔗 Getting mediation context for {conflict_id}")
        
        # Get the current conflict
        current_conflict = db_service.get_conflict(conflict_id)
        if not current_conflict:
            raise HTTPException(status_code=404, detail="Conflict not found")
        
        relationship_id = current_conflict.get("relationship_id")
        
        # Get all unresolved issues
        all_conflicts = db_service.get_previous_conflicts(relationship_id, limit=20)
        unresolved_issues = [
            {
                "conflict_id": c.get("id"),
                "topic": c.get("metadata", {}).get("topic"),
                "days_unresolved": (db_service._get_days_since(c.get("started_at")) if c.get("started_at") else 0),
                "resentment_level": c.get("resentment_level", 5),
                "unmet_needs": c.get("unmet_needs", [])
            }
            for c in all_conflicts if not c.get("is_resolved")
        ]
        
        # Get chronic needs
        chronic_needs_objs = await pattern_analysis_service.track_chronic_needs(relationship_id)
        chronic_needs = [n.need for n in chronic_needs_objs[:3]]
        
        # Get high-impact triggers
        phrases_analysis = await pattern_analysis_service.find_trigger_phrase_patterns(relationship_id)
        high_impact_triggers = [
            {
                "phrase": p["phrase"],
                "category": p["phrase_category"],
                "escalation_rate": p["escalation_rate"]
            }
            for p in phrases_analysis.get("most_impactful", [])[:5]
        ]
        
        # Get escalation risk
        risk_report = await pattern_analysis_service.calculate_escalation_risk(relationship_id)
        
        return {
            "current_conflict": {
                "topic": current_conflict.get("metadata", {}).get("topic"),
                "resentment_level": current_conflict.get("resentment_level", 5),
                "unmet_needs": current_conflict.get("unmet_needs", []),
            },
            "unresolved_issues": unresolved_issues[:5],
            "chronic_needs": chronic_needs,
            "high_impact_triggers": high_impact_triggers,
            "escalation_risk": {
                "score": risk_report.risk_score,
                "interpretation": risk_report.interpretation,
                "is_critical": risk_report.risk_score > 0.75,
            },
            "active_chains": [],
        }
    except Exception as e:
        logger.error(f"❌ Error getting mediation context: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enhance-response")
async def enhance_luna_response(
    conflict_id: str = Body(...),
    response: str = Body(...),
    user_message: Optional[str] = Body(None)
):
    """
    Enhance Luna's response with relationship context

    Uses mediation context to suggest improvements or risk warnings
    """
    try:
        logger.info(f"💡 Enhancing Luna response for conflict {conflict_id}")

        # Get mediation context
        context = await get_mediation_context(conflict_id)

        # Check for risk patterns in response
        enhancements = {
            "original_response": response,
            "suggestions": [],
            "risk_warnings": [],
            "context_applied": []
        }

        # Risk escalation warning
        escalation = context.get("escalation_risk", {})
        if escalation.get("is_critical"):
            enhancements["risk_warnings"].append({
                "type": "critical_escalation",
                "message": "Relationship is at critical escalation risk. Consider suggesting a break or recommending professional help.",
                "severity": "high"
            })
            enhancements["context_applied"].append("escalation_risk")

        # Trigger phrase warning
        triggers = context.get("high_impact_triggers", [])
        if triggers:
            trigger_phrases = [t.get("phrase", "") for t in triggers[:3]]
            if any(phrase.lower() in response.lower() for phrase in trigger_phrases):
                enhancements["risk_warnings"].append({
                    "type": "trigger_phrase_detected",
                    "message": f"Response contains known escalation trigger: {', '.join(trigger_phrases)}",
                    "severity": "medium"
                })
                enhancements["context_applied"].append("trigger_phrases")

        # Chronic needs suggestion
        chronic_needs = context.get("chronic_needs", [])
        if chronic_needs and user_message:
            if not any(need in response.lower() for need in chronic_needs):
                enhancements["suggestions"].append({
                    "type": "address_chronic_needs",
                    "message": f"Consider addressing chronic unmet needs: {', '.join(chronic_needs)}",
                    "needs": chronic_needs
                })
                enhancements["context_applied"].append("chronic_needs")

        # Unresolved issues connection
        unresolved = context.get("unresolved_issues", [])
        if unresolved and len(unresolved) > 2:
            enhancements["suggestions"].append({
                "type": "connect_to_past",
                "message": f"This may be connected to {len(unresolved)} other unresolved issues. Help them see the pattern.",
                "unresolved_count": len(unresolved)
            })
            enhancements["context_applied"].append("unresolved_issues")

        logger.info(f"✅ Response enhancement complete. Applied {len(enhancements['context_applied'])} context elements.")

        return enhancements

    except Exception as e:
        logger.error(f"❌ Error enhancing response: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
