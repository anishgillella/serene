"""
Phase 4: Gender-Neutral Data Model Tests

Tests verify:
1. PDF type normalization (boyfriend_profile -> partner_a_profile)
2. Partner name handling (dynamic names instead of hardcoded)
3. Schema backward compatibility
4. Luna agent dynamic instructions
5. Gender-neutral API responses
"""
import pytest
import uuid
import os


# Check if we have valid database credentials
def has_valid_database():
    """Check if we have valid database credentials."""
    db_url = os.environ.get('DATABASE_URL', '')
    return db_url and 'test:test@localhost' not in db_url


# Skip integration tests if no real database
requires_database = pytest.mark.skipif(
    not has_valid_database(),
    reason="Requires valid DATABASE_URL in .env file"
)


class TestPdfTypeNormalization:
    """Test PDF type normalization for backward compatibility."""

    def test_normalize_boyfriend_to_partner_a(self):
        """Test normalizing boyfriend_profile to partner_a_profile."""
        import sys
        from pathlib import Path

        # Set up test environment
        if 'DATABASE_URL' not in os.environ:
            os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost:5432/test_db'
            os.environ['LIVEKIT_URL'] = 'wss://test.livekit.cloud'
            os.environ['LIVEKIT_API_KEY'] = 'test_key'
            os.environ['LIVEKIT_API_SECRET'] = 'test_secret'
            os.environ['OPENROUTER_API_KEY'] = 'test_key'
            os.environ['DEEPGRAM_API_KEY'] = 'test_key'
            os.environ['ELEVENLABS_API_KEY'] = 'test_key'
            os.environ['VOYAGE_API_KEY'] = 'test_key'
            os.environ['PINECONE_API_KEY'] = 'test_key'
            os.environ['MISTRAL_API_KEY'] = 'test_key'
            os.environ['SUPABASE_URL'] = 'https://test.supabase.co'
            os.environ['SUPABASE_KEY'] = 'test_key'
            os.environ['AWS_ACCESS_KEY_ID'] = 'test_key'
            os.environ['AWS_SECRET_ACCESS_KEY'] = 'test_secret'
            os.environ['AWS_REGION'] = 'us-east-1'
            os.environ['S3_BUCKET_NAME'] = 'test-bucket'

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.models.schemas import normalize_pdf_type

        assert normalize_pdf_type('boyfriend_profile') == 'partner_a_profile'
        assert normalize_pdf_type('boyfriend') == 'partner_a_profile'

    def test_normalize_girlfriend_to_partner_b(self):
        """Test normalizing girlfriend_profile to partner_b_profile."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.models.schemas import normalize_pdf_type

        assert normalize_pdf_type('girlfriend_profile') == 'partner_b_profile'
        assert normalize_pdf_type('girlfriend') == 'partner_b_profile'

    def test_normalize_preserves_new_types(self):
        """Test that new gender-neutral types are preserved."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.models.schemas import normalize_pdf_type

        assert normalize_pdf_type('partner_a_profile') == 'partner_a_profile'
        assert normalize_pdf_type('partner_b_profile') == 'partner_b_profile'
        assert normalize_pdf_type('handbook') == 'handbook'

    def test_is_partner_a_profile(self):
        """Test partner A profile detection."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.models.schemas import is_partner_a_profile

        assert is_partner_a_profile('boyfriend_profile') is True
        assert is_partner_a_profile('partner_a_profile') is True
        assert is_partner_a_profile('partner_a') is True
        assert is_partner_a_profile('girlfriend_profile') is False
        assert is_partner_a_profile('handbook') is False

    def test_is_partner_b_profile(self):
        """Test partner B profile detection."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.models.schemas import is_partner_b_profile

        assert is_partner_b_profile('girlfriend_profile') is True
        assert is_partner_b_profile('partner_b_profile') is True
        assert is_partner_b_profile('partner_b') is True
        assert is_partner_b_profile('boyfriend_profile') is False
        assert is_partner_b_profile('handbook') is False


class TestConflictAnalysisSchema:
    """Test ConflictAnalysis schema with gender-neutral fields."""

    def test_schema_uses_partner_a_b_fields(self):
        """Test that schema has gender-neutral field names."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.models.schemas import ConflictAnalysis

        # Create instance
        analysis = ConflictAnalysis(
            conflict_id="test-123",
            fight_summary="Test conflict",
            root_causes=["test cause"],
            unmet_needs_partner_a=["need A1", "need A2"],
            unmet_needs_partner_b=["need B1"]
        )

        assert analysis.unmet_needs_partner_a == ["need A1", "need A2"]
        assert analysis.unmet_needs_partner_b == ["need B1"]

    def test_backward_compatibility_aliases(self):
        """Test that backward compatibility aliases work."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.models.schemas import ConflictAnalysis

        analysis = ConflictAnalysis(
            conflict_id="test-123",
            fight_summary="Test conflict",
            root_causes=["test cause"],
            unmet_needs_partner_a=["need from partner A"],
            unmet_needs_partner_b=["need from partner B"]
        )

        # Backward compatibility aliases should return same data
        assert analysis.unmet_needs_boyfriend == analysis.unmet_needs_partner_a
        assert analysis.unmet_needs_girlfriend == analysis.unmet_needs_partner_b


class TestDynamicPartnerNames:
    """Test dynamic partner name handling."""

    def test_luna_dynamic_instructions(self):
        """Test Luna agent generates dynamic instructions."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.agents.luna.agent import get_dynamic_instructions

        # Test with custom names
        instructions = get_dynamic_instructions("Alex", "Jordan")

        assert "Alex" in instructions
        assert "Jordan" in instructions
        assert "Luna" in instructions
        # Should NOT contain hardcoded names
        assert "Adrian" not in instructions
        assert "Elara" not in instructions

    def test_luna_default_instructions_no_hardcoded_names(self):
        """Test that default instructions don't have hardcoded names."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.agents.luna.agent import DEFAULT_INSTRUCTIONS

        # Default instructions should use generic Partner A/B
        assert "Partner A" in DEFAULT_INSTRUCTIONS or "Partner B" in DEFAULT_INSTRUCTIONS
        # Should NOT contain hardcoded Adrian/Elara
        assert "Adrian" not in DEFAULT_INSTRUCTIONS
        assert "Elara" not in DEFAULT_INSTRUCTIONS


class TestRepairPlanSchema:
    """Test RepairPlan schema with gender-neutral fields."""

    def test_partner_requesting_field(self):
        """Test that partner_requesting field accepts gender-neutral values."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.models.schemas import RepairPlan

        # Test with gender-neutral values
        plan_a = RepairPlan(
            conflict_id="test-123",
            partner_requesting="partner_a",
            steps=["Step 1"],
            apology_script="I'm sorry...",
            timing_suggestion="Tomorrow morning"
        )
        assert plan_a.partner_requesting == "partner_a"

        # Test with actual name
        plan_name = RepairPlan(
            conflict_id="test-456",
            partner_requesting="Alex",
            steps=["Step 1"],
            apology_script="I'm sorry...",
            timing_suggestion="Tomorrow morning"
        )
        assert plan_name.partner_requesting == "Alex"


@requires_database
class TestGenderNeutralAPIResponses:
    """Test that API responses use gender-neutral terminology."""

    def test_relationship_profile_gender_neutral(self, test_client, sample_relationship_data):
        """Test that relationship profile returns gender-neutral data."""
        # Create relationship
        create_response = test_client.post(
            "/api/relationships/create",
            json=sample_relationship_data
        )
        relationship_id = create_response.json()["relationship_id"]

        # Get profile
        response = test_client.get(f"/api/relationships/{relationship_id}/profile")

        assert response.status_code == 200
        data = response.json()
        assert "partner_a_name" in data["profile"]
        assert "partner_b_name" in data["profile"]

    def test_speaker_labels_use_partner_names(self, test_client, sample_relationship_data):
        """Test that speaker labels use actual partner names."""
        # Create relationship with specific names
        custom_data = {
            "partner_a_name": "Alex",
            "partner_b_name": "Jordan"
        }
        create_response = test_client.post(
            "/api/relationships/create",
            json=custom_data
        )
        relationship_id = create_response.json()["relationship_id"]

        # Get speaker labels
        response = test_client.get(f"/api/relationships/{relationship_id}/speaker-labels")

        assert response.status_code == 200
        data = response.json()
        assert data["labels"]["partner_a"] == "Alex"
        assert data["labels"]["partner_b"] == "Jordan"
        # Should NOT contain hardcoded names
        assert "Adrian" not in str(data)
        assert "Elara" not in str(data)


class TestSpeakerSegmentSchema:
    """Test SpeakerSegment schema."""

    def test_speaker_accepts_any_name(self):
        """Test that speaker field accepts any name."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.models.schemas import SpeakerSegment

        # Test with various names
        segment = SpeakerSegment(speaker="Alex", text="Hello")
        assert segment.speaker == "Alex"

        segment2 = SpeakerSegment(speaker="Jordan", text="Hi")
        assert segment2.speaker == "Jordan"
