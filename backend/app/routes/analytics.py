"""
Analytics API Routes - Phase 2
Provides analytics data for dashboard and visualizations
"""
import logging
from fastapi import APIRouter, Query, HTTPException

from app.services.pattern_analysis_service import pattern_analysis_service
from app.services.db_service import db_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/escalation-risk")
async def get_escalation_risk(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000")
):
    """Get escalation risk assessment for a relationship"""
    try:
        logger.info(f"📊 Getting escalation risk for {relationship_id}")
        risk_report = await pattern_analysis_service.calculate_escalation_risk(
            relationship_id
        )
        return risk_report.model_dump()
    except Exception as e:
        logger.error(f"❌ Error getting escalation risk: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trigger-phrases")
async def get_trigger_phrases(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000")
):
    """Get trigger phrase analysis with patterns"""
    try:
        logger.info(f"🎯 Getting trigger phrases for {relationship_id}")
        analysis = await pattern_analysis_service.find_trigger_phrase_patterns(
            relationship_id
        )
        return analysis
    except Exception as e:
        logger.error(f"❌ Error getting trigger phrases: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conflict-chains")
async def get_conflict_chains(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000")
):
    """Get identified conflict chains (related conflicts)"""
    try:
        logger.info(f"🔗 Getting conflict chains for {relationship_id}")
        chains = await pattern_analysis_service.identify_conflict_chains(
            relationship_id
        )
        return {"chains": chains}
    except Exception as e:
        logger.error(f"❌ Error getting conflict chains: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unmet-needs")
async def get_unmet_needs(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000")
):
    """Get chronic unmet needs (appearing in 3+ conflicts)"""
    try:
        logger.info(f"💔 Getting unmet needs for {relationship_id}")
        needs = await pattern_analysis_service.track_chronic_needs(relationship_id)
        return {"chronic_needs": [n.model_dump() for n in needs]}
    except Exception as e:
        logger.error(f"❌ Error getting unmet needs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health-score")
async def get_health_score(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000")
):
    """Get relationship health score (0-100)"""
    try:
        logger.info(f"📈 Calculating health score for {relationship_id}")
        risk_report = await pattern_analysis_service.calculate_escalation_risk(
            relationship_id
        )
        health_score = int((1.0 - risk_report.risk_score) * 100)
        recent_conflicts = db_service.get_previous_conflicts(relationship_id, limit=20)
        
        if len(recent_conflicts) >= 2:
            recent_unresolved = sum(
                1 for c in recent_conflicts[:5] if not c.get("is_resolved")
            )
            older_unresolved = sum(
                1 for c in recent_conflicts[5:10] if not c.get("is_resolved")
            )
            if recent_unresolved < older_unresolved:
                trend = "up"
            elif recent_unresolved > older_unresolved:
                trend = "down"
            else:
                trend = "stable"
        else:
            trend = "stable"

        return {
            "value": health_score,
            "trend": trend,
            "breakdownFactors": {
                "unresolved_issues": risk_report.factors.get("unresolved_issues", 0),
                "conflict_frequency": risk_report.factors.get("recurrence_pattern", 0),
                "escalation_risk": risk_report.risk_score,
                "resentment_level": risk_report.factors.get("avg_resentment", 5),
            },
        }
    except Exception as e:
        logger.error(f"❌ Error calculating health score: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_dashboard_data(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000")
):
    """Get comprehensive dashboard data"""
    try:
        logger.info(f"📊 Getting dashboard data for {relationship_id}")
        risk_report = await pattern_analysis_service.calculate_escalation_risk(
            relationship_id
        )
        phrases = await pattern_analysis_service.find_trigger_phrase_patterns(
            relationship_id
        )
        chains = await pattern_analysis_service.identify_conflict_chains(relationship_id)
        needs = await pattern_analysis_service.track_chronic_needs(relationship_id)

        recent_conflicts = db_service.get_previous_conflicts(relationship_id, limit=30)
        total_conflicts = len(recent_conflicts)
        resolved_count = sum(1 for c in recent_conflicts if c.get("is_resolved"))
        resolution_rate = (
            (resolved_count / total_conflicts * 100) if total_conflicts > 0 else 0
        )

        health_score = int((1.0 - risk_report.risk_score) * 100)

        return {
            "health_score": health_score,
            "escalation_risk": risk_report.model_dump(),
            "trigger_phrases": phrases,
            "conflict_chains": chains,
            "chronic_needs": [n.model_dump() for n in needs],
            "metrics": {
                "total_conflicts": total_conflicts,
                "resolved_conflicts": resolved_count,
                "unresolved_conflicts": total_conflicts - resolved_count,
                "resolution_rate": resolution_rate,
                "avg_resentment": risk_report.factors.get("avg_resentment", 5),
                "days_since_last_conflict": risk_report.factors.get("days_since_last", 0),
            },
            "insights": [
                f"Total conflicts: {total_conflicts}",
                f"Resolution rate: {resolution_rate:.0f}%",
                f"Unresolved issues: {risk_report.unresolved_issues}",
                f"Chronic unmet needs: {len(needs)}",
            ],
        }
    except Exception as e:
        logger.error(f"❌ Error getting dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
