"""
Weekly Relationship Digest Service

Aggregates metrics from the past week and generates an AI narrative summary
with highlights and recommendations.
"""
import logging
from datetime import date, timedelta
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class WeeklyDigest(BaseModel):
    """AI-generated weekly relationship digest."""
    narrative: str = Field(..., description="2-3 paragraph narrative summary of the week")
    highlights: List[str] = Field(..., description="3-5 key highlights from the week")
    recommendations: List[str] = Field(..., description="2-3 actionable recommendations")


class DigestService:
    """Generates weekly relationship digests."""

    async def generate_weekly_digest(
        self,
        relationship_id: str,
        week_start: date = None,
        week_end: date = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a weekly digest for a relationship.
        Aggregates conflict data, Gottman scores, messaging trends, etc.
        """
        from app.services.db_service import db_service
        from app.services.llm_service import llm_service

        if week_end is None:
            week_end = date.today()
        if week_start is None:
            week_start = week_end - timedelta(days=7)

        logger.info(f"Generating digest for {relationship_id}: {week_start} to {week_end}")

        # Gather metrics
        metrics = {}

        try:
            # 1. Conflict count and resolution rate
            conflicts = db_service.get_previous_conflicts(relationship_id, limit=100)
            week_conflicts = [
                c for c in conflicts
                if c.get("started_at") and
                str(c["started_at"])[:10] >= str(week_start) and
                str(c["started_at"])[:10] <= str(week_end)
            ]
            resolved = sum(1 for c in week_conflicts if c.get("is_resolved"))
            metrics["conflict_count"] = len(week_conflicts)
            metrics["resolved_count"] = resolved
            metrics["resolution_rate"] = round(resolved / len(week_conflicts) * 100, 1) if week_conflicts else 0

            # 2. Partner names
            names = db_service.get_partner_names(relationship_id)
            partner_a_name = names.get("partner_a", "Partner A")
            partner_b_name = names.get("partner_b", "Partner B")
            metrics["partner_a_name"] = partner_a_name
            metrics["partner_b_name"] = partner_b_name

            # 3. Gottman scores (from analytics)
            try:
                from app.services.gottman_analysis_service import gottman_service
                gottman_scores = await gottman_service.get_relationship_scores(relationship_id)
                if gottman_scores:
                    metrics["gottman_health_score"] = float(gottman_scores.get("gottman_health_score", 0))
                    metrics["repair_success_rate"] = float(gottman_scores.get("overall_repair_success_rate", 0))
            except Exception as e:
                logger.warning(f"Could not fetch Gottman scores: {e}")

            # 4. Escalation risk
            try:
                from app.services.pattern_analysis_service import pattern_analysis_service
                risk = await pattern_analysis_service.calculate_escalation_risk(relationship_id)
                if risk:
                    metrics["escalation_risk_score"] = risk.risk_score
                    metrics["risk_level"] = risk.risk_level
            except Exception as e:
                logger.warning(f"Could not fetch escalation risk: {e}")

            # 5. Trigger phrases
            try:
                from app.services.pattern_analysis_service import pattern_analysis_service
                phrases = await pattern_analysis_service.find_trigger_phrase_patterns(relationship_id)
                if phrases:
                    metrics["top_triggers"] = phrases[:3] if isinstance(phrases, list) else []
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error gathering digest metrics: {e}")

        # Generate narrative using LLM
        try:
            prompt = f"""You are a relationship wellness advisor. Generate a weekly relationship digest
for {partner_a_name} and {partner_b_name} based on the following metrics from the past week:

Metrics:
- Conflicts this week: {metrics.get('conflict_count', 0)}
- Resolved: {metrics.get('resolved_count', 0)} ({metrics.get('resolution_rate', 0)}%)
- Gottman health score: {metrics.get('gottman_health_score', 'N/A')}
- Repair success rate: {metrics.get('repair_success_rate', 'N/A')}%
- Escalation risk: {metrics.get('risk_level', 'N/A')} ({metrics.get('escalation_risk_score', 'N/A')})

Be warm, supportive, and specific. Focus on growth and positive patterns.
If there were conflicts, acknowledge them constructively.
If data is limited, provide general relationship maintenance advice."""

            digest_result = llm_service.structured_output(
                messages=[
                    {"role": "system", "content": "You are Luna, a compassionate AI relationship advisor."},
                    {"role": "user", "content": prompt}
                ],
                response_model=WeeklyDigest,
                temperature=0.7,
            )

            # Store in database
            digest_id = db_service.create_digest(
                relationship_id=relationship_id,
                week_start=week_start,
                week_end=week_end,
                metrics=metrics,
                narrative=digest_result.narrative,
                highlights=digest_result.highlights,
                recommendations=digest_result.recommendations,
            )

            return {
                "id": digest_id,
                "relationship_id": relationship_id,
                "week_start": str(week_start),
                "week_end": str(week_end),
                "metrics": metrics,
                "narrative": digest_result.narrative,
                "highlights": digest_result.highlights,
                "recommendations": digest_result.recommendations,
            }

        except Exception as e:
            logger.error(f"Error generating digest narrative: {e}")
            # Store with metrics only
            digest_id = db_service.create_digest(
                relationship_id=relationship_id,
                week_start=week_start,
                week_end=week_end,
                metrics=metrics,
            )
            return {
                "id": digest_id,
                "relationship_id": relationship_id,
                "week_start": str(week_start),
                "week_end": str(week_end),
                "metrics": metrics,
                "narrative": None,
                "highlights": [],
                "recommendations": [],
            }


digest_service = DigestService()
