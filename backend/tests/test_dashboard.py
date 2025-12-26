"""
Unit tests for Dashboard Aggregation - Phase 4
Tests dashboard data aggregation and endpoint
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.main import app
from app.models.schemas import EscalationRiskReport, UnmetNeedRecurrence


client = TestClient(app)


class TestDashboardEndpoint:
    """Test /api/analytics/dashboard endpoint"""

    @patch('app.routes.analytics.pattern_analysis_service')
    @patch('app.routes.analytics.db_service')
    def test_dashboard_success(self, mock_db, mock_service):
        """Test successful dashboard data retrieval"""
        relationship_id = str(uuid4())

        # Mock risk report
        mock_risk = EscalationRiskReport(
            risk_score=0.4,
            interpretation="medium",
            unresolved_issues=2,
            days_until_predicted_conflict=10,
            factors={
                "unresolved_issues": 0.4,
                "resentment_accumulation": 0.4,
                "time_since_conflict": 0.6,
                "recurrence_pattern": 0.4,
                "avg_resentment": 5.0,
                "days_since_last": 5,
            },
            recommendations=["Take a break", "Address unresolved issues"]
        )
        mock_service.calculate_escalation_risk = AsyncMock(return_value=mock_risk)

        # Mock phrases
        mock_service.find_trigger_phrase_patterns = AsyncMock(return_value={
            "most_impactful": [
                {
                    "phrase": "You never listen",
                    "phrase_category": "blame",
                    "usage_count": 5,
                    "avg_emotional_intensity": 8.0,
                    "escalation_rate": 0.8,
                    "speaker": "partner_a",
                    "is_pattern_trigger": True
                }
            ]
        })

        # Mock chains
        mock_service.identify_conflict_chains = AsyncMock(return_value=[
            {
                "root_cause": "finances",
                "conflicts_in_chain": 3,
                "timeline": "finances → trust → communication",
            }
        ])

        # Mock chronic needs
        mock_service.track_chronic_needs = AsyncMock(return_value=[
            UnmetNeedRecurrence(
                need="feeling_heard",
                conflict_count=5,
                first_appeared="2024-01-01",
                days_appeared_in=30,
                is_chronic=True,
                percentage_of_conflicts=50.0
            )
        ])

        # Mock conflicts
        mock_db.get_previous_conflicts = MagicMock(return_value=[
            {
                "id": str(uuid4()),
                "is_resolved": True,
                "metadata": {"topic": "finances"}
            },
            {
                "id": str(uuid4()),
                "is_resolved": True,
                "metadata": {"topic": "trust"}
            },
            {
                "id": str(uuid4()),
                "is_resolved": False,
                "metadata": {"topic": "communication"}
            }
        ])

        response = client.get(f"/api/analytics/dashboard?relationship_id={relationship_id}")

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "health_score" in data
        assert "escalation_risk" in data
        assert "trigger_phrases" in data
        assert "conflict_chains" in data
        assert "chronic_needs" in data
        assert "metrics" in data
        assert "insights" in data

        # Verify metrics
        assert data["metrics"]["total_conflicts"] == 3
        assert data["metrics"]["resolved_conflicts"] == 2
        assert data["metrics"]["unresolved_conflicts"] == 1
        assert data["metrics"]["resolution_rate"] > 0

    @patch('app.routes.analytics.pattern_analysis_service')
    @patch('app.routes.analytics.db_service')
    def test_dashboard_health_score_calculation(self, mock_db, mock_service):
        """Test health score calculation (1.0 - risk_score) * 100"""
        relationship_id = str(uuid4())

        mock_risk = EscalationRiskReport(
            risk_score=0.3,  # Should give health_score of 70
            interpretation="low",
            unresolved_issues=0,
            days_until_predicted_conflict=30,
            factors={},
            recommendations=[]
        )
        mock_service.calculate_escalation_risk = AsyncMock(return_value=mock_risk)
        mock_service.find_trigger_phrase_patterns = AsyncMock(return_value={"most_impactful": []})
        mock_service.identify_conflict_chains = AsyncMock(return_value=[])
        mock_service.track_chronic_needs = AsyncMock(return_value=[])
        mock_db.get_previous_conflicts = MagicMock(return_value=[])

        response = client.get(f"/api/analytics/dashboard?relationship_id={relationship_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["health_score"] == 70  # (1.0 - 0.3) * 100

    @patch('app.routes.analytics.pattern_analysis_service')
    @patch('app.routes.analytics.db_service')
    def test_dashboard_resolution_rate(self, mock_db, mock_service):
        """Test resolution rate calculation"""
        relationship_id = str(uuid4())

        mock_risk = EscalationRiskReport(
            risk_score=0.5,
            interpretation="medium",
            unresolved_issues=2,
            days_until_predicted_conflict=14,
            factors={},
            recommendations=[]
        )
        mock_service.calculate_escalation_risk = AsyncMock(return_value=mock_risk)
        mock_service.find_trigger_phrase_patterns = AsyncMock(return_value={"most_impactful": []})
        mock_service.identify_conflict_chains = AsyncMock(return_value=[])
        mock_service.track_chronic_needs = AsyncMock(return_value=[])

        # 8 total, 6 resolved, 2 unresolved = 75% resolution rate
        mock_db.get_previous_conflicts = MagicMock(return_value=[
            {"is_resolved": True} for _ in range(6)
        ] + [{"is_resolved": False} for _ in range(2)])

        response = client.get(f"/api/analytics/dashboard?relationship_id={relationship_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["metrics"]["total_conflicts"] == 8
        assert data["metrics"]["resolved_conflicts"] == 6
        assert data["metrics"]["resolution_rate"] == 75.0

    @patch('app.routes.analytics.pattern_analysis_service')
    @patch('app.routes.analytics.db_service')
    def test_dashboard_with_all_data(self, mock_db, mock_service):
        """Test dashboard with complete data"""
        relationship_id = str(uuid4())

        mock_risk = EscalationRiskReport(
            risk_score=0.6,
            interpretation="high",
            unresolved_issues=3,
            days_until_predicted_conflict=7,
            factors={
                "avg_resentment": 7.0,
                "days_since_last": 3,
                "recurrence_pattern": 0.6,
                "unresolved_issues": 0.6,
                "resentment_accumulation": 0.7,
                "time_since_conflict": 0.4,
            },
            recommendations=[
                "🚨 High escalation risk - Schedule mediation",
                "📋 Address 3 unresolved issues",
                "💬 Talk to Luna"
            ]
        )
        mock_service.calculate_escalation_risk = AsyncMock(return_value=mock_risk)

        mock_service.find_trigger_phrase_patterns = AsyncMock(return_value={
            "most_impactful": [
                {
                    "phrase": "You always...",
                    "phrase_category": "blame",
                    "usage_count": 10,
                    "avg_emotional_intensity": 9.0,
                    "escalation_rate": 0.9,
                    "speaker": "partner_a",
                    "is_pattern_trigger": True
                }
            ]
        })

        mock_service.identify_conflict_chains = AsyncMock(return_value=[
            {
                "root_cause": "finances",
                "conflicts_in_chain": 4,
                "timeline": "finances → trust → intimacy → respect",
            }
        ])

        mock_service.track_chronic_needs = AsyncMock(return_value=[
            UnmetNeedRecurrence(
                need="feeling_heard",
                conflict_count=8,
                first_appeared="2024-01-01",
                days_appeared_in=60,
                is_chronic=True,
                percentage_of_conflicts=80.0
            ),
            UnmetNeedRecurrence(
                need="trust",
                conflict_count=6,
                first_appeared="2024-01-05",
                days_appeared_in=50,
                is_chronic=True,
                percentage_of_conflicts=60.0
            )
        ])

        mock_db.get_previous_conflicts = MagicMock(return_value=[
            {"is_resolved": True, "resentment_level": 5},
            {"is_resolved": True, "resentment_level": 6},
            {"is_resolved": True, "resentment_level": 7},
            {"is_resolved": False, "resentment_level": 8},
            {"is_resolved": False, "resentment_level": 8},
            {"is_resolved": False, "resentment_level": 9}
        ])

        response = client.get(f"/api/analytics/dashboard?relationship_id={relationship_id}")

        assert response.status_code == 200
        data = response.json()

        # Verify all data is present
        assert data["health_score"] == 40  # (1.0 - 0.6) * 100
        assert data["escalation_risk"]["interpretation"] == "high"
        assert len(data["trigger_phrases"]["most_impactful"]) == 1
        assert len(data["conflict_chains"]) == 1
        assert len(data["chronic_needs"]) == 2
        assert data["metrics"]["avg_resentment"] == 7.0
        assert len(data["insights"]) == 4

    @patch('app.routes.analytics.pattern_analysis_service')
    @patch('app.routes.analytics.db_service')
    def test_dashboard_error_handling(self, mock_db, mock_service):
        """Test dashboard error handling"""
        relationship_id = str(uuid4())

        # Simulate error
        mock_service.calculate_escalation_risk = AsyncMock(
            side_effect=Exception("Database error")
        )

        response = client.get(f"/api/analytics/dashboard?relationship_id={relationship_id}")

        assert response.status_code == 500

    @patch('app.routes.analytics.pattern_analysis_service')
    @patch('app.routes.analytics.db_service')
    def test_dashboard_empty_conflicts(self, mock_db, mock_service):
        """Test dashboard with no conflicts"""
        relationship_id = str(uuid4())

        mock_risk = EscalationRiskReport(
            risk_score=0.0,
            interpretation="low",
            unresolved_issues=0,
            days_until_predicted_conflict=30,
            factors={},
            recommendations=["Keep communication open"]
        )
        mock_service.calculate_escalation_risk = AsyncMock(return_value=mock_risk)
        mock_service.find_trigger_phrase_patterns = AsyncMock(return_value={"most_impactful": []})
        mock_service.identify_conflict_chains = AsyncMock(return_value=[])
        mock_service.track_chronic_needs = AsyncMock(return_value=[])
        mock_db.get_previous_conflicts = MagicMock(return_value=[])

        response = client.get(f"/api/analytics/dashboard?relationship_id={relationship_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["metrics"]["total_conflicts"] == 0
        assert data["metrics"]["resolution_rate"] == 0


class TestDashboardDataAggregation:
    """Test data aggregation logic"""

    def test_resolution_rate_calculation(self):
        """Test resolution rate formula"""
        total = 10
        resolved = 7
        rate = (resolved / total * 100) if total > 0 else 0
        assert rate == 70.0

    def test_resolution_rate_zero_conflicts(self):
        """Test resolution rate with zero conflicts"""
        total = 0
        resolved = 0
        rate = (resolved / total * 100) if total > 0 else 0
        assert rate == 0

    def test_health_score_formula(self):
        """Test health score calculation"""
        risk_score = 0.6
        health_score = int((1.0 - risk_score) * 100)
        assert health_score == 40

    def test_health_score_perfect(self):
        """Test health score for perfect relationship"""
        risk_score = 0.0
        health_score = int((1.0 - risk_score) * 100)
        assert health_score == 100

    def test_health_score_worst(self):
        """Test health score for worst case"""
        risk_score = 1.0
        health_score = int((1.0 - risk_score) * 100)
        assert health_score == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
