"""
Analytics API Routes
Provides unified analytics data for the relationship dashboard
Includes Gottman metrics (Four Horsemen, repair attempts, etc.)
"""
import asyncio
import logging
import time
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from psycopg2.extras import RealDictCursor

from app.services.pattern_analysis_service import pattern_analysis_service
from app.services.db_service import db_service
from app.services.gottman_analysis_service import gottman_service
from app.services.advanced_analytics_service import advanced_analytics_service
from app.models.schemas import (
    SentimentShiftResponse,
    CommunicationGrowthResponse,
    FightFrequencyResponse,
    RecoveryTimeResponse,
    AttachmentStyleResponse,
    BidResponseRatioResponse,
    BidResponseConflictResponse,
    NarrativeInsightsResponse,
)

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

        # Calculate previous week's health score for delta comparison
        health_score_previous = None
        try:
            prev_risk = await pattern_analysis_service.calculate_escalation_risk(
                relationship_id, days_back=14
            )
            # Only use if we got a different window; fallback to same score
            if prev_risk and hasattr(prev_risk, 'risk_score'):
                health_score_previous = int((1.0 - prev_risk.risk_score) * 100)
        except Exception:
            pass  # Non-critical — skip if method doesn't support days_back

        return {
            "health_score": health_score,
            "health_score_previous": health_score_previous,
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


# ============================================================================
# ADVANCED METRICS - PHASE 1: COMPUTE FROM EXISTING DATA
# ============================================================================

@router.get("/advanced/sentiment-shift", response_model=SentimentShiftResponse)
async def get_sentiment_shift(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000")
):
    """
    Per-conflict sentiment shift score measuring emotional de-escalation.
    Compares avg intensity of first 3 messages vs last 3 messages.
    """
    try:
        logger.info(f"📊 Getting sentiment shift for {relationship_id}")

        with db_service.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Single query: compute start/end intensity per conflict
                # Uses window functions to rank messages and aggregate top/bottom 3
                cursor.execute("""
                    WITH ranked AS (
                        SELECT
                            et.conflict_id,
                            c.started_at,
                            et.emotional_intensity,
                            ROW_NUMBER() OVER (PARTITION BY et.conflict_id ORDER BY et.message_sequence ASC) as asc_rank,
                            ROW_NUMBER() OVER (PARTITION BY et.conflict_id ORDER BY et.message_sequence DESC) as desc_rank
                        FROM emotional_temperature et
                        INNER JOIN conflicts c ON c.id = et.conflict_id
                        WHERE c.relationship_id = %s
                    )
                    SELECT
                        conflict_id,
                        started_at,
                        AVG(CASE WHEN asc_rank <= 3 THEN emotional_intensity END) as start_intensity,
                        AVG(CASE WHEN desc_rank <= 3 THEN emotional_intensity END) as end_intensity
                    FROM ranked
                    GROUP BY conflict_id, started_at
                    ORDER BY started_at DESC;
                """, (relationship_id,))
                rows = cursor.fetchall()

        per_conflict = []
        for row in rows:
            start_i = float(row['start_intensity'] or 5)
            end_i = float(row['end_intensity'] or 5)
            shift = start_i - end_i  # positive = de-escalated

            per_conflict.append({
                "conflict_id": str(row['conflict_id']),
                "started_at": str(row['started_at']),
                "start_intensity": round(start_i, 2),
                "end_intensity": round(end_i, 2),
                "shift_score": round(shift, 2)
            })

        total_analyzed = len(per_conflict)
        avg_shift = round(sum(c['shift_score'] for c in per_conflict) / total_analyzed, 2) if total_analyzed > 0 else 0
        trend_direction = "improving" if avg_shift > 0.5 else "declining" if avg_shift < -0.5 else "stable"

        return {
            "has_data": total_analyzed > 0,
            "per_conflict": per_conflict,
            "aggregate": {
                "avg_shift": avg_shift,
                "trend_direction": trend_direction,
                "total_analyzed": total_analyzed
            }
        }
    except Exception as e:
        logger.error(f"❌ Error getting sentiment shift: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced/communication-growth", response_model=CommunicationGrowthResponse)
async def get_communication_growth(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000"),
    months: int = Query(default=6, ge=1, le=24)
):
    """
    Month-over-month growth trends for I-statement ratio, interruptions,
    active listening, and repair success from gottman_analysis.
    """
    try:
        logger.info(f"📊 Getting communication growth for {relationship_id} ({months} months)")

        with db_service.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT
                        DATE_TRUNC('month', c.started_at) as month,
                        COUNT(*) as conflicts_count,
                        COALESCE(SUM(g.partner_a_i_statements + g.partner_b_i_statements), 0) as total_i_statements,
                        COALESCE(SUM(g.partner_a_you_statements + g.partner_b_you_statements), 0) as total_you_statements,
                        COALESCE(SUM(g.interruption_count), 0) as total_interruptions,
                        COALESCE(SUM(g.active_listening_instances), 0) as total_active_listening,
                        COALESCE(SUM(g.repair_attempts_count), 0) as total_repair_attempts,
                        COALESCE(SUM(g.successful_repairs_count), 0) as total_successful_repairs
                    FROM conflicts c
                    LEFT JOIN gottman_analysis g ON g.conflict_id = c.id
                    WHERE c.relationship_id = %s
                      AND c.started_at >= NOW() - make_interval(months => %s)
                    GROUP BY DATE_TRUNC('month', c.started_at)
                    ORDER BY month ASC;
                """, (relationship_id, months))
                rows = cursor.fetchall()

        monthly_data = []
        for row in rows:
            total_statements = (row['total_i_statements'] or 0) + (row['total_you_statements'] or 0)
            i_ratio = round((row['total_i_statements'] or 0) / total_statements * 100, 1) if total_statements > 0 else 0
            repair_success = round((row['total_successful_repairs'] or 0) / (row['total_repair_attempts'] or 1) * 100, 1) if (row['total_repair_attempts'] or 0) > 0 else 0

            monthly_data.append({
                "month": str(row['month']),
                "conflicts_count": row['conflicts_count'],
                "i_statement_ratio": i_ratio,
                "interruptions_per_conflict": round((row['total_interruptions'] or 0) / max(row['conflicts_count'], 1), 1),
                "active_listening_per_conflict": round((row['total_active_listening'] or 0) / max(row['conflicts_count'], 1), 1),
                "repair_success_rate": repair_success
            })

        # Calculate month-over-month growth percentages
        growth_percentages = []
        for i in range(1, len(monthly_data)):
            prev = monthly_data[i - 1]
            curr = monthly_data[i]
            growth = {}
            for key in ['i_statement_ratio', 'interruptions_per_conflict', 'active_listening_per_conflict', 'repair_success_rate']:
                if prev[key] > 0:
                    growth[key] = round((curr[key] - prev[key]) / prev[key] * 100, 1)
                else:
                    growth[key] = 0
            growth['month'] = curr['month']
            growth_percentages.append(growth)

        return {
            "has_data": len(monthly_data) > 0,
            "monthly_data": monthly_data,
            "growth_percentages": growth_percentages
        }
    except Exception as e:
        logger.error(f"❌ Error getting communication growth: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced/fight-frequency", response_model=FightFrequencyResponse)
async def get_fight_frequency(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000"),
    period: str = Query(default="weekly", description="'weekly' or 'monthly'"),
    periods: int = Query(default=12, ge=1, le=52)
):
    """
    Weekly/monthly fight counts with resolution rates and avg duration.
    """
    try:
        logger.info(f"📊 Getting fight frequency for {relationship_id} ({period}, {periods} periods)")

        # Validate period to prevent injection — only allow known values
        if period not in ("weekly", "monthly"):
            raise HTTPException(status_code=400, detail="period must be 'weekly' or 'monthly'")

        trunc = "week" if period == "weekly" else "month"

        with db_service.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Use make_interval with named params for safe parameterization
                if period == "weekly":
                    cursor.execute("""
                        SELECT
                            DATE_TRUNC(%s, started_at) as period_start,
                            COUNT(*) as fight_count,
                            COUNT(*) FILTER (WHERE is_resolved = TRUE) as resolved_count,
                            AVG(EXTRACT(EPOCH FROM (ended_at - started_at)) / 60)
                                FILTER (WHERE ended_at IS NOT NULL) as avg_duration_minutes
                        FROM conflicts
                        WHERE relationship_id = %s
                          AND started_at >= NOW() - make_interval(weeks => %s)
                        GROUP BY DATE_TRUNC(%s, started_at)
                        ORDER BY period_start ASC;
                    """, (trunc, relationship_id, periods, trunc))
                else:
                    cursor.execute("""
                        SELECT
                            DATE_TRUNC(%s, started_at) as period_start,
                            COUNT(*) as fight_count,
                            COUNT(*) FILTER (WHERE is_resolved = TRUE) as resolved_count,
                            AVG(EXTRACT(EPOCH FROM (ended_at - started_at)) / 60)
                                FILTER (WHERE ended_at IS NOT NULL) as avg_duration_minutes
                        FROM conflicts
                        WHERE relationship_id = %s
                          AND started_at >= NOW() - make_interval(months => %s)
                        GROUP BY DATE_TRUNC(%s, started_at)
                        ORDER BY period_start ASC;
                    """, (trunc, relationship_id, periods, trunc))
                rows = cursor.fetchall()

                # Calculate average days between fights
                cursor.execute("""
                    SELECT started_at FROM conflicts
                    WHERE relationship_id = %s
                    ORDER BY started_at ASC;
                """, (relationship_id,))
                all_conflicts = cursor.fetchall()

        period_data = []
        for row in rows:
            period_data.append({
                "period_start": str(row['period_start']),
                "fight_count": row['fight_count'],
                "resolved_count": row['resolved_count'] or 0,
                "avg_duration_minutes": round(float(row['avg_duration_minutes'] or 0), 1)
            })

        # Calculate average days between fights
        avg_days_between = None
        if len(all_conflicts) > 1:
            gaps = []
            for i in range(1, len(all_conflicts)):
                gap = (all_conflicts[i]['started_at'] - all_conflicts[i-1]['started_at']).total_seconds() / 86400
                gaps.append(gap)
            avg_days_between = round(sum(gaps) / len(gaps), 1) if gaps else None

        return {
            "has_data": len(period_data) > 0,
            "period": period,
            "periods": period_data,
            "average_days_between": avg_days_between
        }
    except Exception as e:
        logger.error(f"❌ Error getting fight frequency: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced/recovery-time", response_model=RecoveryTimeResponse)
async def get_recovery_time(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000")
):
    """
    Days between conflict end and next positive daily check-in.
    Measures emotional recovery time.
    """
    try:
        logger.info(f"📊 Getting recovery time for {relationship_id}")

        with db_service.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT
                        c.id as conflict_id,
                        c.ended_at,
                        (
                            SELECT MIN(dc.checkin_date)
                            FROM daily_checkins dc
                            WHERE dc.relationship_id = c.relationship_id
                              AND dc.checkin_date > c.ended_at::date
                              AND dc.day_rating = 'positive'
                        ) as next_positive_date
                    FROM conflicts c
                    WHERE c.relationship_id = %s
                      AND c.ended_at IS NOT NULL
                    ORDER BY c.ended_at DESC;
                """, (relationship_id,))
                rows = cursor.fetchall()

        per_conflict = []
        recovery_days_list = []
        for row in rows:
            recovery_days = None
            if row['next_positive_date'] and row['ended_at']:
                delta = row['next_positive_date'] - row['ended_at'].date()
                recovery_days = delta.days
                recovery_days_list.append(recovery_days)

            per_conflict.append({
                "conflict_id": str(row['conflict_id']),
                "ended_at": str(row['ended_at']),
                "next_positive_date": str(row['next_positive_date']) if row['next_positive_date'] else None,
                "recovery_days": recovery_days
            })

        avg_recovery = round(sum(recovery_days_list) / len(recovery_days_list), 1) if recovery_days_list else None

        # Determine trend from last 3 vs previous 3
        trend = "stable"
        if len(recovery_days_list) >= 6:
            recent = sum(recovery_days_list[:3]) / 3
            older = sum(recovery_days_list[3:6]) / 3
            if recent < older - 0.5:
                trend = "improving"
            elif recent > older + 0.5:
                trend = "worsening"

        return {
            "has_data": len(per_conflict) > 0,
            "per_conflict": per_conflict,
            "average_recovery_days": avg_recovery,
            "trend": trend
        }
    except Exception as e:
        logger.error(f"❌ Error getting recovery time: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ADVANCED METRICS - PHASE 2: LLM-DEPENDENT
# ============================================================================

@router.get("/advanced/attachment-styles", response_model=AttachmentStyleResponse)
async def get_attachment_styles(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000"),
    refresh: bool = Query(default=False, description="Force re-analysis")
):
    """
    Get attachment style classification for each partner.
    Analyzes behavioral patterns across conflicts to determine
    secure/anxious/avoidant/fearful-avoidant tendencies.
    """
    try:
        logger.info(f"🔍 Getting attachment styles for {relationship_id}")

        if not refresh:
            # Check for existing data
            with db_service.get_db_context() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT * FROM attachment_style_tracking
                        WHERE relationship_id = %s
                        ORDER BY partner;
                    """, (relationship_id,))
                    rows = cursor.fetchall()

            if rows:
                partner_a = next((dict(r) for r in rows if r['partner'] == 'partner_a'), None)
                partner_b = next((dict(r) for r in rows if r['partner'] == 'partner_b'), None)
                return {
                    "has_data": True,
                    "partner_a": partner_a,
                    "partner_b": partner_b,
                    "interaction_dynamic": partner_a.get('interaction_dynamic') if partner_a else None
                }

        # Run analysis
        names = db_service.get_partner_names(relationship_id)
        result = await advanced_analytics_service.analyze_attachment_patterns(
            relationship_id=relationship_id,
            partner_a_name=names.get("partner_a", "Partner A"),
            partner_b_name=names.get("partner_b", "Partner B")
        )

        return {
            "has_data": True,
            "partner_a": result.get("partner_a"),
            "partner_b": result.get("partner_b"),
            "interaction_dynamic": result.get("interaction_dynamic")
        }
    except Exception as e:
        logger.error(f"❌ Error getting attachment styles: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced/bid-response-ratio", response_model=BidResponseRatioResponse)
async def get_bid_response_ratio(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000")
):
    """
    Get aggregated bid-response ratios across all conflicts.
    Tracks Gottman's 'bids for connection' — toward/away/against responses.
    """
    try:
        logger.info(f"📊 Getting bid-response ratio for {relationship_id}")

        result = await advanced_analytics_service.get_bid_response_ratios(relationship_id)
        return result
    except Exception as e:
        logger.error(f"❌ Error getting bid-response ratio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced/bid-response/{conflict_id}", response_model=BidResponseConflictResponse)
async def get_bid_response_for_conflict(
    conflict_id: str,
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000")
):
    """
    Get bid-response analysis for a specific conflict.
    """
    try:
        logger.info(f"📊 Getting bid-response for conflict {conflict_id}")

        with db_service.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM bid_response_tracking
                    WHERE conflict_id = %s
                    ORDER BY message_sequence;
                """, (conflict_id,))
                rows = cursor.fetchall()

        if rows:
            bids = [dict(r) for r in rows]
            toward = sum(1 for b in bids if b['response_type'] == 'toward')
            away = sum(1 for b in bids if b['response_type'] == 'away')
            against = sum(1 for b in bids if b['response_type'] == 'against')
            total = len(bids)

            return {
                "conflict_id": conflict_id,
                "has_data": True,
                "bids": bids,
                "summary": {
                    "total_bids": total,
                    "toward": toward,
                    "away": away,
                    "against": against,
                    "toward_rate": round(toward / total * 100, 1) if total > 0 else 0
                }
            }

        # Run analysis if no data
        transcript_data = db_service.get_conflict_transcript(conflict_id)
        if not transcript_data or not transcript_data.get("transcript_text"):
            raise HTTPException(status_code=404, detail="No transcript found")

        names = db_service.get_partner_names(relationship_id)
        result = await advanced_analytics_service.analyze_bid_response(
            conflict_id=conflict_id,
            transcript=transcript_data["transcript_text"],
            relationship_id=relationship_id,
            partner_a_name=names.get("partner_a", "Partner A"),
            partner_b_name=names.get("partner_b", "Partner B")
        )

        bids = result.bids if hasattr(result, 'bids') else []
        bid_dicts = [b.model_dump() for b in bids]
        toward = sum(1 for b in bids if b.response_type == 'toward')
        away = sum(1 for b in bids if b.response_type == 'away')
        against = sum(1 for b in bids if b.response_type == 'against')
        total = len(bids)

        return {
            "conflict_id": conflict_id,
            "has_data": True,
            "bids": bid_dicts,
            "summary": {
                "total_bids": total,
                "toward": toward,
                "away": away,
                "against": against,
                "toward_rate": round(toward / total * 100, 1) if total > 0 else 0
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting bid-response for conflict: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NARRATIVE INSIGHTS ENDPOINT
# ============================================================================

# Simple in-memory cache: { (relationship_id, viewer_role): (timestamp, result) }
_narrative_cache: dict = {}
_NARRATIVE_TTL_SECONDS = 300  # 5 minutes


from pydantic import BaseModel as PydanticBaseModel


class NarrativeInsightsRequest(PydanticBaseModel):
    """Frontend sends already-fetched metrics to avoid redundant DB calls."""
    relationship_id: str = "00000000-0000-0000-0000-000000000000"
    viewer_role: Optional[str] = None
    metrics: dict = {}  # All metric data the frontend already has


@router.post("/advanced/narrative-insights", response_model=NarrativeInsightsResponse)
async def post_narrative_insights(body: NarrativeInsightsRequest):
    """
    Generate AI narrative insights from metrics the frontend already fetched.
    Accepts a POST body with all metric data — no redundant DB round-trips.
    Results are cached for 5 minutes per (relationship_id, viewer_role).
    """
    try:
        relationship_id = body.relationship_id
        viewer_role = body.viewer_role
        logger.info(f"Generating narrative insights for {relationship_id}")

        # Validate viewer_role
        if viewer_role and viewer_role not in ("partner_a", "partner_b"):
            viewer_role = None

        # Check cache
        cache_key = (relationship_id, viewer_role)
        now = time.time()
        if cache_key in _narrative_cache:
            cached_at, cached_result = _narrative_cache[cache_key]
            if now - cached_at < _NARRATIVE_TTL_SECONDS:
                logger.info(f"Returning cached narrative insights (age={int(now - cached_at)}s)")
                return cached_result

        names = db_service.get_partner_names(relationship_id)
        partner_a_name = names.get("partner_a", "Partner A")
        partner_b_name = names.get("partner_b", "Partner B")

        insights = await advanced_analytics_service.generate_narrative_insights(
            metrics=body.metrics,
            partner_a_name=partner_a_name,
            partner_b_name=partner_b_name,
            viewer_role=viewer_role
        )

        result = {
            "has_data": True,
            "overview_digest": insights.overview_digest,
            "fight_quality_insight": insights.fight_quality_insight,
            "trigger_insight": insights.trigger_insight,
            "growth_insight": insights.growth_insight,
            "cross_metric_correlations": insights.cross_metric_correlations,
        }

        # Store in cache
        _narrative_cache[cache_key] = (now, result)

        return result
    except Exception as e:
        logger.error(f"Error generating narrative insights: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ADVANCED METRICS - PHASE 3: REPAIR PLAN COMPLIANCE
# ============================================================================

@router.get("/repair-compliance/{conflict_id}")
async def get_repair_compliance(
    conflict_id: str,
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000")
):
    """
    Get repair plan compliance checklist for a conflict.
    Auto-populates from repair plan if no records exist.
    """
    try:
        logger.info(f"📋 Getting repair compliance for {conflict_id}")

        with db_service.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Check for existing compliance records
                cursor.execute("""
                    SELECT * FROM repair_plan_compliance
                    WHERE conflict_id = %s
                    ORDER BY partner, step_index;
                """, (conflict_id,))
                rows = cursor.fetchall()

                if rows:
                    steps = [dict(r) for r in rows]
                    total = len(steps)
                    completed = sum(1 for s in steps if s['completed'])
                    return {
                        "conflict_id": conflict_id,
                        "has_data": True,
                        "steps": steps,
                        "progress": {
                            "total": total,
                            "completed": completed,
                            "percentage": round(completed / total * 100, 1) if total > 0 else 0
                        }
                    }

                # Auto-populate from repair_plans table
                cursor.execute("""
                    SELECT id, steps, partner_requesting
                    FROM repair_plans
                    WHERE conflict_id = %s
                    LIMIT 2;
                """, (conflict_id,))
                plans = cursor.fetchall()

                if not plans:
                    return {
                        "conflict_id": conflict_id,
                        "has_data": False,
                        "message": "No repair plan found for this conflict."
                    }

                # Create compliance records from repair plan steps
                all_steps = []
                for plan in plans:
                    plan_id = plan['id']
                    partner = plan.get('partner_requesting', 'partner_a')
                    steps_list = plan.get('steps', [])

                    # Handle both string lists and RepairStep objects
                    for idx, step in enumerate(steps_list):
                        step_desc = step if isinstance(step, str) else step.get('action', str(step))
                        cursor.execute("""
                            INSERT INTO repair_plan_compliance (
                                repair_plan_id, conflict_id, relationship_id,
                                partner, step_index, step_description
                            ) VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (repair_plan_id, step_index, partner) DO NOTHING
                            RETURNING *;
                        """, (plan_id, conflict_id, relationship_id, partner, idx, step_desc))
                        result = cursor.fetchone()
                        if result:
                            all_steps.append(dict(result))

                    conn.commit()

                return {
                    "conflict_id": conflict_id,
                    "has_data": len(all_steps) > 0,
                    "steps": all_steps,
                    "progress": {
                        "total": len(all_steps),
                        "completed": 0,
                        "percentage": 0
                    }
                }
    except Exception as e:
        logger.error(f"❌ Error getting repair compliance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/repair-compliance/{conflict_id}/update")
async def update_repair_compliance(
    conflict_id: str,
    step_id: str = Query(..., description="UUID of the compliance step"),
    completed: bool = Query(..., description="Mark step as done or undone"),
    notes: Optional[str] = Query(default=None)
):
    """
    Mark a repair plan step as completed or not completed.
    """
    try:
        logger.info(f"📋 Updating compliance step {step_id} -> completed={completed}")

        with db_service.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    UPDATE repair_plan_compliance
                    SET completed = %s,
                        completed_at = CASE WHEN %s THEN NOW() ELSE NULL END,
                        notes = COALESCE(%s, notes)
                    WHERE id = %s AND conflict_id = %s
                    RETURNING *;
                """, (completed, completed, notes, step_id, conflict_id))
                result = cursor.fetchone()
                conn.commit()

        if not result:
            raise HTTPException(status_code=404, detail="Step not found")

        return {
            "success": True,
            "step": dict(result)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating compliance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repair-compliance/summary")
async def get_repair_compliance_summary(
    relationship_id: str = Query(default="00000000-0000-0000-0000-000000000000")
):
    """
    Get overall repair plan compliance rate across all conflicts.
    """
    try:
        logger.info(f"📊 Getting compliance summary for {relationship_id}")

        with db_service.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_steps,
                        COUNT(*) FILTER (WHERE completed = TRUE) as completed_steps,
                        COUNT(DISTINCT conflict_id) as conflicts_with_plans
                    FROM repair_plan_compliance
                    WHERE relationship_id = %s;
                """, (relationship_id,))
                row = cursor.fetchone()

                # Per-conflict breakdown
                cursor.execute("""
                    SELECT
                        conflict_id,
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE completed = TRUE) as completed
                    FROM repair_plan_compliance
                    WHERE relationship_id = %s
                    GROUP BY conflict_id
                    ORDER BY MIN(created_at) DESC;
                """, (relationship_id,))
                per_conflict = cursor.fetchall()

        total = row['total_steps'] or 0
        completed = row['completed_steps'] or 0
        rate = round(completed / total * 100, 1) if total > 0 else 0

        return {
            "has_data": total > 0,
            "overall": {
                "total_steps": total,
                "completed_steps": completed,
                "compliance_rate": rate,
                "conflicts_with_plans": row['conflicts_with_plans'] or 0
            },
            "per_conflict": [dict(r) for r in per_conflict]
        }
    except Exception as e:
        logger.error(f"❌ Error getting compliance summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# COMPREHENSIVE ANALYSIS ENDPOINT
# ============================================================================

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
                "annotations": result.get("annotations") is not None,
                "bid_response": result.get("bid_response") is not None,
            }
        }
    except Exception as e:
        logger.error(f"❌ Error in full analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
