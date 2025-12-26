"""
Pattern Analysis Service - Phase 2
Analyzes conflict patterns, escalation risks, and relationships
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from statistics import mean

from app.models.schemas import (
    EscalationRiskReport,
    TriggerPhraseAnalysis,
    UnmetNeedRecurrence,
)
from app.services.db_service import db_service

logger = logging.getLogger(__name__)


class PatternAnalysisService:
    """Service for analyzing conflict patterns and escalation risks"""

    # Risk score weights
    UNRESOLVED_WEIGHT = 0.4
    RESENTMENT_WEIGHT = 0.3
    TIME_WEIGHT = 0.2
    RECURRENCE_WEIGHT = 0.1

    async def calculate_escalation_risk(
        self, relationship_id: str
    ) -> EscalationRiskReport:
        """
        Calculate escalation risk score for a relationship.

        Factors:
        1. Unresolved issues count (40%)
        2. Resentment accumulation (30%)
        3. Days since last conflict (20%)
        4. Recurrence pattern (10%)

        Returns score 0.0-1.0 with interpretation and recommendations.
        """
        try:
            logger.info(f"📊 Calculating escalation risk for {relationship_id}")

            # Get recent conflicts
            recent_conflicts = db_service.get_previous_conflicts(
                relationship_id, limit=20
            )

            if not recent_conflicts:
                return EscalationRiskReport(
                    risk_score=0.0,
                    interpretation="low",
                    unresolved_issues=0,
                    days_until_predicted_conflict=30,
                    factors={},
                    recommendations=[
                        "No previous conflicts recorded. Enjoy your harmony!",
                        "Continue open communication as new conflicts arise.",
                    ],
                )

            # Factor 1: Count unresolved issues
            unresolved_count = sum(
                1 for c in recent_conflicts if not c.get("is_resolved")
            )
            unresolved_score = min(unresolved_count / 5.0, 1.0)  # 5+ = max score

            # Factor 2: Resentment accumulation
            resentment_levels = [
                c.get("resentment_level", 5) for c in recent_conflicts
            ]
            avg_resentment = mean(resentment_levels) if resentment_levels else 5.0
            resentment_score = avg_resentment / 10.0

            # Factor 3: Time since last conflict
            last_conflict = recent_conflicts[0]
            last_conflict_date = last_conflict.get("started_at")
            if last_conflict_date:
                if isinstance(last_conflict_date, str):
                    last_conflict_date = datetime.fromisoformat(
                        last_conflict_date.replace("Z", "+00:00")
                    )
                days_since_last = (datetime.now(last_conflict_date.tzinfo) - last_conflict_date).days
            else:
                days_since_last = 30

            time_score = max(0, 1.0 - (days_since_last / 30.0))

            # Factor 4: Recurrence pattern
            recurrence_score = self._calculate_recurrence_score(recent_conflicts)

            # Calculate weighted risk score
            risk_score = (
                unresolved_score * self.UNRESOLVED_WEIGHT
                + resentment_score * self.RESENTMENT_WEIGHT
                + time_score * self.TIME_WEIGHT
                + recurrence_score * self.RECURRENCE_WEIGHT
            )

            # Interpret risk level
            if risk_score < 0.25:
                interpretation = "low"
            elif risk_score < 0.50:
                interpretation = "medium"
            elif risk_score < 0.75:
                interpretation = "high"
            else:
                interpretation = "critical"

            # Predict days until next conflict
            days_until_predicted = self._predict_next_conflict(recent_conflicts)

            # Generate recommendations
            recommendations = self._generate_recommendations(
                interpretation,
                unresolved_count,
                avg_resentment,
                recurrence_score,
                recent_conflicts,
            )

            logger.info(
                f"✅ Risk calculation complete: {interpretation} "
                f"({risk_score:.2f}), {unresolved_count} unresolved"
            )

            return EscalationRiskReport(
                risk_score=risk_score,
                interpretation=interpretation,
                unresolved_issues=unresolved_count,
                days_until_predicted_conflict=days_until_predicted,
                factors={
                    "unresolved_issues": unresolved_score,
                    "resentment_accumulation": resentment_score,
                    "time_since_conflict": time_score,
                    "recurrence_pattern": recurrence_score,
                    "avg_resentment": avg_resentment,
                    "days_since_last": days_since_last,
                },
                recommendations=recommendations,
            )

        except Exception as e:
            logger.error(f"❌ Error calculating escalation risk: {str(e)}")
            # Return safe default
            return EscalationRiskReport(
                risk_score=0.5,
                interpretation="unknown",
                unresolved_issues=0,
                days_until_predicted_conflict=7,
                factors={},
                recommendations=["Unable to calculate risk. Check system logs."],
            )

    def _calculate_recurrence_score(self, conflicts: List[Dict]) -> float:
        """Calculate recurrence pattern score"""
        if len(conflicts) < 2:
            return 0.0

        # Calculate intervals between conflicts
        intervals = []
        for i in range(len(conflicts) - 1):
            curr_date = conflicts[i].get("started_at")
            next_date = conflicts[i + 1].get("started_at")

            if curr_date and next_date:
                if isinstance(curr_date, str):
                    curr_date = datetime.fromisoformat(
                        curr_date.replace("Z", "+00:00")
                    )
                if isinstance(next_date, str):
                    next_date = datetime.fromisoformat(
                        next_date.replace("Z", "+00:00")
                    )

                days_between = (curr_date - next_date).days
                if days_between > 0:
                    intervals.append(days_between)

        if not intervals:
            return 0.3

        # Rapid recurrence = high score
        avg_interval = mean(intervals)
        if avg_interval <= 3:
            return 0.8  # Conflict every 3 days or less
        elif avg_interval <= 7:
            return 0.6  # Weekly
        elif avg_interval <= 14:
            return 0.4  # Bi-weekly
        else:
            return 0.2  # Monthly or less

    def _predict_next_conflict(self, conflicts: List[Dict]) -> int:
        """Predict days until next conflict based on pattern"""
        if len(conflicts) < 2:
            return 30  # Default to 30 days

        # Get interval between last 2 conflicts
        last_conflict = conflicts[0]
        second_last = conflicts[1] if len(conflicts) > 1 else None

        if not second_last:
            return 30

        last_date = last_conflict.get("started_at")
        second_date = second_last.get("started_at")

        if last_date and second_date:
            if isinstance(last_date, str):
                last_date = datetime.fromisoformat(last_date.replace("Z", "+00:00"))
            if isinstance(second_date, str):
                second_date = datetime.fromisoformat(
                    second_date.replace("Z", "+00:00")
                )

            days_between = (last_date - second_date).days
            return max(3, days_between)  # Minimum 3 days

        return 7

    def _generate_recommendations(
        self,
        interpretation: str,
        unresolved_count: int,
        avg_resentment: float,
        recurrence_score: float,
        recent_conflicts: List[Dict],
    ) -> List[str]:
        """Generate actionable recommendations based on risk factors"""
        recommendations = []

        # Based on interpretation
        if interpretation == "critical":
            recommendations.append(
                "🚨 High escalation risk - Schedule immediate mediation session with Luna"
            )
        elif interpretation == "high":
            recommendations.append(
                "⚠️ Elevated risk detected - Consider proactive conversation this week"
            )
        elif interpretation == "medium":
            recommendations.append(
                "📌 Moderate tension - Continue monitoring patterns"
            )

        # Based on unresolved issues
        if unresolved_count > 0:
            if unresolved_count >= 3:
                recommendations.append(
                    f"📋 You have {unresolved_count} unresolved issues. "
                    "Prioritize resolving the oldest one first."
                )
            else:
                recommendations.append(
                    f"💬 Address the {unresolved_count} unresolved issue(s) before new conflicts arise"
                )

        # Based on resentment
        if avg_resentment > 8:
            recommendations.append(
                "💔 High resentment detected - Focus on validating each other's feelings"
            )
        elif avg_resentment > 6:
            recommendations.append("😔 Resentment building - Have an appreciative conversation")

        # Based on recurrence
        if recurrence_score > 0.7:
            recommendations.append(
                "⏰ Conflicts are recurring rapidly - Identify and resolve root cause"
            )

        # Default recommendations
        if not recommendations:
            recommendations.append("✅ Continue open communication")

        recommendations.append("💬 Talk to Luna for personalized guidance")

        return recommendations

    async def find_trigger_phrase_patterns(
        self, relationship_id: str
    ) -> Dict[str, Any]:
        """Find most impactful trigger phrases and patterns"""
        try:
            logger.info(f"🎯 Analyzing trigger phrases for {relationship_id}")

            phrases = db_service.get_trigger_phrases_for_relationship(relationship_id)

            if not phrases:
                return {
                    "most_impactful": [],
                    "by_category": {},
                    "by_speaker": {},
                    "trends": [],
                }

            # Convert to proper format
            most_impactful = [
                TriggerPhraseAnalysis(
                    phrase=p.get("phrase"),
                    phrase_category=p.get("phrase_category", "unknown"),
                    usage_count=p.get("usage_count", 1),
                    avg_emotional_intensity=float(
                        p.get("avg_emotional_intensity", 5)
                    ),
                    escalation_rate=float(p.get("escalation_rate", 0.5)),
                    speaker=p.get("speaker"),
                    is_pattern_trigger=float(p.get("escalation_rate", 0)) > 0.7,
                )
                for p in phrases
            ]

            logger.info(f"✅ Found {len(most_impactful)} trigger phrases")

            return {
                "most_impactful": [p.model_dump() for p in most_impactful],
                "trends": self._calculate_phrase_trends(relationship_id),
            }

        except Exception as e:
            logger.error(f"❌ Error analyzing trigger phrases: {str(e)}")
            return {"most_impactful": [], "trends": []}

    def _calculate_phrase_trends(self, relationship_id: str) -> List[Dict]:
        """Calculate trends in trigger phrase usage"""
        # This would query time-series data
        # For now, return empty list - can be enhanced
        return []

    async def identify_conflict_chains(
        self, relationship_id: str
    ) -> List[Dict[str, Any]]:
        """Identify sequences of related conflicts (chains)"""
        try:
            logger.info(f"🔗 Identifying conflict chains for {relationship_id}")

            conflicts = db_service.get_previous_conflicts(relationship_id, limit=50)

            if not conflicts:
                return []

            # Build chains by tracing parent relationships
            chains = []
            processed = set()

            for conflict in conflicts:
                conflict_id = conflict.get("id")
                if conflict_id in processed:
                    continue

                # Trace back to root
                chain = []
                current = conflict
                while current:
                    chain.insert(0, current)
                    parent_id = current.get("parent_conflict_id")
                    if parent_id:
                        # Find parent in conflicts list
                        current = next(
                            (c for c in conflicts if c.get("id") == parent_id), None
                        )
                    else:
                        current = None

                if len(chain) > 1:  # Only include chains of 2+
                    chains.append(
                        {
                            "root_cause": chain[0].get("metadata", {}).get("topic"),
                            "conflicts_in_chain": len(chain),
                            "timeline": " → ".join(
                                [c.get("metadata", {}).get("topic", "?") for c in chain]
                            ),
                            "unmet_needs": chain[0].get("unmet_needs", []),
                            "resolution_attempts": sum(
                                1 for c in chain if c.get("is_resolved")
                            ),
                            "is_resolved": chain[-1].get("is_resolved", False),
                        }
                    )

                    for c in chain:
                        processed.add(c.get("id"))

            logger.info(f"✅ Found {len(chains)} conflict chains")
            return chains

        except Exception as e:
            logger.error(f"❌ Error identifying conflict chains: {str(e)}")
            return []

    async def track_chronic_needs(
        self, relationship_id: str
    ) -> List[UnmetNeedRecurrence]:
        """Track chronic unmet needs (appear in 3+ conflicts)"""
        try:
            logger.info(f"💔 Tracking chronic needs for {relationship_id}")

            needs = db_service.get_unmet_needs_for_relationship(relationship_id)

            if not needs:
                return []

            chronic_needs = []
            for need in needs:
                conflict_count = need.get("conflict_count", 0)

                # Only include chronic needs (3+ conflicts)
                if conflict_count >= 3:
                    chronic_needs.append(
                        UnmetNeedRecurrence(
                            need=need.get("need"),
                            conflict_count=conflict_count,
                            first_appeared=need.get("first_appeared"),
                            days_appeared_in=need.get("days_appeared_in", 0),
                            is_chronic=True,
                            percentage_of_conflicts=float(
                                need.get("percentage_of_conflicts", 0)
                            ),
                        )
                    )

            logger.info(f"✅ Found {len(chronic_needs)} chronic needs")
            return chronic_needs

        except Exception as e:
            logger.error(f"❌ Error tracking chronic needs: {str(e)}")
            return []


# Singleton instance
pattern_analysis_service = PatternAnalysisService()
