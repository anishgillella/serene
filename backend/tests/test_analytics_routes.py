"""
Integration tests for Analytics Routes - Phase 2
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.main import app
from app.models.schemas import EscalationRiskReport
from app.services.pattern_analysis_service import pattern_analysis_service


client = TestClient(app)


class TestEscalationRiskEndpoint:
    """Test /api/analytics/escalation-risk endpoint"""

    @patch('app.routes.analytics.pattern_analysis_service')
    def test_escalation_risk_success(self, mock_service):
        """Test successful escalation risk retrieval"""
        mock_risk_report = EscalationRiskReport(
            risk_score=0.6,
            interpretation="high",
            unresolved_issues=2,
            days_until_predicted_conflict=7,
            factors={
                "unresolved_issues": 0.4,
                "resentment_accumulation": 0.6,
                "time_since_conflict": 0.5,
                "recurrence_pattern": 0.8,
                "avg_resentment": 6.0,
                "days_since_last": 3,
            },
            recommendations=[
                "Schedule mediation",
                "Address unresolved issues"
            ]
        )

        mock_service.calculate_escalation_risk = AsyncMock(return_value=mock_risk_report)

        response = client.get("/api/analytics/escalation-risk?relationship_id=test-rel-id")

        assert response.status_code == 200
        data = response.json()
        assert data["risk_score"] == 0.6
        assert data["interpretation"] == "high"
        assert data["unresolved_issues"] == 2

    @patch('app.routes.analytics.pattern_analysis_service')
    def test_escalation_risk_default_relationship(self, mock_service):
        """Test escalation risk with default relationship ID"""
        mock_risk_report = EscalationRiskReport(
            risk_score=0.0,
            interpretation="low",
            unresolved_issues=0,
            days_until_predicted_conflict=30,
            factors={},
            recommendations=[]
        )

        mock_service.calculate_escalation_risk = AsyncMock(return_value=mock_risk_report)

        response = client.get("/api/analytics/escalation-risk")

        assert response.status_code == 200
        mock_service.calculate_escalation_risk.assert_called()

    @patch('app.routes.analytics.pattern_analysis_service')
    def test_escalation_risk_error(self, mock_service):
        """Test escalation risk error handling"""
        mock_service.calculate_escalation_risk = AsyncMock(side_effect=Exception("DB error"))

        response = client.get("/api/analytics/escalation-risk")

        assert response.status_code == 500


class TestTriggerPhrasesEndpoint:
    """Test /api/analytics/trigger-phrases endpoint"""

    @patch('app.routes.analytics.pattern_analysis_service')
    def test_trigger_phrases_success(self, mock_service):
        """Test successful trigger phrases retrieval"""
        mock_result = {
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
            ],
            "trends": []
        }

        mock_service.find_trigger_phrase_patterns = AsyncMock(return_value=mock_result)

        response = client.get("/api/analytics/trigger-phrases")

        assert response.status_code == 200
        data = response.json()
        assert len(data["most_impactful"]) == 1
        assert data["most_impactful"][0]["phrase"] == "You never listen"

    @patch('app.routes.analytics.pattern_analysis_service')
    def test_trigger_phrases_empty(self, mock_service):
        """Test trigger phrases with no data"""
        mock_result = {"most_impactful": [], "trends": []}

        mock_service.find_trigger_phrase_patterns = AsyncMock(return_value=mock_result)

        response = client.get("/api/analytics/trigger-phrases")

        assert response.status_code == 200
        assert response.json()["most_impactful"] == []


class TestConflictChainsEndpoint:
    """Test /api/analytics/conflict-chains endpoint"""

    @patch('app.routes.analytics.pattern_analysis_service')
    def test_conflict_chains_success(self, mock_service):
        """Test successful conflict chains retrieval"""
        mock_chains = [
            {
                "root_cause": "finances",
                "conflicts_in_chain": 3,
                "timeline": "finances → trust → communication",
                "unmet_needs": ["feeling_heard"],
                "resolution_attempts": 1,
                "is_resolved": False
            }
        ]

        mock_service.identify_conflict_chains = AsyncMock(return_value=mock_chains)

        response = client.get("/api/analytics/conflict-chains")

        assert response.status_code == 200
        data = response.json()
        assert len(data["chains"]) == 1
        assert data["chains"][0]["conflicts_in_chain"] == 3

    @patch('app.routes.analytics.pattern_analysis_service')
    def test_conflict_chains_empty(self, mock_service):
        """Test conflict chains with no chains"""
        mock_service.identify_conflict_chains = AsyncMock(return_value=[])

        response = client.get("/api/analytics/conflict-chains")

        assert response.status_code == 200
        assert response.json()["chains"] == []


class TestUnmetNeedsEndpoint:
    """Test /api/analytics/unmet-needs endpoint"""

    @patch('app.routes.analytics.pattern_analysis_service')
    def test_unmet_needs_success(self, mock_service):
        """Test successful unmet needs retrieval"""
        from app.models.schemas import UnmetNeedRecurrence

        mock_needs = [
            UnmetNeedRecurrence(
                need="feeling_heard",
                conflict_count=5,
                first_appeared="2024-01-01",
                days_appeared_in=30,
                is_chronic=True,
                percentage_of_conflicts=50.0
            )
        ]

        mock_service.track_chronic_needs = AsyncMock(return_value=mock_needs)

        response = client.get("/api/analytics/unmet-needs")

        assert response.status_code == 200
        data = response.json()
        assert len(data["chronic_needs"]) == 1
        assert data["chronic_needs"][0]["need"] == "feeling_heard"


class TestHealthScoreEndpoint:
    """Test /api/analytics/health-score endpoint"""

    @patch('app.routes.analytics.pattern_analysis_service')
    @patch('app.routes.analytics.db_service')
    def test_health_score_success(self, mock_db, mock_service):
        """Test successful health score retrieval"""
        mock_risk_report = EscalationRiskReport(
            risk_score=0.4,
            interpretation="medium",
            unresolved_issues=1,
            days_until_predicted_conflict=14,
            factors={
                "unresolved_issues": 0.2,
                "resentment_accumulation": 0.4,
                "time_since_conflict": 0.5,
                "recurrence_pattern": 0.5,
                "avg_resentment": 5.0,
                "days_since_last": 5,
            },
            recommendations=[]
        )

        mock_service.calculate_escalation_risk = AsyncMock(return_value=mock_risk_report)
        mock_db.get_previous_conflicts = MagicMock(return_value=[
            {"is_resolved": False},
            {"is_resolved": True},
            {"is_resolved": True}
        ])

        response = client.get("/api/analytics/health-score")

        assert response.status_code == 200
        data = response.json()
        assert data["value"] == 60  # (1.0 - 0.4) * 100
        assert "trend" in data
        assert "breakdownFactors" in data

    @patch('app.routes.analytics.pattern_analysis_service')
    @patch('app.routes.analytics.db_service')
    def test_health_score_trending_up(self, mock_db, mock_service):
        """Test health score trend calculation"""
        mock_risk_report = EscalationRiskReport(
            risk_score=0.5,
            interpretation="medium",
            unresolved_issues=2,
            days_until_predicted_conflict=10,
            factors={
                "avg_resentment": 5.0,
                "days_since_last": 3,
                "recurrence_pattern": 0.5,
                "unresolved_issues": 0.4,
                "resentment_accumulation": 0.5,
                "time_since_conflict": 0.6,
            },
            recommendations=[]
        )

        mock_service.calculate_escalation_risk = AsyncMock(return_value=mock_risk_report)
        # More unresolved in recent conflicts = trend is "down" (improving)
        mock_db.get_previous_conflicts = MagicMock(return_value=[
            {"is_resolved": True},   # Recent: 1 unresolved
            {"is_resolved": True},
            {"is_resolved": True},
            {"is_resolved": True},
            {"is_resolved": True},
            {"is_resolved": False},  # Older: 3 unresolved
            {"is_resolved": False},
            {"is_resolved": False},
            {"is_resolved": True},
        ])

        response = client.get("/api/analytics/health-score")

        assert response.status_code == 200
        data = response.json()
        assert data["trend"] == "up"


class TestDashboardEndpoint:
    """Test /api/analytics/dashboard endpoint"""

    @patch('app.routes.analytics.pattern_analysis_service')
    @patch('app.routes.analytics.db_service')
    def test_dashboard_success(self, mock_db, mock_service):
        """Test successful dashboard data retrieval"""
        mock_risk_report = EscalationRiskReport(
            risk_score=0.3,
            interpretation="low",
            unresolved_issues=0,
            days_until_predicted_conflict=30,
            factors={
                "unresolved_issues": 0.0,
                "resentment_accumulation": 0.3,
                "time_since_conflict": 0.8,
                "recurrence_pattern": 0.2,
                "avg_resentment": 3.0,
                "days_since_last": 10,
            },
            recommendations=["Keep communication open"]
        )

        mock_phrases = {"most_impactful": [], "trends": []}
        mock_chains = []
        from app.models.schemas import UnmetNeedRecurrence
        mock_needs = []

        mock_service.calculate_escalation_risk = AsyncMock(return_value=mock_risk_report)
        mock_service.find_trigger_phrase_patterns = AsyncMock(return_value=mock_phrases)
        mock_service.identify_conflict_chains = AsyncMock(return_value=mock_chains)
        mock_service.track_chronic_needs = AsyncMock(return_value=mock_needs)

        mock_db.get_previous_conflicts = MagicMock(return_value=[
            {"is_resolved": True},
            {"is_resolved": True},
            {"is_resolved": False}
        ])

        response = client.get("/api/analytics/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert data["health_score"] == 70  # (1.0 - 0.3) * 100
        assert "escalation_risk" in data
        assert "trigger_phrases" in data
        assert "conflict_chains" in data
        assert "chronic_needs" in data
        assert "metrics" in data
        assert "insights" in data
        assert data["metrics"]["total_conflicts"] == 3
        assert data["metrics"]["resolved_conflicts"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
