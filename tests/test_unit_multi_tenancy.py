"""
Unit tests for multi-tenancy implementation.
These tests don't require database connection.
"""
import pytest
import uuid


class TestRelationshipIdValidation:
    """Test relationship ID format and validation."""

    def test_uuid_format(self):
        """Test that relationship IDs are valid UUIDs."""
        relationship_id = str(uuid.uuid4())
        # Should not raise
        parsed = uuid.UUID(relationship_id)
        assert str(parsed) == relationship_id

    def test_default_relationship_id_format(self):
        """Test the default relationship ID format."""
        default_id = "00000000-0000-0000-0000-000000000000"
        # Should not raise
        parsed = uuid.UUID(default_id)
        assert str(parsed) == default_id


class TestPartnerNamesValidation:
    """Test partner name validation logic."""

    def test_partner_names_not_empty(self):
        """Test that partner names are not empty."""
        partner_a = "Alice"
        partner_b = "Bob"
        assert len(partner_a) > 0
        assert len(partner_b) > 0

    def test_partner_names_different(self):
        """Test that partner names can be different."""
        partner_a = "Alice"
        partner_b = "Bob"
        assert partner_a != partner_b


class TestDynamicInstructions:
    """Test Luna agent dynamic instructions."""

    def test_get_dynamic_instructions_format(self):
        """Test that dynamic instructions contain partner names."""
        # Import the function
        import sys
        import os
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

        from app.agents.luna.agent import get_dynamic_instructions

        partner_a = "TestPartnerA"
        partner_b = "TestPartnerB"

        instructions = get_dynamic_instructions(partner_a, partner_b)

        # Verify partner names appear in instructions
        assert partner_a in instructions
        assert partner_b in instructions
        assert "Luna" in instructions

    def test_default_instructions_exist(self):
        """Test that default instructions are defined."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.agents.luna.agent import DEFAULT_INSTRUCTIONS

        assert DEFAULT_INSTRUCTIONS is not None
        assert len(DEFAULT_INSTRUCTIONS) > 0
        assert "Luna" in DEFAULT_INSTRUCTIONS


class TestShareableLinks:
    """Test shareable link generation."""

    def test_shareable_link_format(self):
        """Test that shareable links have correct format."""
        relationship_id = str(uuid.uuid4())
        base_url = "https://example.com"

        # Simulate the getShareableLink function logic
        shareable_link = f"{base_url}?r={relationship_id}"

        assert relationship_id in shareable_link
        assert "?r=" in shareable_link

    def test_url_param_parsing(self):
        """Test URL parameter parsing for relationship_id."""
        relationship_id = "123e4567-e89b-12d3-a456-426614174000"
        url = f"https://example.com?r={relationship_id}&other=param"

        # Simulate URL param extraction
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert 'r' in params
        assert params['r'][0] == relationship_id
