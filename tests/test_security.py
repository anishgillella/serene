"""
Phase 5: Security Hardening Tests

Tests verify:
1. Rate limiting functionality
2. Security headers in responses
3. Input validation and sanitization
4. UUID format validation
5. XSS and SQL injection prevention
6. Audit logging
"""
import pytest
import uuid
import os
import time


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


class TestInputValidation:
    """Test input validation and sanitization."""

    def test_valid_uuid_format(self):
        """Test UUID format validation."""
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

        from app.middleware.security import InputValidator

        # Valid UUIDs
        assert InputValidator.is_valid_uuid("00000000-0000-0000-0000-000000000000") is True
        assert InputValidator.is_valid_uuid("123e4567-e89b-12d3-a456-426614174000") is True
        assert InputValidator.is_valid_uuid(str(uuid.uuid4())) is True

        # Invalid UUIDs
        assert InputValidator.is_valid_uuid("not-a-uuid") is False
        assert InputValidator.is_valid_uuid("") is False
        assert InputValidator.is_valid_uuid("12345") is False
        assert InputValidator.is_valid_uuid("123e4567-e89b-12d3-a456") is False

    def test_xss_sanitization(self):
        """Test XSS pattern detection and removal."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.middleware.security import InputValidator

        # Script tags should be detected
        xss_input = "<script>alert('xss')</script>"
        sanitized = InputValidator.sanitize_text(xss_input)
        assert "<script>" not in sanitized.lower()
        assert "alert" not in sanitized.lower()

        # JavaScript: protocol should be detected
        xss_input2 = "javascript:alert('xss')"
        sanitized2 = InputValidator.sanitize_text(xss_input2)
        assert "javascript:" not in sanitized2.lower()

        # Event handlers should be sanitized
        xss_input3 = '<img onerror="alert(1)">'
        sanitized3 = InputValidator.sanitize_text(xss_input3)
        assert "onerror" not in sanitized3.lower()

        # Normal text should pass through (with HTML encoding)
        normal_text = "Hello, this is normal text!"
        sanitized_normal = InputValidator.sanitize_text(normal_text)
        assert "Hello" in sanitized_normal

    def test_sql_injection_detection(self):
        """Test SQL injection pattern detection."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.middleware.security import InputValidator

        # SQL injection patterns should be detected
        assert InputValidator.check_sql_injection("' OR '1'='1") is True
        assert InputValidator.check_sql_injection("'; DROP TABLE users;--") is True
        assert InputValidator.check_sql_injection("UNION SELECT * FROM passwords") is True

        # Normal text should not be flagged
        assert InputValidator.check_sql_injection("Hello world") is False
        assert InputValidator.check_sql_injection("My name is John") is False
        assert InputValidator.check_sql_injection("") is False

    def test_validate_relationship_id(self):
        """Test relationship_id validation."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.middleware.security import InputValidator

        # Valid relationship IDs
        assert InputValidator.validate_relationship_id("00000000-0000-0000-0000-000000000000") is True
        assert InputValidator.validate_relationship_id(str(uuid.uuid4())) is True

        # Invalid relationship IDs
        assert InputValidator.validate_relationship_id("invalid-id") is False
        assert InputValidator.validate_relationship_id("") is False


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limiter_allows_requests(self):
        """Test that rate limiter allows requests within limits."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.middleware.security import RateLimiter

        limiter = RateLimiter()

        # Create mock request
        class MockRequest:
            class MockClient:
                host = "127.0.0.1"

            client = MockClient()
            headers = {}
            query_params = {}

            class MockUrl:
                path = "/api/test"

            url = MockUrl()

        request = MockRequest()

        # First request should be allowed
        allowed, headers = limiter.is_allowed(request)
        assert allowed is True
        assert "X-RateLimit-Limit" in headers
        assert "X-RateLimit-Remaining" in headers

    def test_rate_limiter_blocks_excess_requests(self):
        """Test that rate limiter blocks requests over limit."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.middleware.security import RateLimiter

        limiter = RateLimiter()
        # Set a very low limit for testing
        limiter.config["/api/test-limit"] = {"limit": 3, "window": 60}

        class MockRequest:
            class MockClient:
                host = "192.168.1.100"

            client = MockClient()
            headers = {}
            query_params = {}

            class MockUrl:
                path = "/api/test-limit"

            url = MockUrl()

        request = MockRequest()

        # Make requests up to and beyond limit
        for i in range(3):
            allowed, _ = limiter.is_allowed(request)
            assert allowed is True, f"Request {i+1} should be allowed"

        # Next request should be blocked
        allowed, headers = limiter.is_allowed(request)
        assert allowed is False
        assert "Retry-After" in headers

    def test_rate_limit_headers(self):
        """Test that rate limit headers are returned."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.middleware.security import RateLimiter

        limiter = RateLimiter()

        class MockRequest:
            class MockClient:
                host = "10.0.0.1"

            client = MockClient()
            headers = {}
            query_params = {}

            class MockUrl:
                path = "/api/check-headers"

            url = MockUrl()

        request = MockRequest()
        allowed, headers = limiter.is_allowed(request)

        assert "X-RateLimit-Limit" in headers
        assert "X-RateLimit-Remaining" in headers
        assert "X-RateLimit-Reset" in headers
        assert int(headers["X-RateLimit-Limit"]) > 0


@requires_database
class TestSecurityHeaders:
    """Test security headers in API responses."""

    def test_security_headers_present(self, test_client):
        """Test that security headers are present in responses."""
        response = test_client.get("/")

        # Check for security headers
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

        assert "X-XSS-Protection" in response.headers

    def test_request_id_header(self, test_client):
        """Test that request ID header is added."""
        response = test_client.get("/")

        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0

    def test_rate_limit_headers_present(self, test_client):
        """Test that rate limit headers are present."""
        response = test_client.get("/api/relationships/default/id")

        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers


@requires_database
class TestDataIsolationSecurity:
    """Test that data is properly isolated between relationships."""

    def test_cannot_access_other_relationship_data(self, test_client):
        """Test that one relationship cannot access another's conflicts."""
        # Create two separate relationships
        response1 = test_client.post(
            "/api/relationships/create",
            json={"partner_a_name": "Alice", "partner_b_name": "Bob"}
        )
        relationship_id_1 = response1.json()["relationship_id"]

        response2 = test_client.post(
            "/api/relationships/create",
            json={"partner_a_name": "Charlie", "partner_b_name": "Diana"}
        )
        relationship_id_2 = response2.json()["relationship_id"]

        # Create a conflict for relationship 1
        conflict_response = test_client.post(
            "/api/conflicts/create",
            json={"relationship_id": relationship_id_1}
        )
        conflict_id = conflict_response.json()["conflict_id"]

        # Try to access from relationship 2 - should not see the conflict
        list_response = test_client.get(f"/api/conflicts?relationship_id={relationship_id_2}")
        conflicts = list_response.json().get("conflicts", [])
        conflict_ids = [c["id"] for c in conflicts]

        assert conflict_id not in conflict_ids, "Relationship 2 should not see Relationship 1's conflicts"

    def test_cannot_create_conflict_for_invalid_relationship(self, test_client):
        """Test that creating a conflict with invalid relationship_id fails."""
        fake_relationship_id = str(uuid.uuid4())

        response = test_client.post(
            "/api/conflicts/create",
            json={"relationship_id": fake_relationship_id}
        )

        assert response.status_code == 404


class TestValidationHelpers:
    """Test validation helper functions."""

    def test_validate_uuid_helper(self):
        """Test the validate_uuid helper function."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.middleware.security import validate_uuid
        from fastapi import HTTPException

        # Valid UUID should pass
        valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
        result = validate_uuid(valid_uuid, "test_id")
        assert result == valid_uuid

        # Invalid UUID should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            validate_uuid("not-a-uuid", "test_id")

        assert exc_info.value.status_code == 400
        assert "Invalid" in exc_info.value.detail


class TestAuditLogging:
    """Test audit logging functionality."""

    def test_audit_logger_initialization(self):
        """Test that audit logger initializes correctly."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.middleware.security import AuditLogger

        logger = AuditLogger()
        assert logger is not None

    def test_audit_log_format(self):
        """Test audit log entry format."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.middleware.security import AuditLogger

        logger = AuditLogger()

        # Create a mock request
        class MockRequest:
            class MockClient:
                host = "127.0.0.1"

            client = MockClient()
            headers = {"User-Agent": "TestAgent/1.0"}
            method = "GET"

            class MockUrl:
                path = "/api/test"

            url = MockUrl()

        # This should not raise an exception
        logger.log(
            action="READ",
            table_name="test_table",
            request=MockRequest(),
            record_id="test-123",
            relationship_id="00000000-0000-0000-0000-000000000000",
            status_code=200
        )


class TestSecurityMiddlewareIntegration:
    """Test security middleware integration."""

    def test_middleware_imports(self):
        """Test that all security middleware can be imported."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.middleware.security import (
            RateLimitMiddleware,
            SecurityHeadersMiddleware,
            RequestIDMiddleware,
            InputValidator,
            validate_uuid,
            audit_logger,
            rate_limiter,
        )

        assert RateLimitMiddleware is not None
        assert SecurityHeadersMiddleware is not None
        assert RequestIDMiddleware is not None
        assert InputValidator is not None
        assert validate_uuid is not None
        assert audit_logger is not None
        assert rate_limiter is not None

    def test_middleware_package_exports(self):
        """Test that middleware package exports all components."""
        import sys
        from pathlib import Path

        backend_path = Path(__file__).parent.parent / 'backend'
        sys.path.insert(0, str(backend_path))

        from app.middleware import (
            RateLimitMiddleware,
            SecurityHeadersMiddleware,
            RequestIDMiddleware,
            InputValidator,
            validate_uuid,
            audit_logger,
            rate_limiter,
        )

        # All should be importable from the package
        assert RateLimitMiddleware is not None
        assert SecurityHeadersMiddleware is not None
