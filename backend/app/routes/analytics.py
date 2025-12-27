"""
Analytics API Routes
Provides unified analytics data for the relationship dashboard
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
from app.services.advanced_analytics_service import advanced_analytics_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


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


# ============================================================================
# ADVANCED ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/advanced/surface-underlying/{conflict_id}")
async def get_surface_underlying_analysis(
    conflict_id: str,
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000")
):
    """
    Get Surface vs Underlying Concerns analysis for a conflict.
    Maps what was said to what was really meant.
    """
    try:
        logger.info(f"🔍 Getting surface/underlying analysis for {conflict_id}")

        # Check if analysis exists
        with db_service.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM surface_underlying_mapping
                    WHERE conflict_id = %s
                    ORDER BY created_at;
                """, (conflict_id,))
                rows = cursor.fetchall()

        if rows:
            return {
                "conflict_id": conflict_id,
                "has_data": True,
                "mappings": [dict(r) for r in rows]
            }

        # Run analysis if not exists
        transcript_data = db_service.get_conflict_transcript(conflict_id)
        if not transcript_data or not transcript_data.get("transcript_text"):
            raise HTTPException(status_code=404, detail="No transcript found")

        names = db_service.get_partner_names(relationship_id)
        result = await advanced_analytics_service.analyze_surface_underlying(
            conflict_id=conflict_id,
            transcript=transcript_data["transcript_text"],
            relationship_id=relationship_id,
            partner_a_name=names.get("partner_a", "Partner A"),
            partner_b_name=names.get("partner_b", "Partner B")
        )

        return {
            "conflict_id": conflict_id,
            "has_data": True,
            "mappings": [m.model_dump() for m in result.mappings],
            "overall_pattern": result.overall_pattern,
            "key_insight": result.key_insight
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting surface/underlying: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced/emotional-timeline/{conflict_id}")
async def get_emotional_timeline(
    conflict_id: str,
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000")
):
    """
    Get Emotional Temperature Timeline for a conflict.
    Shows emotional intensity at each message.
    """
    try:
        logger.info(f"📈 Getting emotional timeline for {conflict_id}")

        # Check if analysis exists
        with db_service.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM emotional_temperature
                    WHERE conflict_id = %s
                    ORDER BY message_sequence;
                """, (conflict_id,))
                rows = cursor.fetchall()

        if rows:
            # Calculate summary
            moments = [dict(r) for r in rows]
            peak_moment = max(moments, key=lambda x: x['emotional_intensity'])
            return {
                "conflict_id": conflict_id,
                "has_data": True,
                "moments": moments,
                "summary": {
                    "peak_intensity": peak_moment['emotional_intensity'],
                    "peak_moment": peak_moment['message_sequence'],
                    "peak_emotion": peak_moment['primary_emotion'],
                    "total_escalations": sum(1 for m in moments if m['is_escalation_point']),
                    "total_repair_attempts": sum(1 for m in moments if m['is_repair_attempt']),
                    "total_de_escalations": sum(1 for m in moments if m['is_de_escalation'])
                }
            }

        # Run analysis if not exists
        transcript_data = db_service.get_conflict_transcript(conflict_id)
        if not transcript_data:
            raise HTTPException(status_code=404, detail="No transcript found")

        names = db_service.get_partner_names(relationship_id)
        result = await advanced_analytics_service.analyze_emotional_timeline(
            conflict_id=conflict_id,
            transcript=transcript_data.get("transcript_text", ""),
            relationship_id=relationship_id,
            messages=transcript_data.get("messages", []),
            partner_a_name=names.get("partner_a", "Partner A"),
            partner_b_name=names.get("partner_b", "Partner B")
        )

        return {
            "conflict_id": conflict_id,
            "has_data": True,
            "moments": [m.model_dump() for m in result.moments],
            "summary": {
                "peak_intensity_moment": result.peak_intensity_moment,
                "peak_emotion": result.peak_emotion,
                "total_escalations": result.total_escalations,
                "total_repair_attempts": result.total_repair_attempts,
                "successful_de_escalations": result.successful_de_escalations,
                "emotional_arc": result.emotional_arc
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting emotional timeline: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced/emotional-trends")
async def get_emotional_trends(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000"),
    period_type: str = Query(default="weekly", description="daily, weekly, or monthly"),
    periods: int = Query(default=8, ge=1, le=52)
):
    """
    Get emotional trends across multiple conflicts over time.
    Shows how emotional patterns are changing.
    """
    try:
        logger.info(f"📊 Getting emotional trends for {relationship_id}")
        trends = await advanced_analytics_service.get_emotional_trends(
            relationship_id=relationship_id,
            period_type=period_type,
            periods=periods
        )
        return {
            "relationship_id": relationship_id,
            "period_type": period_type,
            "trends": trends
        }
    except Exception as e:
        logger.error(f"❌ Error getting emotional trends: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced/trigger-sensitivity")
async def get_trigger_sensitivity(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000"),
    refresh: bool = Query(default=False, description="Force re-analysis")
):
    """
    Get Partner-Specific Trigger Sensitivity analysis.
    Shows what triggers each partner and how they react.
    """
    try:
        logger.info(f"🎯 Getting trigger sensitivity for {relationship_id}")

        if not refresh:
            # Check for existing data
            existing = await advanced_analytics_service.get_partner_sensitivities(relationship_id)
            if existing['partner_a_triggers'] or existing['partner_b_triggers']:
                return {
                    "relationship_id": relationship_id,
                    "has_data": True,
                    **existing
                }

        # Run analysis
        names = db_service.get_partner_names(relationship_id)
        result = await advanced_analytics_service.analyze_trigger_sensitivity(
            relationship_id=relationship_id,
            partner_a_name=names.get("partner_a", "Partner A"),
            partner_b_name=names.get("partner_b", "Partner B")
        )

        return {
            "relationship_id": relationship_id,
            "has_data": True,
            "partner_a_triggers": [t.model_dump() for t in result.partner_a_triggers],
            "partner_b_triggers": [t.model_dump() for t in result.partner_b_triggers],
            "cross_trigger_patterns": result.cross_trigger_patterns
        }
    except Exception as e:
        logger.error(f"❌ Error getting trigger sensitivity: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced/conflict-annotations/{conflict_id}")
async def get_conflict_annotations(
    conflict_id: str,
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000"),
    refresh: bool = Query(default=False, description="Force re-analysis")
):
    """
    Get Conflict Replay Annotations for a specific conflict.
    Marks escalation points, repair attempts, missed bids, and suggestions.
    """
    try:
        logger.info(f"📝 Getting annotations for {conflict_id}")

        if not refresh:
            # Check for existing annotations
            existing = await advanced_analytics_service.get_conflict_annotations(conflict_id)
            if existing:
                return {
                    "conflict_id": conflict_id,
                    "has_data": True,
                    "annotations": existing
                }

        # Run analysis
        transcript_data = db_service.get_conflict_transcript(conflict_id)
        if not transcript_data:
            raise HTTPException(status_code=404, detail="No transcript found")

        names = db_service.get_partner_names(relationship_id)
        result = await advanced_analytics_service.generate_conflict_annotations(
            conflict_id=conflict_id,
            transcript=transcript_data.get("transcript_text", ""),
            relationship_id=relationship_id,
            messages=transcript_data.get("messages", []),
            partner_a_name=names.get("partner_a", "Partner A"),
            partner_b_name=names.get("partner_b", "Partner B")
        )

        return {
            "conflict_id": conflict_id,
            "has_data": True,
            "annotations": [a.model_dump() for a in result.annotations],
            "key_turning_points": result.key_turning_points,
            "overall_assessment": result.overall_assessment,
            "primary_improvement_area": result.primary_improvement_area
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting annotations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced/conflict-replay/{conflict_id}")
async def get_conflict_replay(
    conflict_id: str,
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000")
):
    """
    Get full conflict replay data including transcript, emotional timeline, and annotations.
    Used by the frontend for the interactive conflict replay feature.
    """
    try:
        logger.info(f"🎬 Getting conflict replay for {conflict_id}")

        # Get transcript with messages
        transcript_data = db_service.get_conflict_transcript(conflict_id)
        if not transcript_data:
            raise HTTPException(status_code=404, detail="No transcript found")

        # Get emotional timeline
        with db_service.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM emotional_temperature
                    WHERE conflict_id = %s
                    ORDER BY message_sequence;
                """, (conflict_id,))
                emotional_data = [dict(r) for r in cursor.fetchall()]

                cursor.execute("""
                    SELECT * FROM conflict_annotations
                    WHERE conflict_id = %s
                    ORDER BY message_sequence_start;
                """, (conflict_id,))
                annotations = [dict(r) for r in cursor.fetchall()]

                cursor.execute("""
                    SELECT * FROM surface_underlying_mapping
                    WHERE conflict_id = %s;
                """, (conflict_id,))
                surface_underlying = [dict(r) for r in cursor.fetchall()]

        # Build replay data structure
        messages = transcript_data.get("messages", [])
        replay_messages = []
        for i, msg in enumerate(messages):
            seq = i + 1
            emotion = next((e for e in emotional_data if e['message_sequence'] == seq), None)
            msg_annotations = [a for a in annotations if a['message_sequence_start'] <= seq and (a['message_sequence_end'] is None or a['message_sequence_end'] >= seq)]

            replay_messages.append({
                "sequence": seq,
                "speaker": msg.get("partner_id"),
                "content": msg.get("content"),
                "timestamp": msg.get("created_at"),
                "emotional_intensity": emotion['emotional_intensity'] if emotion else None,
                "primary_emotion": emotion['primary_emotion'] if emotion else None,
                "is_escalation": emotion['is_escalation_point'] if emotion else False,
                "is_repair_attempt": emotion['is_repair_attempt'] if emotion else False,
                "annotations": msg_annotations
            })

        return {
            "conflict_id": conflict_id,
            "messages": replay_messages,
            "surface_underlying": surface_underlying,
            "summary": {
                "total_messages": len(messages),
                "has_emotional_data": len(emotional_data) > 0,
                "has_annotations": len(annotations) > 0,
                "annotation_count": len(annotations)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting conflict replay: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/advanced/analyze-conflict/{conflict_id}")
async def run_full_advanced_analysis(
    conflict_id: str,
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000")
):
    """
    Run all advanced analytics on a conflict.
    Includes surface/underlying, emotional timeline, and annotations.
    """
    try:
        logger.info(f"🚀 Running full advanced analysis for {conflict_id}")

        names = db_service.get_partner_names(relationship_id)
        result = await advanced_analytics_service.run_full_analysis(
            conflict_id=conflict_id,
            relationship_id=relationship_id,
            partner_a_name=names.get("partner_a", "Partner A"),
            partner_b_name=names.get("partner_b", "Partner B")
        )

        return {
            "success": True,
            "conflict_id": conflict_id,
            "analyses_completed": {
                "surface_underlying": result.get("surface_underlying") is not None,
                "emotional_timeline": result.get("emotional_timeline") is not None,
                "annotations": result.get("annotations") is not None
            }
        }
    except Exception as e:
        logger.error(f"❌ Error in full analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
