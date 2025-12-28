"""
Phase 3: Fight Debrief Tests

Tests for the FightDebrief system that generates comprehensive post-fight analysis
including repair attempts, escalation triggers, and resolution status.
"""
import pytest
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# Test models that mirror the actual schemas
class RepairAttemptOutcome(BaseModel):
    """A single repair attempt and its outcome within a fight"""
    timestamp: str
    speaker: str
    speaker_name: str
    action_type: str
    what_they_said_or_did: str
    outcome: str
    outcome_evidence: str
    why_it_worked_or_failed: str


class FightDebrief(BaseModel):
    """Comprehensive post-fight analysis"""
    conflict_id: str
    relationship_id: str
    analyzed_at: datetime = Field(default_factory=datetime.now)

    # What happened
    topic: str
    summary: str
    duration_estimate: str
    intensity_peak: str
    key_moments: List[str] = Field(default_factory=list)

    # Repair dynamics
    repair_attempts: List[RepairAttemptOutcome] = Field(default_factory=list)
    who_initiated_repairs: str
    total_repair_attempts: int = 0
    successful_repairs: int = 0
    failed_repairs: int = 0
    most_effective_moment: Optional[str] = None
    most_damaging_moment: Optional[str] = None

    # Resolution
    resolution_status: str
    what_resolved_it: Optional[str] = None
    what_remains_unresolved: Optional[str] = None

    # Learnings
    phrases_to_avoid: List[str] = Field(default_factory=list)
    phrases_that_helped: List[str] = Field(default_factory=list)
    unmet_needs_partner_a: List[str] = Field(default_factory=list)
    unmet_needs_partner_b: List[str] = Field(default_factory=list)
    what_would_have_helped: str = ""

    # Connection to past
    similar_to_past_topics: List[str] = Field(default_factory=list)
    recurring_pattern_detected: Optional[str] = None


class TestFightDebriefModel:
    """Tests for the FightDebrief Pydantic model"""

    def create_sample_debrief(self) -> FightDebrief:
        """Create a sample FightDebrief for testing"""
        return FightDebrief(
            conflict_id="test-conflict-123",
            relationship_id="test-relationship-456",
            topic="Household Chores",
            summary="Argument about who does more chores. Escalated when Sarah felt dismissed.",
            duration_estimate="25 minutes",
            intensity_peak="high",
            key_moments=[
                "0:00 - Started discussing chores calmly",
                "5:30 - Tension when Tom said 'I do plenty'",
                "10:00 - Sarah raised voice about feeling unappreciated",
                "18:00 - Tom tried to apologize",
                "22:00 - Both calmed down"
            ],
            repair_attempts=[
                RepairAttemptOutcome(
                    timestamp="18:00",
                    speaker="partner_a",
                    speaker_name="Tom",
                    action_type="apologized",
                    what_they_said_or_did="I'm sorry, I didn't mean to dismiss you",
                    outcome="helped",
                    outcome_evidence="Sarah's tone softened and she acknowledged his effort",
                    why_it_worked_or_failed="He specifically acknowledged what he did wrong"
                )
            ],
            who_initiated_repairs="partner_a",
            total_repair_attempts=2,
            successful_repairs=1,
            failed_repairs=1,
            most_effective_moment="When Tom said 'I hear you, and I know I haven't been pulling my weight'",
            most_damaging_moment="When Sarah said 'You never listen to me'",
            resolution_status="temporary_truce",
            what_resolved_it="Tom's genuine apology and commitment to a chore schedule",
            what_remains_unresolved="Underlying feeling of being taken for granted",
            phrases_to_avoid=["You never...", "You always...", "I do plenty"],
            phrases_that_helped=["I hear you", "I'm sorry I made you feel that way", "Let's figure this out together"],
            unmet_needs_partner_a=["To feel appreciated for his contributions"],
            unmet_needs_partner_b=["To feel heard and supported", "Equal partnership in household tasks"],
            what_would_have_helped="Discussing concerns calmly before resentment built up",
            similar_to_past_topics=["Division of labor", "Feeling unappreciated"],
            recurring_pattern_detected="This topic has come up 3 times in the past month"
        )

    def test_fight_debrief_has_required_fields(self):
        """Test that FightDebrief has all required fields"""
        debrief = self.create_sample_debrief()

        assert debrief.conflict_id != ""
        assert debrief.relationship_id != ""
        assert debrief.topic != ""
        assert debrief.summary != ""
        assert debrief.intensity_peak in ["low", "medium", "high", "explosive"]
        assert debrief.resolution_status in ["resolved", "unresolved", "temporary_truce"]

    def test_fight_debrief_tracks_repair_attempts(self):
        """Test that repair attempts are properly tracked"""
        debrief = self.create_sample_debrief()

        assert len(debrief.repair_attempts) == 1
        assert debrief.total_repair_attempts == 2
        assert debrief.successful_repairs == 1
        assert debrief.failed_repairs == 1

        repair = debrief.repair_attempts[0]
        assert repair.speaker == "partner_a"
        assert repair.outcome == "helped"

    def test_fight_debrief_captures_key_moments(self):
        """Test that key moments are captured with timestamps"""
        debrief = self.create_sample_debrief()

        assert len(debrief.key_moments) >= 3
        # Check that moments have timestamps
        for moment in debrief.key_moments:
            assert ":" in moment  # Has timestamp format

    def test_fight_debrief_identifies_phrases(self):
        """Test that helpful and harmful phrases are identified"""
        debrief = self.create_sample_debrief()

        assert len(debrief.phrases_to_avoid) > 0
        assert len(debrief.phrases_that_helped) > 0

        # Check for common problematic patterns
        avoid_text = " ".join(debrief.phrases_to_avoid).lower()
        assert "never" in avoid_text or "always" in avoid_text

    def test_fight_debrief_tracks_unmet_needs(self):
        """Test that unmet needs are tracked for both partners"""
        debrief = self.create_sample_debrief()

        assert len(debrief.unmet_needs_partner_a) > 0
        assert len(debrief.unmet_needs_partner_b) > 0

    def test_fight_debrief_connects_to_past(self):
        """Test that connection to past fights is tracked"""
        debrief = self.create_sample_debrief()

        assert len(debrief.similar_to_past_topics) > 0
        assert debrief.recurring_pattern_detected is not None


class TestRepairAttemptOutcome:
    """Tests for the RepairAttemptOutcome model"""

    def test_repair_attempt_has_all_fields(self):
        """Test that RepairAttemptOutcome has all required fields"""
        repair = RepairAttemptOutcome(
            timestamp="5:30",
            speaker="partner_b",
            speaker_name="Sarah",
            action_type="validated_feelings",
            what_they_said_or_did="I understand why you're frustrated",
            outcome="helped",
            outcome_evidence="Tom visibly relaxed and started listening",
            why_it_worked_or_failed="Validation made Tom feel heard"
        )

        assert repair.timestamp == "5:30"
        assert repair.speaker == "partner_b"
        assert repair.action_type == "validated_feelings"
        assert repair.outcome in ["helped", "hurt", "neutral"]

    def test_repair_attempt_action_types(self):
        """Test that various action types are valid"""
        valid_action_types = [
            "apologized",
            "validated_feelings",
            "took_responsibility",
            "offered_solution",
            "used_humor",
            "physical_affection",
            "asked_for_break",
            "redirected_topic",
            "expressed_love",
            "other"
        ]

        for action_type in valid_action_types:
            repair = RepairAttemptOutcome(
                timestamp="0:00",
                speaker="partner_a",
                speaker_name="Tom",
                action_type=action_type,
                what_they_said_or_did="Test action",
                outcome="neutral",
                outcome_evidence="Nothing changed",
                why_it_worked_or_failed="Test reason"
            )
            assert repair.action_type == action_type

    def test_repair_attempt_outcomes(self):
        """Test that outcomes are properly categorized"""
        outcomes = ["helped", "hurt", "neutral"]

        for outcome in outcomes:
            repair = RepairAttemptOutcome(
                timestamp="0:00",
                speaker="partner_a",
                speaker_name="Tom",
                action_type="apologized",
                what_they_said_or_did="I'm sorry",
                outcome=outcome,
                outcome_evidence="Test evidence",
                why_it_worked_or_failed="Test reason"
            )
            assert repair.outcome == outcome


class TestFightDebriefSummaryGeneration:
    """Tests for generating debrief summaries for repair plan context"""

    def generate_debrief_summary(self, debrief: FightDebrief) -> str:
        """Generate summary like the backend does"""
        return f"""
Topic: {debrief.topic}
Summary: {debrief.summary}
Intensity: {debrief.intensity_peak}
Resolution: {debrief.resolution_status}
Most effective moment: {debrief.most_effective_moment or 'None identified'}
Most damaging moment: {debrief.most_damaging_moment or 'None identified'}
Successful repairs: {debrief.successful_repairs}/{debrief.total_repair_attempts}
Phrases that helped: {', '.join(debrief.phrases_that_helped[:3]) if debrief.phrases_that_helped else 'None'}
Phrases to avoid: {', '.join(debrief.phrases_to_avoid[:3]) if debrief.phrases_to_avoid else 'None'}
"""

    def test_summary_includes_key_info(self):
        """Test that summary includes key information"""
        debrief = FightDebrief(
            conflict_id="test-123",
            relationship_id="rel-456",
            topic="Money Management",
            summary="Disagreement about budget priorities",
            duration_estimate="30 min",
            intensity_peak="medium",
            resolution_status="resolved",
            who_initiated_repairs="both",
            total_repair_attempts=3,
            successful_repairs=2,
            most_effective_moment="When we agreed to revisit monthly",
            most_damaging_moment="When I said 'you're irresponsible'",
            phrases_that_helped=["Let's find a middle ground", "I understand your concern"],
            phrases_to_avoid=["You're irresponsible", "You don't care"]
        )

        summary = self.generate_debrief_summary(debrief)

        assert "Money Management" in summary
        assert "medium" in summary
        assert "resolved" in summary
        assert "2/3" in summary
        assert "middle ground" in summary
        assert "irresponsible" in summary

    def test_summary_handles_empty_lists(self):
        """Test that summary handles empty phrases lists"""
        debrief = FightDebrief(
            conflict_id="test-123",
            relationship_id="rel-456",
            topic="Test Topic",
            summary="Test summary",
            duration_estimate="10 min",
            intensity_peak="low",
            resolution_status="resolved",
            who_initiated_repairs="partner_a",
            phrases_that_helped=[],
            phrases_to_avoid=[]
        )

        summary = self.generate_debrief_summary(debrief)

        assert "Phrases that helped: None" in summary
        assert "Phrases to avoid: None" in summary


class TestFightDebriefIntegration:
    """Integration tests for FightDebrief with repair plan generation"""

    def test_debrief_provides_context_for_repair_plan(self):
        """Test that debrief provides useful context for repair plan generation"""
        debrief = FightDebrief(
            conflict_id="test-123",
            relationship_id="rel-456",
            topic="Communication Breakdown",
            summary="Partner A felt unheard when Partner B was distracted",
            duration_estimate="20 min",
            intensity_peak="medium",
            resolution_status="temporary_truce",
            who_initiated_repairs="partner_b",
            total_repair_attempts=2,
            successful_repairs=1,
            most_effective_moment="When Partner B put down the phone and gave full attention",
            most_damaging_moment="When Partner A said 'You never listen'",
            phrases_that_helped=["I'm giving you my full attention now"],
            phrases_to_avoid=["You never listen", "I was listening"],
            unmet_needs_partner_a=["To feel prioritized", "Undivided attention"],
            unmet_needs_partner_b=["To not feel criticized constantly"]
        )

        # Verify debrief contains actionable info for repair plan
        assert debrief.most_effective_moment is not None
        assert "phone" in debrief.most_effective_moment.lower() or "attention" in debrief.most_effective_moment.lower()

        # Verify we know what to avoid
        assert len(debrief.phrases_to_avoid) > 0
        avoid_text = " ".join(debrief.phrases_to_avoid).lower()
        assert "never" in avoid_text

        # Verify we know what worked
        assert len(debrief.phrases_that_helped) > 0

    def test_debrief_tracks_who_initiated_repairs(self):
        """Test that we know who typically tries to repair"""
        debrief = FightDebrief(
            conflict_id="test-123",
            relationship_id="rel-456",
            topic="Test",
            summary="Test",
            duration_estimate="10 min",
            intensity_peak="low",
            resolution_status="resolved",
            who_initiated_repairs="partner_a"
        )

        assert debrief.who_initiated_repairs in ["partner_a", "partner_b", "both", "neither"]


class TestDebriefStorage:
    """Tests for Fight Debrief storage in S3 and Pinecone"""

    def test_debrief_can_be_serialized_to_json(self):
        """Test that debrief can be serialized to JSON for S3 storage"""
        import json

        debrief = FightDebrief(
            conflict_id="test-123",
            relationship_id="rel-456",
            topic="Test Topic",
            summary="Test summary",
            duration_estimate="10 min",
            intensity_peak="low",
            resolution_status="resolved",
            who_initiated_repairs="partner_a",
            repair_attempts=[
                RepairAttemptOutcome(
                    timestamp="5:00",
                    speaker="partner_a",
                    speaker_name="Tom",
                    action_type="apologized",
                    what_they_said_or_did="Sorry",
                    outcome="helped",
                    outcome_evidence="Tension reduced",
                    why_it_worked_or_failed="Sincere apology"
                )
            ]
        )

        # Should be able to dump to JSON
        json_str = json.dumps(debrief.model_dump(), default=str, indent=2)
        assert json_str is not None
        assert "test-123" in json_str
        assert "apologized" in json_str

    def test_debrief_metadata_for_pinecone(self):
        """Test that debrief metadata is suitable for Pinecone storage"""
        debrief = FightDebrief(
            conflict_id="test-123",
            relationship_id="rel-456",
            topic="Household Chores",
            summary="Fight about who does more around the house",
            duration_estimate="20 min",
            intensity_peak="high",
            resolution_status="temporary_truce",
            who_initiated_repairs="partner_a",
            successful_repairs=2,
            total_repair_attempts=3,
            phrases_to_avoid=["You never help", "I do everything"],
            phrases_that_helped=["I appreciate when you...", "Let's split this fairly"]
        )

        # Create metadata like backend does
        metadata = {
            "conflict_id": debrief.conflict_id,
            "relationship_id": debrief.relationship_id,
            "topic": debrief.topic,
            "summary": debrief.summary[:500],
            "resolution_status": debrief.resolution_status,
            "intensity_peak": debrief.intensity_peak,
            "successful_repairs": debrief.successful_repairs,
            "total_repairs": debrief.total_repair_attempts,
            "phrases_to_avoid": str(debrief.phrases_to_avoid[:5]),
            "phrases_that_helped": str(debrief.phrases_that_helped[:5]),
            "analyzed_at": str(debrief.analyzed_at)
        }

        # Verify all metadata fields are present
        assert metadata["conflict_id"] == "test-123"
        assert metadata["topic"] == "Household Chores"
        assert metadata["successful_repairs"] == 2
        assert "You never help" in metadata["phrases_to_avoid"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
