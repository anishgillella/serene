"""
Unit tests for Mediator Context - Phase 3
Tests Luna's context-aware mediation capabilities
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.main import app
from app.models.schemas import EscalationRiskReport, TriggerPhraseAnalysis, UnmetNeedRecurrence


client = TestClient(app)


class TestMediationContextEndpoint:
    """Test /api/mediator/context/{conflict_id} endpoint"""

    @patch('app.routes.mediator_context.db_service')
    @patch('app.routes.mediator_context.pattern_analysis_service')
    def test_get_mediation_context_success(self, mock_service, mock_db):
        """Test successful mediation context retrieval"""
        conflict_id = str(uuid4())
        relationship_id = str(uuid4())

        # Mock current conflict
        mock_conflict = {
            "id": conflict_id,
            "relationship_id": relationship_id,
            "metadata": {"topic": "finances"},
            "resentment_level": 7,
            "unmet_needs": ["feeling_heard", "trust"]
        }
        mock_db.get_conflict = MagicMock(return_value=mock_conflict)

        # Mock previous conflicts
        mock_db.get_previous_conflicts = MagicMock(return_value=[
            {
                "id": str(uuid4()),
                "is_resolved": False,
                "metadata": {"topic": "trust"},
                "resentment_level": 8,
                "started_at": "2024-12-20T10:00:00Z",
                "unmet_needs": ["communication"]
            },
            {
                "id": str(uuid4()),
                "is_resolved": True,
                "metadata": {"topic": "intimacy"},
                "resentment_level": 5,
                "started_at": "2024-12-15T10:00:00Z",
                "unmet_needs": []
            }
        ])

        # Mock pattern analysis
        mock_risk_report = EscalationRiskReport(
            risk_score=0.7,
            interpretation="high",
            unresolved_issues=1,
            days_until_predicted_conflict=7,
            factors={},
            recommendations=[]
        )
        mock_service.calculate_escalation_risk = AsyncMock(return_value=mock_risk_report)
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
        mock_service.find_trigger_phrase_patterns = AsyncMock(return_value={
            "most_impactful": [
                {
                    "phrase": "You never listen",
                    "phrase_category": "blame",
                    "usage_count": 5,
                    "avg_emotional_intensity": 8,
                    "escalation_rate": 0.8,
                    "speaker": "partner_a",
                    "is_pattern_trigger": True
                }
            ]
        })

        response = client.get(f"/api/mediator/context/{conflict_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["current_conflict"]["topic"] == "finances"
        assert data["current_conflict"]["resentment_level"] == 7
        assert "unresolved_issues" in data
        assert "chronic_needs" in data
        assert "high_impact_triggers" in data
        assert "escalation_risk" in data

    @patch('app.routes.mediator_context.db_service')
    def test_get_mediation_context_conflict_not_found(self, mock_db):
        """Test mediation context with non-existent conflict"""
        conflict_id = str(uuid4())

        mock_db.get_conflict = MagicMock(return_value=None)

        response = client.get(f"/api/mediator/context/{conflict_id}")

        assert response.status_code == 404

    @patch('app.routes.mediator_context.db_service')
    @patch('app.routes.mediator_context.pattern_analysis_service')
    def test_escalation_risk_critical_flag(self, mock_service, mock_db):
        """Test that critical escalation flag is set correctly"""
        conflict_id = str(uuid4())
        relationship_id = str(uuid4())

        mock_conflict = {
            "id": conflict_id,
            "relationship_id": relationship_id,
            "metadata": {"topic": "breakup"},
            "resentment_level": 9,
            "unmet_needs": []
        }
        mock_db.get_conflict = MagicMock(return_value=mock_conflict)
        mock_db.get_previous_conflicts = MagicMock(return_value=[])

        # Critical escalation risk
        critical_risk = EscalationRiskReport(
            risk_score=0.85,  # > 0.75
            interpretation="critical",
            unresolved_issues=5,
            days_until_predicted_conflict=1,
            factors={},
            recommendations=[]
        )
        mock_service.calculate_escalation_risk = AsyncMock(return_value=critical_risk)
        mock_service.track_chronic_needs = AsyncMock(return_value=[])
        mock_service.find_trigger_phrase_patterns = AsyncMock(return_value={"most_impactful": []})

        response = client.get(f"/api/mediator/context/{conflict_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["escalation_risk"]["is_critical"] is True


class TestEnhanceResponseEndpoint:
    """Test /api/mediator/enhance-response endpoint (Phase 3)"""

    @patch('app.routes.mediator_context.db_service')
    @patch('app.routes.mediator_context.pattern_analysis_service')
    def test_enhance_response_success(self, mock_service, mock_db):
        """Test successful response enhancement"""
        conflict_id = str(uuid4())
        relationship_id = str(uuid4())

        mock_conflict = {
            "id": conflict_id,
            "relationship_id": relationship_id,
            "metadata": {"topic": "finances"},
            "resentment_level": 7,
            "unmet_needs": ["feeling_heard"]
        }
        mock_db.get_conflict = MagicMock(return_value=mock_conflict)
        mock_db.get_previous_conflicts = MagicMock(return_value=[])

        mock_risk = EscalationRiskReport(
            risk_score=0.6,
            interpretation="high",
            unresolved_issues=2,
            days_until_predicted_conflict=7,
            factors={},
            recommendations=[]
        )
        mock_service.calculate_escalation_risk = AsyncMock(return_value=mock_risk)
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
        mock_service.find_trigger_phrase_patterns = AsyncMock(return_value={
            "most_impactful": []
        })

        response = client.post(
            "/api/mediator/enhance-response",
            json={
                "conflict_id": conflict_id,
                "response": "I understand you're frustrated about money",
                "user_message": "We never talk about money"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert "risk_warnings" in data
        assert "context_applied" in data
        assert "original_response" in data

    @patch('app.routes.mediator_context.db_service')
    @patch('app.routes.mediator_context.pattern_analysis_service')
    def test_enhance_response_critical_escalation_warning(self, mock_service, mock_db):
        """Test that critical escalation warning is generated"""
        conflict_id = str(uuid4())
        relationship_id = str(uuid4())

        mock_conflict = {
            "id": conflict_id,
            "relationship_id": relationship_id,
            "metadata": {"topic": "breakup"},
            "resentment_level": 10,
            "unmet_needs": []
        }
        mock_db.get_conflict = MagicMock(return_value=mock_conflict)
        mock_db.get_previous_conflicts = MagicMock(return_value=[])

        critical_risk = EscalationRiskReport(
            risk_score=0.9,
            interpretation="critical",
            unresolved_issues=10,
            days_until_predicted_conflict=1,
            factors={},
            recommendations=[]
        )
        mock_service.calculate_escalation_risk = AsyncMock(return_value=critical_risk)
        mock_service.track_chronic_needs = AsyncMock(return_value=[])
        mock_service.find_trigger_phrase_patterns = AsyncMock(return_value={
            "most_impactful": []
        })

        response = client.post(
            "/api/mediator/enhance-response",
            json={
                "conflict_id": conflict_id,
                "response": "Let's work through this together",
                "user_message": "I want to break up"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["risk_warnings"]) > 0

        critical_warning = next(
            (w for w in data["risk_warnings"] if w["type"] == "critical_escalation"),
            None
        )
        assert critical_warning is not None
        assert critical_warning["severity"] == "high"

    @patch('app.routes.mediator_context.db_service')
    @patch('app.routes.mediator_context.pattern_analysis_service')
    def test_enhance_response_trigger_phrase_detection(self, mock_service, mock_db):
        """Test detection of trigger phrases in response"""
        conflict_id = str(uuid4())
        relationship_id = str(uuid4())

        mock_conflict = {
            "id": conflict_id,
            "relationship_id": relationship_id,
            "metadata": {"topic": "communication"},
            "resentment_level": 6,
            "unmet_needs": []
        }
        mock_db.get_conflict = MagicMock(return_value=mock_conflict)
        mock_db.get_previous_conflicts = MagicMock(return_value=[])

        mock_risk = EscalationRiskReport(
            risk_score=0.5,
            interpretation="medium",
            unresolved_issues=1,
            days_until_predicted_conflict=14,
            factors={},
            recommendations=[]
        )
        mock_service.calculate_escalation_risk = AsyncMock(return_value=mock_risk)
        mock_service.track_chronic_needs = AsyncMock(return_value=[])
        mock_service.find_trigger_phrase_patterns = AsyncMock(return_value={
            "most_impactful": [
                {
                    "phrase": "You never listen",
                    "category": "blame",
                    "escalation_rate": 0.8
                }
            ]
        })

        response = client.post(
            "/api/mediator/enhance-response",
            json={
                "conflict_id": conflict_id,
                "response": "You never listen to what I'm saying",
                "user_message": "I feel unheard"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Check if trigger phrase was detected
        trigger_warning = next(
            (w for w in data["risk_warnings"] if w["type"] == "trigger_phrase_detected"),
            None
        )
        assert trigger_warning is not None

    @patch('app.routes.mediator_context.db_service')
    @patch('app.routes.mediator_context.pattern_analysis_service')
    def test_enhance_response_addresses_chronic_needs(self, mock_service, mock_db):
        """Test that suggestions address chronic needs"""
        conflict_id = str(uuid4())
        relationship_id = str(uuid4())

        mock_conflict = {
            "id": conflict_id,
            "relationship_id": relationship_id,
            "metadata": {"topic": "trust"},
            "resentment_level": 7,
            "unmet_needs": ["trust"]
        }
        mock_db.get_conflict = MagicMock(return_value=mock_conflict)
        mock_db.get_previous_conflicts = MagicMock(return_value=[])

        mock_risk = EscalationRiskReport(
            risk_score=0.6,
            interpretation="high",
            unresolved_issues=3,
            days_until_predicted_conflict=7,
            factors={},
            recommendations=[]
        )
        mock_service.calculate_escalation_risk = AsyncMock(return_value=mock_risk)
        mock_service.track_chronic_needs = AsyncMock(return_value=[
            UnmetNeedRecurrence(
                need="trust",
                conflict_count=7,
                first_appeared="2024-01-01",
                days_appeared_in=30,
                is_chronic=True,
                percentage_of_conflicts=70.0
            )
        ])
        mock_service.find_trigger_phrase_patterns = AsyncMock(return_value={
            "most_impactful": []
        })

        response = client.post(
            "/api/mediator/enhance-response",
            json={
                "conflict_id": conflict_id,
                "response": "I want to rebuild what we have",
                "user_message": "Can we fix this?"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Check if chronic needs suggestion is present
        needs_suggestion = next(
            (s for s in data["suggestions"] if s["type"] == "address_chronic_needs"),
            None
        )
        assert needs_suggestion is not None


class TestLunaAgentContextInjection:
    """Test Luna agent context injection (Phase 3)"""

    def test_rag_mediator_with_context_initialization(self):
        """Test RAGMediator initialization with mediation context"""
        from app.agents.luna.agent import RAGMediator

        mock_rag_system = MagicMock()
        mediation_context = {
            "escalation_risk": {
                "score": 0.7,
                "interpretation": "high",
                "is_critical": False
            },
            "chronic_needs": ["feeling_heard", "trust"],
            "high_impact_triggers": [
                {
                    "phrase": "You never listen",
                    "category": "blame",
                    "escalation_rate": 0.8
                }
            ],
            "unresolved_issues": [
                {
                    "topic": "finances",
                    "days_unresolved": 10,
                    "resentment_level": 7
                }
            ]
        }

        agent = RAGMediator(
            rag_system=mock_rag_system,
            conflict_id="test-conflict",
            relationship_id="test-relationship",
            mediation_context=mediation_context,
            partner_a_name="Alex",
            partner_b_name="Jordan"
        )

        # Verify context is stored
        assert agent.mediation_context == mediation_context

        # Verify instructions include pattern awareness
        assert "RELATIONSHIP PATTERNS" in agent.instructions
        assert "HIGH" in agent.instructions
        assert "feeling_heard" in agent.instructions

    def test_pattern_awareness_section_generation(self):
        """Test that pattern awareness section is correctly generated"""
        from app.agents.luna.agent import RAGMediator

        mock_rag_system = MagicMock()
        context = {
            "escalation_risk": {
                "score": 0.85,
                "interpretation": "critical",
                "is_critical": True
            },
            "chronic_needs": ["feeling_heard"],
            "high_impact_triggers": [
                {
                    "phrase": "You never listen",
                    "category": "blame",
                    "escalation_rate": 0.8
                }
            ],
            "unresolved_issues": []
        }

        agent = RAGMediator(
            rag_system=mock_rag_system,
            conflict_id="test",
            relationship_id="test",
            mediation_context=context
        )

        section = agent._build_pattern_awareness_section()

        # Check for critical warning
        assert "⚠️ THIS RELATIONSHIP IS AT CRITICAL ESCALATION RISK" in section
        assert "Use extra care" in section

        # Check for triggers
        assert "You never listen" in section
        assert "80%" in section

        # Check for guidance
        assert "Recognize and name the patterns" in section


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
