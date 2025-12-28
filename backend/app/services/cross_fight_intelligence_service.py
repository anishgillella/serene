"""
Cross-Fight Intelligence Service (Phase 4)

Aggregates learnings across ALL past fights without requiring user feedback:
1. Pattern Aggregation - identifies recurring triggers and effective techniques
2. Similar Fight Retrieval - finds past fights with similar dynamics
3. Repair Outcome Inference - infers if past repair plans worked
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import json

from app.services.pinecone_service import pinecone_service
from app.services.embeddings_service import embeddings_service
from app.services.db_service import db_service
from app.services.s3_service import s3_service
from app.models.schemas import (
    CrossFightIntelligence,
    EscalationTriggerPattern,
    DeescalationTechnique,
    RecurringTopic,
    RepairOutcomeInference,
    SimilarFightResult,
    FightDebrief
)

logger = logging.getLogger(__name__)


class CrossFightIntelligenceService:
    """Service for aggregating intelligence across all past fights"""

    def __init__(self):
        self.pinecone = pinecone_service
        self.embeddings = embeddings_service
        self.db = db_service
        self.s3 = s3_service
        logger.info("✅ Initialized Cross-Fight Intelligence Service")

    async def get_all_debriefs(
        self,
        relationship_id: str,
        days_back: int = 90
    ) -> List[FightDebrief]:
        """
        Fetch all FightDebriefs for a relationship from S3/Pinecone.

        Args:
            relationship_id: The relationship UUID
            days_back: How many days of history to analyze

        Returns:
            List of FightDebrief objects
        """
        debriefs = []

        try:
            # Query Pinecone for all debriefs in this relationship
            # Use a generic query to get all debriefs
            dummy_embedding = [0.0] * 1024

            results = self.pinecone.index.query(
                vector=dummy_embedding,
                top_k=100,  # Get up to 100 past fights
                namespace="debriefs",
                include_metadata=True,
                filter={"relationship_id": {"$eq": relationship_id}}
            )

            if not results or not results.matches:
                logger.info(f"No debriefs found for relationship {relationship_id}")
                return []

            # Fetch full debrief from S3 for each match
            for match in results.matches:
                try:
                    conflict_id = match.metadata.get("conflict_id")
                    if not conflict_id:
                        continue

                    # Try to get from S3
                    debrief_path = f"debriefs/{relationship_id}/{conflict_id}_debrief.json"
                    content = self.s3.download_file(debrief_path)

                    if content:
                        debrief_data = json.loads(content)
                        debrief = FightDebrief(**debrief_data)

                        # Check if within date range
                        analyzed_at = debrief.analyzed_at
                        if isinstance(analyzed_at, str):
                            analyzed_at = datetime.fromisoformat(analyzed_at.replace('Z', '+00:00'))

                        cutoff = datetime.now() - timedelta(days=days_back)
                        if analyzed_at.replace(tzinfo=None) >= cutoff:
                            debriefs.append(debrief)

                except Exception as e:
                    logger.warning(f"Could not load debrief for conflict: {e}")
                    continue

            logger.info(f"✅ Retrieved {len(debriefs)} debriefs for relationship {relationship_id}")
            return debriefs

        except Exception as e:
            logger.error(f"❌ Error fetching debriefs: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def aggregate_escalation_triggers(
        self,
        debriefs: List[FightDebrief]
    ) -> List[EscalationTriggerPattern]:
        """
        Analyze all debriefs to find phrases/behaviors that consistently escalate fights.

        Returns:
            List of EscalationTriggerPattern sorted by escalation rate
        """
        trigger_counts = defaultdict(lambda: {
            "occurrences": 0,
            "conflicts": [],
            "speakers": defaultdict(int)
        })

        for debrief in debriefs:
            # Collect phrases to avoid from each debrief
            for phrase in debrief.phrases_to_avoid:
                # Normalize the phrase
                normalized = phrase.lower().strip()
                trigger_counts[normalized]["occurrences"] += 1
                trigger_counts[normalized]["conflicts"].append(debrief.conflict_id)

                # Track who says it from repair attempts
                for attempt in debrief.repair_attempts:
                    if attempt.outcome == "hurt" and phrase.lower() in attempt.what_they_said_or_did.lower():
                        trigger_counts[normalized]["speakers"][attempt.speaker] += 1

        # Convert to EscalationTriggerPattern objects
        patterns = []
        total_fights = len(debriefs)

        for phrase, data in trigger_counts.items():
            if data["occurrences"] >= 2:  # Only include if seen at least twice
                # Determine who typically says it
                speaker_counts = data["speakers"]
                if speaker_counts.get("partner_a", 0) > speaker_counts.get("partner_b", 0):
                    who = "partner_a"
                elif speaker_counts.get("partner_b", 0) > speaker_counts.get("partner_a", 0):
                    who = "partner_b"
                else:
                    who = "both"

                patterns.append(EscalationTriggerPattern(
                    trigger_phrase=phrase,
                    occurrence_count=data["occurrences"],
                    total_fights_analyzed=total_fights,
                    escalation_rate=data["occurrences"] / total_fights if total_fights > 0 else 0.0,
                    example_conflicts=data["conflicts"][:5],  # Limit to 5 examples
                    who_typically_says_it=who
                ))

        # Sort by escalation rate (highest first)
        patterns.sort(key=lambda x: x.escalation_rate, reverse=True)
        return patterns[:10]  # Return top 10

    def aggregate_deescalation_techniques(
        self,
        debriefs: List[FightDebrief]
    ) -> List[DeescalationTechnique]:
        """
        Analyze all debriefs to find techniques that successfully de-escalate fights.

        Returns:
            List of DeescalationTechnique sorted by success rate
        """
        technique_stats = defaultdict(lambda: {
            "success": 0,
            "attempts": 0,
            "action_types": defaultdict(int),
            "speakers": defaultdict(int),
            "timings": []
        })

        for debrief in debriefs:
            # Collect phrases that helped
            for phrase in debrief.phrases_that_helped:
                normalized = phrase.lower().strip()
                technique_stats[normalized]["success"] += 1
                technique_stats[normalized]["attempts"] += 1

            # Analyze repair attempts
            for i, attempt in enumerate(debrief.repair_attempts):
                normalized = attempt.what_they_said_or_did.lower().strip()[:100]  # First 100 chars
                technique_stats[normalized]["attempts"] += 1
                technique_stats[normalized]["action_types"][attempt.action_type] += 1
                technique_stats[normalized]["speakers"][attempt.speaker] += 1

                if attempt.outcome == "helped":
                    technique_stats[normalized]["success"] += 1

                    # Track timing (early, mid, late in fight)
                    total_attempts = len(debrief.repair_attempts)
                    if total_attempts > 0:
                        position = i / total_attempts
                        if position < 0.33:
                            technique_stats[normalized]["timings"].append("early")
                        elif position < 0.66:
                            technique_stats[normalized]["timings"].append("mid")
                        else:
                            technique_stats[normalized]["timings"].append("late")

        # Convert to DeescalationTechnique objects
        techniques = []

        for technique, stats in technique_stats.items():
            if stats["attempts"] >= 2:  # Only include if tried at least twice
                # Determine most common action type
                action_types = stats["action_types"]
                action_type = max(action_types, key=action_types.get) if action_types else "other"

                # Determine who typically uses it
                speakers = stats["speakers"]
                if speakers.get("partner_a", 0) > speakers.get("partner_b", 0):
                    who = "partner_a"
                elif speakers.get("partner_b", 0) > speakers.get("partner_a", 0):
                    who = "partner_b"
                else:
                    who = "both"

                # Determine best timing
                timings = stats["timings"]
                best_timing = None
                if timings:
                    timing_counts = defaultdict(int)
                    for t in timings:
                        timing_counts[t] += 1
                    best_timing = max(timing_counts, key=timing_counts.get)

                success_rate = stats["success"] / stats["attempts"] if stats["attempts"] > 0 else 0.0

                techniques.append(DeescalationTechnique(
                    technique=technique[:200],  # Limit length
                    success_count=stats["success"],
                    attempt_count=stats["attempts"],
                    success_rate=success_rate,
                    action_type=action_type,
                    who_typically_uses_it=who,
                    best_timing=best_timing
                ))

        # Sort by success rate (highest first), then by attempt count
        techniques.sort(key=lambda x: (x.success_rate, x.attempt_count), reverse=True)
        return techniques[:10]  # Return top 10

    def aggregate_recurring_topics(
        self,
        debriefs: List[FightDebrief]
    ) -> List[RecurringTopic]:
        """
        Identify topics that come up repeatedly in conflicts.

        Returns:
            List of RecurringTopic sorted by occurrence count
        """
        topic_stats = defaultdict(lambda: {
            "count": 0,
            "dates": [],
            "resolutions": [],
            "intensities": [],
            "needs_a": [],
            "needs_b": []
        })

        for debrief in debriefs:
            topic = debrief.topic.lower().strip()
            topic_stats[topic]["count"] += 1
            topic_stats[topic]["dates"].append(str(debrief.analyzed_at))
            topic_stats[topic]["resolutions"].append(debrief.resolution_status)
            topic_stats[topic]["intensities"].append(debrief.intensity_peak)
            topic_stats[topic]["needs_a"].extend(debrief.unmet_needs_partner_a)
            topic_stats[topic]["needs_b"].extend(debrief.unmet_needs_partner_b)

        # Convert to RecurringTopic objects
        topics = []

        for topic, stats in topic_stats.items():
            if stats["count"] >= 2:  # Only include if occurred at least twice
                dates = sorted(stats["dates"])
                resolutions = stats["resolutions"]
                resolved_count = sum(1 for r in resolutions if r == "resolved")
                resolution_rate = resolved_count / len(resolutions) if resolutions else 0.0

                # Calculate average intensity
                intensity_map = {"low": 1, "medium": 2, "high": 3, "explosive": 4}
                intensities = [intensity_map.get(i, 2) for i in stats["intensities"]]
                avg_intensity_num = sum(intensities) / len(intensities) if intensities else 2
                if avg_intensity_num < 1.5:
                    avg_intensity = "low"
                elif avg_intensity_num < 2.5:
                    avg_intensity = "medium"
                else:
                    avg_intensity = "high"

                # Get most common underlying needs
                needs_a = stats["needs_a"]
                needs_b = stats["needs_b"]
                common_need_a = max(set(needs_a), key=needs_a.count) if needs_a else None
                common_need_b = max(set(needs_b), key=needs_b.count) if needs_b else None

                topics.append(RecurringTopic(
                    topic=topic.title(),
                    occurrence_count=stats["count"],
                    first_seen=dates[0] if dates else "unknown",
                    last_seen=dates[-1] if dates else "unknown",
                    resolution_rate=resolution_rate,
                    average_intensity=avg_intensity,
                    underlying_need_partner_a=common_need_a,
                    underlying_need_partner_b=common_need_b
                ))

        # Sort by occurrence count
        topics.sort(key=lambda x: x.occurrence_count, reverse=True)
        return topics[:10]

    def infer_repair_outcomes(
        self,
        debriefs: List[FightDebrief]
    ) -> List[RepairOutcomeInference]:
        """
        Infer if past repair plans worked WITHOUT user feedback.

        Logic:
        - If same topic doesn't recur within 10 days = likely worked
        - If same topic recurs within 3 days = likely failed
        - Check resolution status of subsequent fights
        """
        outcomes = []

        # Sort debriefs by date
        sorted_debriefs = sorted(
            debriefs,
            key=lambda x: x.analyzed_at if isinstance(x.analyzed_at, datetime)
            else datetime.fromisoformat(str(x.analyzed_at).replace('Z', '+00:00'))
        )

        for i, debrief in enumerate(sorted_debriefs[:-1]):  # Skip last one
            # Get date of this fight
            fight_date = debrief.analyzed_at
            if isinstance(fight_date, str):
                fight_date = datetime.fromisoformat(fight_date.replace('Z', '+00:00'))

            topic = debrief.topic.lower()

            # Look for similar fights in the future
            days_until_similar = None
            for future_debrief in sorted_debriefs[i + 1:]:
                future_date = future_debrief.analyzed_at
                if isinstance(future_date, str):
                    future_date = datetime.fromisoformat(future_date.replace('Z', '+00:00'))

                # Check if similar topic
                if topic in future_debrief.topic.lower() or future_debrief.topic.lower() in topic:
                    days_diff = (future_date.replace(tzinfo=None) - fight_date.replace(tzinfo=None)).days
                    days_until_similar = days_diff
                    break

            # Infer outcome
            if days_until_similar is None:
                # No similar fight found - likely worked
                inference = RepairOutcomeInference(
                    conflict_id=debrief.conflict_id,
                    repair_plan_generated_at=str(fight_date),
                    inference_method="no_recurrence",
                    inferred_success=True,
                    confidence="medium",
                    evidence=f"No similar fight about '{debrief.topic}' in the following {len(sorted_debriefs) - i - 1} conflicts",
                    days_until_next_similar_fight=None
                )
            elif days_until_similar <= 3:
                # Same topic within 3 days - likely failed
                inference = RepairOutcomeInference(
                    conflict_id=debrief.conflict_id,
                    repair_plan_generated_at=str(fight_date),
                    inference_method="same_topic_recurred",
                    inferred_success=False,
                    confidence="high",
                    evidence=f"Same topic recurred within {days_until_similar} days",
                    days_until_next_similar_fight=days_until_similar
                )
            elif days_until_similar <= 10:
                # Same topic within 10 days - uncertain
                inference = RepairOutcomeInference(
                    conflict_id=debrief.conflict_id,
                    repair_plan_generated_at=str(fight_date),
                    inference_method="same_topic_recurred",
                    inferred_success=False,
                    confidence="low",
                    evidence=f"Similar topic recurred after {days_until_similar} days",
                    days_until_next_similar_fight=days_until_similar
                )
            else:
                # Same topic after 10+ days - likely worked for a while
                inference = RepairOutcomeInference(
                    conflict_id=debrief.conflict_id,
                    repair_plan_generated_at=str(fight_date),
                    inference_method="topic_resolved",
                    inferred_success=True,
                    confidence="medium",
                    evidence=f"Topic didn't recur for {days_until_similar} days",
                    days_until_next_similar_fight=days_until_similar
                )

            outcomes.append(inference)

        return outcomes

    async def generate_cross_fight_intelligence(
        self,
        relationship_id: str,
        days_back: int = 90
    ) -> CrossFightIntelligence:
        """
        Generate comprehensive cross-fight intelligence for a relationship.

        Args:
            relationship_id: The relationship UUID
            days_back: How many days of history to analyze

        Returns:
            CrossFightIntelligence object with all aggregated patterns
        """
        logger.info(f"🧠 Generating Cross-Fight Intelligence for relationship {relationship_id}")

        # Fetch all debriefs
        debriefs = await self.get_all_debriefs(relationship_id, days_back)

        if len(debriefs) < 3:
            logger.warning(f"Only {len(debriefs)} debriefs found - need at least 3 for pattern detection")
            return CrossFightIntelligence(
                relationship_id=relationship_id,
                total_fights_analyzed=len(debriefs),
                analysis_period_days=days_back,
                key_insight="Not enough fight history for pattern detection. Need at least 3 recorded conflicts."
            )

        # Aggregate all patterns
        escalation_triggers = self.aggregate_escalation_triggers(debriefs)
        deescalation_techniques = self.aggregate_deescalation_techniques(debriefs)
        recurring_topics = self.aggregate_recurring_topics(debriefs)
        repair_outcomes = self.infer_repair_outcomes(debriefs)

        # Calculate repair success rate
        successful_repairs = sum(1 for o in repair_outcomes if o.inferred_success)
        repair_success_rate = successful_repairs / len(repair_outcomes) if repair_outcomes else 0.0

        # Calculate who initiates repairs more
        initiation_counts = {"partner_a": 0, "partner_b": 0, "both": 0, "neither": 0}
        for debrief in debriefs:
            initiator = debrief.who_initiated_repairs
            if initiator in initiation_counts:
                initiation_counts[initiator] += 1

        max_initiator = max(initiation_counts, key=initiation_counts.get)
        who_initiates_more = max_initiator if initiation_counts[max_initiator] > len(debriefs) * 0.4 else "both"

        # Calculate average days between fights
        fight_dates = []
        for d in debriefs:
            date = d.analyzed_at
            if isinstance(date, str):
                date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            fight_dates.append(date)

        fight_dates.sort()
        if len(fight_dates) >= 2:
            total_days = (fight_dates[-1] - fight_dates[0]).days
            avg_days_between = total_days / (len(fight_dates) - 1) if len(fight_dates) > 1 else None
        else:
            avg_days_between = None

        # Generate key insight
        key_insight = self._generate_key_insight(
            escalation_triggers,
            deescalation_techniques,
            recurring_topics,
            repair_success_rate
        )

        # Generate prevention recommendations
        prevention_recs = self._generate_prevention_recommendations(
            escalation_triggers,
            recurring_topics
        )

        intelligence = CrossFightIntelligence(
            relationship_id=relationship_id,
            total_fights_analyzed=len(debriefs),
            analysis_period_days=days_back,
            escalation_triggers=escalation_triggers,
            top_escalation_trigger=escalation_triggers[0].trigger_phrase if escalation_triggers else None,
            deescalation_techniques=deescalation_techniques,
            most_effective_technique=deescalation_techniques[0].technique if deescalation_techniques else None,
            recurring_topics=recurring_topics,
            chronic_unresolved_issue=next(
                (t.topic for t in recurring_topics if t.resolution_rate < 0.3),
                None
            ),
            repair_outcomes=repair_outcomes,
            overall_repair_success_rate=repair_success_rate,
            who_initiates_repairs_more=who_initiates_more,
            repair_initiation_counts=initiation_counts,
            average_days_between_fights=avg_days_between,
            key_insight=key_insight,
            prevention_recommendations=prevention_recs
        )

        logger.info(f"✅ Generated Cross-Fight Intelligence: {len(debriefs)} fights, "
                   f"{len(escalation_triggers)} triggers, {len(deescalation_techniques)} techniques")

        return intelligence

    def _generate_key_insight(
        self,
        triggers: List[EscalationTriggerPattern],
        techniques: List[DeescalationTechnique],
        topics: List[RecurringTopic],
        repair_rate: float
    ) -> str:
        """Generate the most important insight from the analysis"""
        insights = []

        if triggers and triggers[0].escalation_rate > 0.5:
            insights.append(
                f"The phrase '{triggers[0].trigger_phrase}' escalates {int(triggers[0].escalation_rate * 100)}% of your fights."
            )

        if techniques and techniques[0].success_rate > 0.7:
            insights.append(
                f"'{techniques[0].technique}' has a {int(techniques[0].success_rate * 100)}% success rate at calming things down."
            )

        if topics:
            chronic = [t for t in topics if t.resolution_rate < 0.3 and t.occurrence_count >= 3]
            if chronic:
                insights.append(
                    f"'{chronic[0].topic}' keeps coming back unresolved - this might need a deeper conversation."
                )

        if repair_rate < 0.3:
            insights.append(
                "Current repair strategies aren't working well. Consider trying different approaches."
            )
        elif repair_rate > 0.7:
            insights.append(
                "Your repair strategies are working! Keep using what's been effective."
            )

        return " ".join(insights) if insights else "Keep recording conflicts to build up pattern data."

    def _generate_prevention_recommendations(
        self,
        triggers: List[EscalationTriggerPattern],
        topics: List[RecurringTopic]
    ) -> List[str]:
        """Generate specific recommendations to prevent future fights"""
        recs = []

        # Avoid top triggers
        for trigger in triggers[:3]:
            if trigger.escalation_rate > 0.3:
                recs.append(f"Avoid saying '{trigger.trigger_phrase}' - it escalates {int(trigger.escalation_rate * 100)}% of fights")

        # Address chronic topics proactively
        for topic in topics[:2]:
            if topic.resolution_rate < 0.5:
                recs.append(f"Have a calm conversation about '{topic.topic}' before it becomes a fight again")

        return recs[:5]  # Return top 5

    async def find_similar_past_fights(
        self,
        relationship_id: str,
        current_topic: str,
        current_summary: str,
        top_k: int = 3
    ) -> List[SimilarFightResult]:
        """
        Find past fights similar to the current one using semantic search.

        Args:
            relationship_id: The relationship UUID
            current_topic: Topic of current fight
            current_summary: Summary of current fight
            top_k: Number of similar fights to return

        Returns:
            List of SimilarFightResult objects
        """
        try:
            # Create query from topic and summary
            query_text = f"{current_topic} {current_summary}"
            query_embedding = self.embeddings.embed_query(query_text)

            # Search debriefs namespace
            results = self.pinecone.index.query(
                vector=query_embedding,
                top_k=top_k + 1,  # Get extra in case current fight is in results
                namespace="debriefs",
                include_metadata=True,
                filter={"relationship_id": {"$eq": relationship_id}}
            )

            similar_fights = []

            if results and results.matches:
                for match in results.matches:
                    metadata = match.metadata
                    conflict_id = metadata.get("conflict_id", "")

                    # Try to get full debrief from S3 for more details
                    what_worked = None
                    what_failed = None
                    key_lesson = ""

                    try:
                        debrief_path = f"debriefs/{relationship_id}/{conflict_id}_debrief.json"
                        content = self.s3.download_file(debrief_path)
                        if content:
                            debrief_data = json.loads(content)
                            if debrief_data.get("phrases_that_helped"):
                                what_worked = debrief_data["phrases_that_helped"][0]
                            if debrief_data.get("phrases_to_avoid"):
                                what_failed = debrief_data["phrases_to_avoid"][0]
                            if debrief_data.get("what_would_have_helped"):
                                key_lesson = debrief_data["what_would_have_helped"]
                    except Exception:
                        pass

                    similar_fights.append(SimilarFightResult(
                        conflict_id=conflict_id,
                        topic=metadata.get("topic", "Unknown"),
                        date=metadata.get("analyzed_at", "Unknown"),
                        similarity_score=match.score,
                        resolution_status=metadata.get("resolution_status", "unknown"),
                        what_worked=what_worked,
                        what_failed=what_failed,
                        key_lesson=key_lesson
                    ))

            # Sort by similarity and remove current fight if present
            similar_fights.sort(key=lambda x: x.similarity_score, reverse=True)
            return similar_fights[:top_k]

        except Exception as e:
            logger.error(f"❌ Error finding similar fights: {e}")
            return []

    def format_intelligence_for_repair_plan(
        self,
        intelligence: CrossFightIntelligence,
        similar_fights: List[SimilarFightResult]
    ) -> str:
        """
        Format cross-fight intelligence for injection into repair plan prompt.

        Returns:
            Formatted string with key patterns and lessons
        """
        sections = []

        sections.append("=== INTELLIGENCE FROM PAST FIGHTS ===")
        sections.append(f"Based on analysis of {intelligence.total_fights_analyzed} past conflicts:")
        sections.append("")

        # Top triggers to avoid
        if intelligence.escalation_triggers:
            sections.append("TRIGGERS TO AVOID (these consistently make fights worse):")
            for trigger in intelligence.escalation_triggers[:3]:
                sections.append(f"  - '{trigger.trigger_phrase}' (escalated {int(trigger.escalation_rate * 100)}% of fights)")
            sections.append("")

        # Effective techniques
        if intelligence.deescalation_techniques:
            sections.append("TECHNIQUES THAT WORK (use these):")
            for tech in intelligence.deescalation_techniques[:3]:
                sections.append(f"  - '{tech.technique}' ({int(tech.success_rate * 100)}% success rate)")
            sections.append("")

        # Similar past fights
        if similar_fights:
            sections.append("SIMILAR PAST FIGHTS (learn from these):")
            for fight in similar_fights[:2]:
                sections.append(f"  - {fight.topic} ({fight.date}): {fight.resolution_status}")
                if fight.what_worked:
                    sections.append(f"    What worked: {fight.what_worked}")
                if fight.key_lesson:
                    sections.append(f"    Lesson: {fight.key_lesson}")
            sections.append("")

        # Key insight
        if intelligence.key_insight:
            sections.append(f"KEY INSIGHT: {intelligence.key_insight}")

        return "\n".join(sections)


# Singleton instance
cross_fight_intelligence_service = CrossFightIntelligenceService()
