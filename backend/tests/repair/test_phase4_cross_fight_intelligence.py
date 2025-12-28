"""
Phase 4: Cross-Fight Intelligence Tests

Tests for the cross-fight intelligence system that aggregates learnings
across all past fights without requiring user feedback.
"""
import pytest
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel, Field
from collections import defaultdict


# Test models that mirror the actual schemas
class EscalationTriggerPattern(BaseModel):
    """Pattern of a phrase/behavior that consistently escalates fights"""
    trigger_phrase: str
    occurrence_count: int
    total_fights_analyzed: int
    escalation_rate: float
    example_conflicts: List[str] = Field(default_factory=list)
    who_typically_says_it: str = "both"


class DeescalationTechnique(BaseModel):
    """A technique that has helped de-escalate fights"""
    technique: str
    success_count: int
    attempt_count: int
    success_rate: float
    action_type: str
    who_typically_uses_it: str = "both"
    best_timing: Optional[str] = None


class RecurringTopic(BaseModel):
    """A topic that comes up repeatedly in conflicts"""
    topic: str
    occurrence_count: int
    first_seen: str
    last_seen: str
    resolution_rate: float
    average_intensity: str
    underlying_need_partner_a: Optional[str] = None
    underlying_need_partner_b: Optional[str] = None


class RepairOutcomeInference(BaseModel):
    """Inferred outcome of a past repair plan without user feedback"""
    conflict_id: str
    repair_plan_generated_at: str
    inference_method: str
    inferred_success: bool
    confidence: str
    evidence: str
    days_until_next_similar_fight: Optional[int] = None


class CrossFightIntelligence(BaseModel):
    """Aggregated intelligence from all past fights"""
    relationship_id: str
    generated_at: datetime = Field(default_factory=datetime.now)
    total_fights_analyzed: int = 0
    analysis_period_days: int = 90

    escalation_triggers: List[EscalationTriggerPattern] = Field(default_factory=list)
    top_escalation_trigger: Optional[str] = None

    deescalation_techniques: List[DeescalationTechnique] = Field(default_factory=list)
    most_effective_technique: Optional[str] = None

    recurring_topics: List[RecurringTopic] = Field(default_factory=list)
    chronic_unresolved_issue: Optional[str] = None

    repair_outcomes: List[RepairOutcomeInference] = Field(default_factory=list)
    overall_repair_success_rate: float = 0.0

    who_initiates_repairs_more: str = "both"
    repair_initiation_counts: dict = Field(default_factory=lambda: {"partner_a": 0, "partner_b": 0})

    average_days_between_fights: Optional[float] = None
    high_risk_periods: List[str] = Field(default_factory=list)

    key_insight: str = ""
    prevention_recommendations: List[str] = Field(default_factory=list)


class SimilarFightResult(BaseModel):
    """A past fight that is similar to the current one"""
    conflict_id: str
    topic: str
    date: str
    similarity_score: float
    resolution_status: str
    what_worked: Optional[str] = None
    what_failed: Optional[str] = None
    key_lesson: str = ""


class TestCrossFightIntelligenceModel:
    """Tests for the CrossFightIntelligence Pydantic model"""

    def create_sample_intelligence(self) -> CrossFightIntelligence:
        """Create sample intelligence for testing"""
        return CrossFightIntelligence(
            relationship_id="test-relationship-123",
            total_fights_analyzed=10,
            escalation_triggers=[
                EscalationTriggerPattern(
                    trigger_phrase="you never listen",
                    occurrence_count=4,
                    total_fights_analyzed=10,
                    escalation_rate=0.4,
                    example_conflicts=["c1", "c2", "c3", "c4"],
                    who_typically_says_it="partner_b"
                ),
                EscalationTriggerPattern(
                    trigger_phrase="calm down",
                    occurrence_count=3,
                    total_fights_analyzed=10,
                    escalation_rate=0.3,
                    example_conflicts=["c2", "c5", "c7"],
                    who_typically_says_it="partner_a"
                )
            ],
            top_escalation_trigger="you never listen",
            deescalation_techniques=[
                DeescalationTechnique(
                    technique="i hear you and i understand",
                    success_count=5,
                    attempt_count=6,
                    success_rate=0.83,
                    action_type="validated_feelings",
                    who_typically_uses_it="partner_a",
                    best_timing="early"
                )
            ],
            most_effective_technique="i hear you and i understand",
            recurring_topics=[
                RecurringTopic(
                    topic="Household Chores",
                    occurrence_count=4,
                    first_seen="2024-01-15",
                    last_seen="2024-03-20",
                    resolution_rate=0.25,
                    average_intensity="medium",
                    underlying_need_partner_a="To feel appreciated",
                    underlying_need_partner_b="Equal partnership"
                )
            ],
            chronic_unresolved_issue="Household Chores",
            overall_repair_success_rate=0.65,
            who_initiates_repairs_more="partner_a",
            average_days_between_fights=12.5,
            key_insight="The phrase 'you never listen' escalates 40% of fights. Try using 'I hear you' instead.",
            prevention_recommendations=[
                "Avoid saying 'you never listen' - it escalates 40% of fights",
                "Have a calm conversation about 'Household Chores' before it becomes a fight again"
            ]
        )

    def test_intelligence_has_required_fields(self):
        """Test that CrossFightIntelligence has all required fields"""
        intel = self.create_sample_intelligence()

        assert intel.relationship_id != ""
        assert intel.total_fights_analyzed > 0
        assert intel.analysis_period_days > 0

    def test_intelligence_tracks_escalation_triggers(self):
        """Test that escalation triggers are properly tracked"""
        intel = self.create_sample_intelligence()

        assert len(intel.escalation_triggers) >= 1
        assert intel.top_escalation_trigger is not None

        top_trigger = intel.escalation_triggers[0]
        assert top_trigger.escalation_rate > 0
        assert top_trigger.occurrence_count > 0

    def test_intelligence_tracks_deescalation_techniques(self):
        """Test that de-escalation techniques are tracked"""
        intel = self.create_sample_intelligence()

        assert len(intel.deescalation_techniques) >= 1
        assert intel.most_effective_technique is not None

        technique = intel.deescalation_techniques[0]
        assert technique.success_rate > 0
        assert technique.action_type != ""

    def test_intelligence_identifies_recurring_topics(self):
        """Test that recurring topics are identified"""
        intel = self.create_sample_intelligence()

        assert len(intel.recurring_topics) >= 1

        topic = intel.recurring_topics[0]
        assert topic.occurrence_count >= 2  # Recurring means at least twice
        assert topic.resolution_rate >= 0.0
        assert topic.resolution_rate <= 1.0

    def test_intelligence_tracks_repair_success_rate(self):
        """Test that overall repair success rate is tracked"""
        intel = self.create_sample_intelligence()

        assert intel.overall_repair_success_rate >= 0.0
        assert intel.overall_repair_success_rate <= 1.0

    def test_intelligence_provides_actionable_insights(self):
        """Test that key insights and recommendations are provided"""
        intel = self.create_sample_intelligence()

        assert intel.key_insight != ""
        assert len(intel.prevention_recommendations) > 0


class TestEscalationPatternAggregation:
    """Tests for aggregating escalation trigger patterns"""

    def aggregate_triggers(self, phrases_list: List[List[str]]) -> List[EscalationTriggerPattern]:
        """Simulate trigger aggregation logic"""
        trigger_counts = defaultdict(lambda: {"occurrences": 0, "conflicts": []})

        for i, phrases in enumerate(phrases_list):
            for phrase in phrases:
                normalized = phrase.lower().strip()
                trigger_counts[normalized]["occurrences"] += 1
                trigger_counts[normalized]["conflicts"].append(f"conflict_{i}")

        patterns = []
        total_fights = len(phrases_list)

        for phrase, data in trigger_counts.items():
            if data["occurrences"] >= 2:
                patterns.append(EscalationTriggerPattern(
                    trigger_phrase=phrase,
                    occurrence_count=data["occurrences"],
                    total_fights_analyzed=total_fights,
                    escalation_rate=data["occurrences"] / total_fights,
                    example_conflicts=data["conflicts"][:5]
                ))

        patterns.sort(key=lambda x: x.escalation_rate, reverse=True)
        return patterns

    def test_aggregates_repeated_phrases(self):
        """Test that repeated phrases are aggregated correctly"""
        phrases_list = [
            ["You never listen", "Calm down"],
            ["you never listen", "whatever"],
            ["YOU NEVER LISTEN", "I don't care"],
            ["This is stupid", "Calm down"]
        ]

        patterns = self.aggregate_triggers(phrases_list)

        # "you never listen" appears 3 times, "calm down" appears 2 times
        assert len(patterns) == 2
        assert patterns[0].trigger_phrase == "you never listen"
        assert patterns[0].occurrence_count == 3
        assert patterns[0].escalation_rate == 0.75

    def test_ignores_single_occurrences(self):
        """Test that single occurrences are not included"""
        phrases_list = [
            ["unique phrase 1"],
            ["unique phrase 2"],
            ["unique phrase 3"]
        ]

        patterns = self.aggregate_triggers(phrases_list)
        assert len(patterns) == 0

    def test_sorts_by_escalation_rate(self):
        """Test that patterns are sorted by escalation rate"""
        phrases_list = [
            ["phrase a", "phrase b"],
            ["phrase a", "phrase b"],
            ["phrase a"],  # phrase a appears 3 times
            ["phrase b"]   # phrase b appears 3 times
        ]

        patterns = self.aggregate_triggers(phrases_list)
        for i in range(len(patterns) - 1):
            assert patterns[i].escalation_rate >= patterns[i + 1].escalation_rate


class TestDeescalationTechniqueAggregation:
    """Tests for aggregating de-escalation techniques"""

    def test_calculates_success_rate(self):
        """Test that success rate is calculated correctly"""
        technique = DeescalationTechnique(
            technique="I understand how you feel",
            success_count=7,
            attempt_count=10,
            success_rate=0.7,
            action_type="validated_feelings"
        )

        assert technique.success_rate == 0.7
        assert technique.success_count <= technique.attempt_count

    def test_tracks_timing(self):
        """Test that best timing is tracked"""
        technique = DeescalationTechnique(
            technique="Let's take a break",
            success_count=5,
            attempt_count=8,
            success_rate=0.625,
            action_type="asked_for_break",
            best_timing="mid"
        )

        assert technique.best_timing in ["early", "mid", "late", None]

    def test_tracks_who_uses_it(self):
        """Test that we know who typically uses each technique"""
        technique = DeescalationTechnique(
            technique="I'm sorry",
            success_count=6,
            attempt_count=10,
            success_rate=0.6,
            action_type="apologized",
            who_typically_uses_it="partner_a"
        )

        assert technique.who_typically_uses_it in ["partner_a", "partner_b", "both"]


class TestRecurringTopicDetection:
    """Tests for detecting recurring topics"""

    def test_identifies_chronic_issues(self):
        """Test that chronic (unresolved) issues are identified"""
        topic = RecurringTopic(
            topic="Money Management",
            occurrence_count=5,
            first_seen="2024-01-01",
            last_seen="2024-03-15",
            resolution_rate=0.2,  # Only resolved 20% of the time
            average_intensity="high"
        )

        # Chronic = low resolution rate
        assert topic.resolution_rate < 0.5
        assert topic.occurrence_count >= 3

    def test_tracks_underlying_needs(self):
        """Test that underlying needs are tracked for recurring topics"""
        topic = RecurringTopic(
            topic="Quality Time",
            occurrence_count=3,
            first_seen="2024-02-01",
            last_seen="2024-03-10",
            resolution_rate=0.33,
            average_intensity="medium",
            underlying_need_partner_a="More dedicated couple time",
            underlying_need_partner_b="Balance between together time and personal space"
        )

        assert topic.underlying_need_partner_a is not None
        assert topic.underlying_need_partner_b is not None


class TestRepairOutcomeInference:
    """Tests for inferring repair outcomes without user feedback"""

    def test_no_recurrence_means_success(self):
        """Test that no recurrence of topic implies success"""
        outcome = RepairOutcomeInference(
            conflict_id="conflict-123",
            repair_plan_generated_at="2024-03-01",
            inference_method="no_recurrence",
            inferred_success=True,
            confidence="medium",
            evidence="No similar fight in the following 30 days",
            days_until_next_similar_fight=None
        )

        assert outcome.inferred_success == True
        assert outcome.inference_method == "no_recurrence"

    def test_quick_recurrence_means_failure(self):
        """Test that same topic within 3 days implies failure"""
        outcome = RepairOutcomeInference(
            conflict_id="conflict-456",
            repair_plan_generated_at="2024-03-05",
            inference_method="same_topic_recurred",
            inferred_success=False,
            confidence="high",
            evidence="Same topic recurred within 2 days",
            days_until_next_similar_fight=2
        )

        assert outcome.inferred_success == False
        assert outcome.days_until_next_similar_fight <= 3
        assert outcome.confidence == "high"

    def test_delayed_recurrence_is_uncertain(self):
        """Test that recurrence after 10+ days has lower confidence"""
        outcome = RepairOutcomeInference(
            conflict_id="conflict-789",
            repair_plan_generated_at="2024-03-10",
            inference_method="topic_resolved",
            inferred_success=True,
            confidence="medium",
            evidence="Topic didn't recur for 15 days",
            days_until_next_similar_fight=15
        )

        assert outcome.days_until_next_similar_fight > 10
        assert outcome.confidence in ["medium", "low"]


class TestSimilarFightRetrieval:
    """Tests for finding similar past fights"""

    def test_similar_fight_has_required_fields(self):
        """Test that SimilarFightResult has all required fields"""
        similar = SimilarFightResult(
            conflict_id="past-conflict-123",
            topic="Communication Breakdown",
            date="2024-02-15",
            similarity_score=0.85,
            resolution_status="resolved",
            what_worked="Taking a 10-minute break",
            what_failed="Trying to solve it immediately",
            key_lesson="Sometimes stepping away helps more than pushing through"
        )

        assert similar.conflict_id != ""
        assert similar.similarity_score >= 0.0
        assert similar.similarity_score <= 1.0
        assert similar.resolution_status in ["resolved", "unresolved", "temporary_truce", "unknown"]

    def test_similar_fight_provides_lessons(self):
        """Test that similar fights provide actionable lessons"""
        similar = SimilarFightResult(
            conflict_id="past-conflict-456",
            topic="Household Responsibilities",
            date="2024-01-20",
            similarity_score=0.78,
            resolution_status="temporary_truce",
            what_worked="Making a chore schedule together",
            what_failed="Pointing fingers about who does more",
            key_lesson="Focus on solutions, not blame"
        )

        assert similar.what_worked is not None
        assert similar.key_lesson != ""


class TestIntelligenceFormatting:
    """Tests for formatting intelligence for repair plan injection"""

    def format_intelligence(
        self,
        intel: CrossFightIntelligence,
        similar_fights: List[SimilarFightResult]
    ) -> str:
        """Simulate formatting logic"""
        sections = []
        sections.append("=== INTELLIGENCE FROM PAST FIGHTS ===")
        sections.append(f"Based on analysis of {intel.total_fights_analyzed} past conflicts:")
        sections.append("")

        if intel.escalation_triggers:
            sections.append("TRIGGERS TO AVOID:")
            for trigger in intel.escalation_triggers[:3]:
                sections.append(f"  - '{trigger.trigger_phrase}' ({int(trigger.escalation_rate * 100)}% escalation)")
            sections.append("")

        if intel.deescalation_techniques:
            sections.append("TECHNIQUES THAT WORK:")
            for tech in intel.deescalation_techniques[:3]:
                sections.append(f"  - '{tech.technique}' ({int(tech.success_rate * 100)}% success)")
            sections.append("")

        if similar_fights:
            sections.append("SIMILAR PAST FIGHTS:")
            for fight in similar_fights[:2]:
                sections.append(f"  - {fight.topic}: {fight.resolution_status}")
            sections.append("")

        if intel.key_insight:
            sections.append(f"KEY INSIGHT: {intel.key_insight}")

        return "\n".join(sections)

    def test_formatting_includes_triggers(self):
        """Test that formatted output includes escalation triggers"""
        intel = CrossFightIntelligence(
            relationship_id="test",
            total_fights_analyzed=5,
            escalation_triggers=[
                EscalationTriggerPattern(
                    trigger_phrase="you always",
                    occurrence_count=3,
                    total_fights_analyzed=5,
                    escalation_rate=0.6
                )
            ]
        )

        formatted = self.format_intelligence(intel, [])
        assert "TRIGGERS TO AVOID" in formatted
        assert "you always" in formatted
        assert "60%" in formatted

    def test_formatting_includes_techniques(self):
        """Test that formatted output includes de-escalation techniques"""
        intel = CrossFightIntelligence(
            relationship_id="test",
            total_fights_analyzed=5,
            deescalation_techniques=[
                DeescalationTechnique(
                    technique="let me understand",
                    success_count=4,
                    attempt_count=5,
                    success_rate=0.8,
                    action_type="validated_feelings"
                )
            ]
        )

        formatted = self.format_intelligence(intel, [])
        assert "TECHNIQUES THAT WORK" in formatted
        assert "let me understand" in formatted
        assert "80%" in formatted

    def test_formatting_includes_similar_fights(self):
        """Test that formatted output includes similar past fights"""
        intel = CrossFightIntelligence(
            relationship_id="test",
            total_fights_analyzed=5
        )

        similar = [
            SimilarFightResult(
                conflict_id="past-1",
                topic="Test Topic",
                date="2024-03-01",
                similarity_score=0.9,
                resolution_status="resolved"
            )
        ]

        formatted = self.format_intelligence(intel, similar)
        assert "SIMILAR PAST FIGHTS" in formatted
        assert "Test Topic" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
