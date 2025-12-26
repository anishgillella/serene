"""
Unit tests for Pattern Analysis Service - Phase 2
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.services.pattern_analysis_service import pattern_analysis_service
from app.models.schemas import EscalationRiskReport, TriggerPhraseAnalysis, UnmetNeedRecurrence
from app.services.db_service import db_service


class TestEscalationRiskCalculation:
    """Test escalation risk calculation"""

    @pytest.mark.asyncio
    async def test_calculate_escalation_risk_no_conflicts(self):
        """Test escalation risk with no conflicts"""
        relationship_id = str(uuid4())

        # Mock get_previous_conflicts to return empty list
        db_service.get_previous_conflicts = lambda rel_id, limit=20: []

        risk_report = await pattern_analysis_service.calculate_escalation_risk(relationship_id)

        assert risk_report.risk_score == 0.0
        assert risk_report.interpretation == "low"
        assert risk_report.unresolved_issues == 0
        assert risk_report.days_until_predicted_conflict == 30

    @pytest.mark.asyncio
    async def test_calculate_escalation_risk_with_unresolved(self):
        """Test escalation risk with unresolved conflicts"""
        relationship_id = str(uuid4())

        conflicts = [
            {
                "id": str(uuid4()),
                "is_resolved": False,
                "resentment_level": 8,
                "started_at": (datetime.now() - timedelta(days=2)).isoformat(),
                "parent_conflict_id": None
            },
            {
                "id": str(uuid4()),
                "is_resolved": False,
                "resentment_level": 7,
                "started_at": (datetime.now() - timedelta(days=5)).isoformat(),
                "parent_conflict_id": None
            }
        ]

        db_service.get_previous_conflicts = lambda rel_id, limit=20: conflicts

        risk_report = await pattern_analysis_service.calculate_escalation_risk(relationship_id)

        assert risk_report.risk_score > 0
        assert risk_report.unresolved_issues == 2
        assert risk_report.interpretation in ["low", "medium", "high", "critical"]

    def test_recurrence_score_daily(self):
        """Test recurrence score for daily conflicts"""
        conflicts = [
            {
                "id": str(uuid4()),
                "started_at": (datetime.now()).isoformat(),
                "is_resolved": False
            },
            {
                "id": str(uuid4()),
                "started_at": (datetime.now() - timedelta(days=1)).isoformat(),
                "is_resolved": False
            },
            {
                "id": str(uuid4()),
                "started_at": (datetime.now() - timedelta(days=2)).isoformat(),
                "is_resolved": False
            }
        ]

        score = pattern_analysis_service._calculate_recurrence_score(conflicts)

        # Daily conflicts should score high
        assert score >= 0.6

    def test_recurrence_score_monthly(self):
        """Test recurrence score for monthly conflicts"""
        conflicts = [
            {
                "id": str(uuid4()),
                "started_at": (datetime.now()).isoformat(),
                "is_resolved": False
            },
            {
                "id": str(uuid4()),
                "started_at": (datetime.now() - timedelta(days=30)).isoformat(),
                "is_resolved": False
            }
        ]

        score = pattern_analysis_service._calculate_recurrence_score(conflicts)

        # Monthly conflicts should score lower
        assert score <= 0.4

    def test_predict_next_conflict(self):
        """Test next conflict prediction"""
        conflicts = [
            {
                "id": str(uuid4()),
                "started_at": (datetime.now()).isoformat(),
            },
            {
                "id": str(uuid4()),
                "started_at": (datetime.now() - timedelta(days=7)).isoformat(),
            }
        ]

        days = pattern_analysis_service._predict_next_conflict(conflicts)

        # Should predict based on interval between last 2 conflicts
        assert days >= 3
        assert days <= 10

    def test_generate_recommendations_critical(self):
        """Test recommendations for critical risk"""
        recent_conflicts = [
            {"id": str(uuid4()), "is_resolved": False, "resentment_level": 9}
        ] * 5

        recs = pattern_analysis_service._generate_recommendations(
            interpretation="critical",
            unresolved_count=5,
            avg_resentment=9,
            recurrence_score=0.9,
            recent_conflicts=recent_conflicts
        )

        assert len(recs) > 0
        assert any("mediation" in rec.lower() or "urgent" in rec.lower() for rec in recs)

    def test_generate_recommendations_low(self):
        """Test recommendations for low risk"""
        recs = pattern_analysis_service._generate_recommendations(
            interpretation="low",
            unresolved_count=0,
            avg_resentment=2,
            recurrence_score=0.1,
            recent_conflicts=[]
        )

        assert len(recs) > 0


class TestTriggerPhraseAnalysis:
    """Test trigger phrase analysis"""

    @pytest.mark.asyncio
    async def test_find_trigger_phrases_empty(self):
        """Test trigger phrase analysis with no data"""
        relationship_id = str(uuid4())

        db_service.get_trigger_phrases_for_relationship = lambda rel_id: []

        result = await pattern_analysis_service.find_trigger_phrase_patterns(relationship_id)

        assert result["most_impactful"] == []
        assert "trends" in result

    @pytest.mark.asyncio
    async def test_find_trigger_phrases_with_data(self):
        """Test trigger phrase analysis with data"""
        relationship_id = str(uuid4())

        phrases = [
            {
                "phrase": "You never listen",
                "phrase_category": "blame",
                "usage_count": 5,
                "avg_emotional_intensity": 8,
                "escalation_rate": 0.8,
                "speaker": "partner_a"
            },
            {
                "phrase": "You always blame me",
                "phrase_category": "blame",
                "usage_count": 3,
                "avg_emotional_intensity": 7,
                "escalation_rate": 0.7,
                "speaker": "partner_b"
            }
        ]

        db_service.get_trigger_phrases_for_relationship = lambda rel_id: phrases

        result = await pattern_analysis_service.find_trigger_phrase_patterns(relationship_id)

        assert len(result["most_impactful"]) == 2
        assert result["most_impactful"][0]["phrase"] == "You never listen"
        assert result["most_impactful"][0]["usage_count"] == 5


class TestConflictChains:
    """Test conflict chain identification"""

    @pytest.mark.asyncio
    async def test_identify_conflict_chains_empty(self):
        """Test chain identification with no conflicts"""
        relationship_id = str(uuid4())

        db_service.get_previous_conflicts = lambda rel_id, limit=50: []

        chains = await pattern_analysis_service.identify_conflict_chains(relationship_id)

        assert chains == []

    @pytest.mark.asyncio
    async def test_identify_conflict_chains_single_chain(self):
        """Test chain identification with linked conflicts"""
        relationship_id = str(uuid4())

        conflict_id_1 = str(uuid4())
        conflict_id_2 = str(uuid4())

        conflicts = [
            {
                "id": conflict_id_2,
                "parent_conflict_id": conflict_id_1,
                "is_resolved": False,
                "metadata": {"topic": "finances"}
            },
            {
                "id": conflict_id_1,
                "parent_conflict_id": None,
                "is_resolved": True,
                "metadata": {"topic": "money"}
            }
        ]

        db_service.get_previous_conflicts = lambda rel_id, limit=50: conflicts

        chains = await pattern_analysis_service.identify_conflict_chains(relationship_id)

        # Should identify the chain
        assert len(chains) >= 1


class TestChronicNeeds:
    """Test chronic unmet needs tracking"""

    @pytest.mark.asyncio
    async def test_track_chronic_needs_empty(self):
        """Test chronic needs with no data"""
        relationship_id = str(uuid4())

        db_service.get_unmet_needs_for_relationship = lambda rel_id: []

        needs = await pattern_analysis_service.track_chronic_needs(relationship_id)

        assert needs == []

    @pytest.mark.asyncio
    async def test_track_chronic_needs_filters_by_count(self):
        """Test that only 3+ conflict needs are included"""
        relationship_id = str(uuid4())

        needs_data = [
            {
                "need": "feeling_heard",
                "conflict_count": 5,
                "first_appeared": "2024-01-01",
                "days_appeared_in": 30,
                "percentage_of_conflicts": 50.0
            },
            {
                "need": "trust",
                "conflict_count": 2,  # Should be filtered out
                "first_appeared": "2024-01-05",
                "days_appeared_in": 20,
                "percentage_of_conflicts": 20.0
            }
        ]

        db_service.get_unmet_needs_for_relationship = lambda rel_id: needs_data

        needs = await pattern_analysis_service.track_chronic_needs(relationship_id)

        # Should only include needs with 3+ conflicts
        assert len(needs) == 1
        assert needs[0].need == "feeling_heard"
        assert needs[0].conflict_count == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
