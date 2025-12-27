"""
Analytics API Routes - Phase 2
Provides analytics data for dashboard and visualizations
Includes Gottman metrics (Four Horsemen, repair attempts, etc.)
"""
import asyncio
import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from psycopg2.extras import RealDictCursor

from app.services.pattern_analysis_service import pattern_analysis_service
from app.services.db_service import db_service
from app.services.gottman_analysis_service import gottman_service

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


# ============================================================================
# GOTTMAN ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/gottman/relationship/{relationship_id}")
async def get_gottman_relationship_scores(
    relationship_id: str
):
    """
    Get aggregated Gottman scores for a relationship.
    Includes Four Horsemen averages, repair success rate, and Gottman health score.
    """
    try:
        logger.info(f"🔬 Getting Gottman scores for {relationship_id}")
        scores = await gottman_service.get_relationship_scores(relationship_id)

        # Get aggregated communication metrics from gottman_analysis table
        comm_stats = await _get_aggregated_communication_stats(relationship_id)

        if not scores:
            # Return empty/default structure if no data yet
            return {
                "has_data": False,
                "message": "No Gottman analysis data yet. Run analysis on conflicts first.",
                "gottman_health_score": None,
                "four_horsemen": {
                    "criticism": 0,
                    "contempt": 0,
                    "defensiveness": 0,
                    "stonewalling": 0,
                    "total": 0
                },
                "repair_metrics": {
                    "success_rate": 0,
                    "total_attempts": 0,
                    "successful": 0
                },
                "communication_stats": comm_stats,
                "conflicts_analyzed": 0
            }

        return {
            "has_data": True,
            "gottman_health_score": float(scores.get("gottman_health_score", 0)),
            "four_horsemen": {
                "criticism": float(scores.get("avg_criticism_score", 0)),
                "contempt": float(scores.get("avg_contempt_score", 0)),
                "defensiveness": float(scores.get("avg_defensiveness_score", 0)),
                "stonewalling": float(scores.get("avg_stonewalling_score", 0)),
                "total": float(scores.get("total_horsemen_score", 0)),
                "trend": scores.get("horsemen_trend", "stable")
            },
            "repair_metrics": {
                "success_rate": float(scores.get("overall_repair_success_rate", 0)),
                "total_attempts": scores.get("total_repair_attempts", 0),
                "successful": scores.get("total_successful_repairs", 0)
            },
            "partner_patterns": {
                "partner_a_dominant_horseman": scores.get("partner_a_dominant_horseman"),
                "partner_b_dominant_horseman": scores.get("partner_b_dominant_horseman"),
                "partner_a_i_to_you_ratio": float(scores.get("partner_a_i_to_you_ratio", 1.0)),
                "partner_b_i_to_you_ratio": float(scores.get("partner_b_i_to_you_ratio", 1.0))
            },
            "communication_stats": comm_stats,
            "conflicts_analyzed": scores.get("conflicts_analyzed", 0),
            "last_calculated_at": scores.get("last_calculated_at")
        }
    except Exception as e:
        logger.error(f"❌ Error getting Gottman scores: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def _get_aggregated_communication_stats(relationship_id: str) -> dict:
    """Get aggregated communication stats from gottman_analysis table"""
    try:
        with db_service.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT
                        COALESCE(SUM(partner_a_i_statements), 0) as partner_a_i_statements,
                        COALESCE(SUM(partner_a_you_statements), 0) as partner_a_you_statements,
                        COALESCE(SUM(partner_b_i_statements), 0) as partner_b_i_statements,
                        COALESCE(SUM(partner_b_you_statements), 0) as partner_b_you_statements,
                        COALESCE(SUM(interruption_count), 0) as total_interruptions,
                        COALESCE(SUM(active_listening_instances), 0) as total_active_listening
                    FROM gottman_analysis
                    WHERE relationship_id = %s;
                """, (relationship_id,))
                row = cursor.fetchone()

        if row:
            return {
                "partner_a": {
                    "i_statements": int(row["partner_a_i_statements"]),
                    "you_statements": int(row["partner_a_you_statements"])
                },
                "partner_b": {
                    "i_statements": int(row["partner_b_i_statements"]),
                    "you_statements": int(row["partner_b_you_statements"])
                },
                "interruptions": int(row["total_interruptions"]),
                "active_listening": int(row["total_active_listening"])
            }
        return {
            "partner_a": {"i_statements": 0, "you_statements": 0},
            "partner_b": {"i_statements": 0, "you_statements": 0},
            "interruptions": 0,
            "active_listening": 0
        }
    except Exception as e:
        logger.error(f"Error getting communication stats: {str(e)}")
        return {
            "partner_a": {"i_statements": 0, "you_statements": 0},
            "partner_b": {"i_statements": 0, "you_statements": 0},
            "interruptions": 0,
            "active_listening": 0
        }


@router.get("/gottman/conflict/{conflict_id}")
async def get_gottman_conflict_analysis(
    conflict_id: str
):
    """
    Get Gottman analysis for a specific conflict.
    Returns detailed Four Horsemen instances, repair attempts, and communication metrics.
    """
    try:
        logger.info(f"🔬 Getting Gottman analysis for conflict {conflict_id}")
        analysis = await gottman_service.get_conflict_analysis(conflict_id)

        if not analysis:
            raise HTTPException(
                status_code=404,
                detail=f"No Gottman analysis found for conflict {conflict_id}"
            )

        return {
            "conflict_id": conflict_id,
            "four_horsemen": {
                "criticism": {
                    "score": analysis.get("criticism_score", 0),
                    "instances": analysis.get("partner_a_horsemen", []) + analysis.get("partner_b_horsemen", [])
                },
                "contempt": {"score": analysis.get("contempt_score", 0)},
                "defensiveness": {"score": analysis.get("defensiveness_score", 0)},
                "stonewalling": {"score": analysis.get("stonewalling_score", 0)}
            },
            "partner_a_horsemen": analysis.get("partner_a_horsemen", []),
            "partner_b_horsemen": analysis.get("partner_b_horsemen", []),
            "repair_attempts": {
                "count": analysis.get("repair_attempts_count", 0),
                "successful": analysis.get("successful_repairs_count", 0),
                "details": analysis.get("repair_attempt_details", [])
            },
            "communication": {
                "partner_a_i_statements": analysis.get("partner_a_i_statements", 0),
                "partner_a_you_statements": analysis.get("partner_a_you_statements", 0),
                "partner_b_i_statements": analysis.get("partner_b_i_statements", 0),
                "partner_b_you_statements": analysis.get("partner_b_you_statements", 0),
                "interruptions": analysis.get("interruption_count", 0),
                "active_listening": analysis.get("active_listening_instances", 0)
            },
            "emotional_flooding": {
                "detected": analysis.get("emotional_flooding_detected", False),
                "affected_partner": analysis.get("flooding_partner")
            },
            "interactions": {
                "positive": analysis.get("positive_interactions", 0),
                "negative": analysis.get("negative_interactions", 0)
            },
            "assessment": {
                "primary_issue": analysis.get("primary_issue"),
                "most_concerning_horseman": analysis.get("most_concerning_horseman"),
                "repair_effectiveness": analysis.get("repair_effectiveness"),
                "recommended_focus": analysis.get("recommended_focus")
            },
            "analyzed_at": analysis.get("analyzed_at")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting conflict analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gottman/analyze/{conflict_id}")
async def analyze_conflict_gottman(
    conflict_id: str,
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000")
):
    """
    Run Gottman analysis on a specific conflict.
    This will extract Four Horsemen, repair attempts, and communication metrics.
    """
    try:
        logger.info(f"🔬 Running Gottman analysis for conflict {conflict_id}")

        # Get transcript
        transcript_data = db_service.get_conflict_transcript(conflict_id)

        if not transcript_data or not transcript_data.get("transcript_text"):
            raise HTTPException(
                status_code=404,
                detail=f"No transcript found for conflict {conflict_id}"
            )

        # Get partner names
        names = db_service.get_partner_names(relationship_id)

        # Run analysis
        result = await gottman_service.analyze_conflict(
            conflict_id=conflict_id,
            transcript=transcript_data["transcript_text"],
            relationship_id=relationship_id,
            partner_a_name=names.get("partner_a", "Partner A"),
            partner_b_name=names.get("partner_b", "Partner B")
        )

        return {
            "success": True,
            "conflict_id": conflict_id,
            "analysis": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error analyzing conflict: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gottman/backfill")
async def backfill_gottman_analysis(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000"),
    batch_size: int = Query(default=10, ge=1, le=20, description="Number of conflicts to process in parallel"),
    include_enrichment: bool = Query(default=True, description="Also backfill trigger phrases and unmet needs"),
    run_in_background: bool = Query(default=False, description="Run in background and return immediately")
):
    """
    Backfill Gottman analysis + trigger phrases + unmet needs for all conflicts.
    Runs in parallel batches for efficiency.
    Set run_in_background=true to return immediately while processing continues.
    """
    try:
        logger.info(f"🔄 Starting Gottman backfill for {relationship_id} (batch_size={batch_size}, background={run_in_background})")

        if run_in_background:
            # Fire and forget - run in background
            asyncio.create_task(gottman_service.backfill_async_background(
                relationship_id=relationship_id,
                batch_size=batch_size
            ))
            return {
                "success": True,
                "relationship_id": relationship_id,
                "message": "Backfill started in background. Check logs for progress.",
                "status": "running"
            }
        else:
            # Wait for completion
            results = await gottman_service.backfill_all_conflicts(
                relationship_id=relationship_id,
                batch_size=batch_size,
                include_enrichment=include_enrichment
            )

            return {
                "success": True,
                "relationship_id": relationship_id,
                "results": results
            }
    except Exception as e:
        logger.error(f"❌ Error in backfill: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DAILY CHECK-IN ENDPOINTS (for 5:1 ratio tracking)
# ============================================================================

@router.post("/checkin")
async def create_daily_checkin(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000"),
    partner_id: str = Query(..., description="'partner_a' or 'partner_b'"),
    day_rating: str = Query(..., description="'positive', 'neutral', or 'negative'"),
    positive_moments: int = Query(default=0),
    negative_moments: int = Query(default=0),
    appreciation_given: bool = Query(default=False),
    notes: Optional[str] = Query(default=None)
):
    """
    Submit a daily check-in for tracking the 5:1 positive/negative ratio.
    This is optional but provides more accurate relationship health metrics.
    """
    try:
        logger.info(f"📝 Creating check-in for {partner_id} in {relationship_id}")

        # Validate inputs
        if partner_id not in ["partner_a", "partner_b"]:
            raise HTTPException(status_code=400, detail="partner_id must be 'partner_a' or 'partner_b'")

        if day_rating not in ["positive", "neutral", "negative"]:
            raise HTTPException(status_code=400, detail="day_rating must be 'positive', 'neutral', or 'negative'")

        # Save to database
        with db_service.get_db_context() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO daily_checkins (
                        relationship_id, partner_id, checkin_date,
                        day_rating, positive_moments, negative_moments,
                        appreciation_given, notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (relationship_id, partner_id, checkin_date)
                    DO UPDATE SET
                        day_rating = EXCLUDED.day_rating,
                        positive_moments = EXCLUDED.positive_moments,
                        negative_moments = EXCLUDED.negative_moments,
                        appreciation_given = EXCLUDED.appreciation_given,
                        notes = EXCLUDED.notes,
                        updated_at = NOW()
                    RETURNING id;
                """, (
                    relationship_id, partner_id, date.today(),
                    day_rating, positive_moments, negative_moments,
                    appreciation_given, notes
                ))
                checkin_id = cursor.fetchone()[0]
                conn.commit()

        return {
            "success": True,
            "checkin_id": str(checkin_id),
            "date": str(date.today())
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating check-in: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positivity-ratio")
async def get_positivity_ratio(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000"),
    days: int = Query(default=30, ge=7, le=365)
):
    """
    Get the positive/negative interaction ratio based on daily check-ins.
    The healthy "magic ratio" per Gottman research is 5:1 or higher.
    """
    try:
        logger.info(f"📊 Getting positivity ratio for {relationship_id} (last {days} days)")

        start_date = date.today() - timedelta(days=days)

        with db_service.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT
                        COUNT(*) FILTER (WHERE day_rating = 'positive') as positive_days,
                        COUNT(*) FILTER (WHERE day_rating = 'negative') as negative_days,
                        COUNT(*) FILTER (WHERE day_rating = 'neutral') as neutral_days,
                        SUM(positive_moments) as total_positive_moments,
                        SUM(negative_moments) as total_negative_moments,
                        COUNT(*) as total_checkins
                    FROM daily_checkins
                    WHERE relationship_id = %s
                      AND checkin_date >= %s;
                """, (relationship_id, start_date))

                row = cursor.fetchone()

        if not row or row["total_checkins"] == 0:
            return {
                "has_data": False,
                "message": f"No check-ins in the last {days} days. Start checking in daily for ratio tracking.",
                "ratio": None,
                "is_healthy": None
            }

        positive = (row["positive_days"] or 0) + (row["total_positive_moments"] or 0)
        negative = (row["negative_days"] or 0) + (row["total_negative_moments"] or 0)

        # Calculate ratio (avoid division by zero)
        if negative > 0:
            ratio = positive / negative
        elif positive > 0:
            ratio = positive  # Infinite ratio, cap at positive count
        else:
            ratio = 0

        return {
            "has_data": True,
            "period_days": days,
            "ratio": round(ratio, 2),
            "is_healthy": ratio >= 5.0,
            "target_ratio": 5.0,
            "breakdown": {
                "positive_days": row["positive_days"] or 0,
                "negative_days": row["negative_days"] or 0,
                "neutral_days": row["neutral_days"] or 0,
                "positive_moments": row["total_positive_moments"] or 0,
                "negative_moments": row["total_negative_moments"] or 0,
                "total_checkins": row["total_checkins"]
            },
            "interpretation": (
                "Excellent! Your ratio exceeds the 5:1 healthy threshold." if ratio >= 5 else
                "Good, but aim for more positive interactions." if ratio >= 3 else
                "Concerning - focus on increasing positive moments." if ratio >= 1 else
                "Critical - seek support to improve your relationship dynamics."
            )
        }
    except Exception as e:
        logger.error(f"❌ Error getting positivity ratio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
