"""
Pytest configuration and fixtures for multi-tenancy tests.

NOTE: These tests require a valid .env file with database credentials.
To run tests:
1. Copy .env.example to .env in the project root
2. Fill in the required credentials
3. Run: python -m pytest tests/ -v

For CI/CD, set environment variables before running tests.
"""
import pytest
import os
import sys
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

# Load environment variables from .env files before importing app
from dotenv import load_dotenv

# Try multiple locations for .env file
env_locations = [
    backend_path / '.env',
    Path(__file__).parent.parent / '.env',
    Path(__file__).parent / '.env',
]

env_loaded = False
for env_path in env_locations:
    if env_path.exists():
        load_dotenv(env_path)
        env_loaded = True
        break

# If no .env found, set minimal test environment variables
# These allow the app to load but won't enable full integration tests
if not env_loaded:
    test_env_vars = {
        'LIVEKIT_URL': 'wss://test.livekit.cloud',
        'LIVEKIT_API_KEY': 'test_key',
        'LIVEKIT_API_SECRET': 'test_secret',
        'OPENROUTER_API_KEY': 'test_key',
        'DEEPGRAM_API_KEY': 'test_key',
        'ELEVENLABS_API_KEY': 'test_key',
        'VOYAGE_API_KEY': 'test_key',
        'PINECONE_API_KEY': 'test_key',
        'MISTRAL_API_KEY': 'test_key',
        'DATABASE_URL': 'postgresql://test:test@localhost:5432/test_db',
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test_key',
        'AWS_ACCESS_KEY_ID': 'test_key',
        'AWS_SECRET_ACCESS_KEY': 'test_secret',
        'AWS_REGION': 'us-east-1',
        'S3_BUCKET_NAME': 'test-bucket',
    }
    for key, value in test_env_vars.items():
        if key not in os.environ:
            os.environ[key] = value


def has_valid_database():
    """Check if we have valid database credentials."""
    db_url = os.environ.get('DATABASE_URL', '')
    return db_url and 'test:test@localhost' not in db_url


# Skip integration tests if no real database
requires_database = pytest.mark.skipif(
    not has_valid_database(),
    reason="Requires valid DATABASE_URL in .env file"
)


@pytest.fixture(scope="function")
def test_client():
    """Create a test client for the FastAPI app.

    Note: scope="function" ensures rate limiter is reset between tests.
    """
    # Reset rate limiter before each test
    try:
        from app.middleware.security import rate_limiter
        rate_limiter.requests.clear()
    except ImportError:
        pass

    # Install compatible version of httpx if needed
    # pip install 'httpx<0.28'
    try:
        # Try using starlette's TestClient directly
        from starlette.testclient import TestClient
        from app.main import app

        # Reset rate limiter again after app import
        try:
            from app.middleware.security import rate_limiter
            rate_limiter.requests.clear()
        except ImportError:
            pass

        client = TestClient(app, raise_server_exceptions=False)
        yield client
    except TypeError:
        # Fallback: Use httpcore transport approach
        import httpx
        from app.main import app

        # Reset rate limiter for fallback path
        try:
            from app.middleware.security import rate_limiter
            rate_limiter.requests.clear()
        except ImportError:
            pass

        # For httpx >= 0.28, use different approach
        async def make_request(method, url, **kwargs):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                return await getattr(client, method.lower())(url, **kwargs)

        # Create a sync wrapper class
        import asyncio

        class SyncTestClient:
            def __init__(self, app):
                self.app = app
                self.base_url = "http://test"

            def _run(self, coro):
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()

            def get(self, url, **kwargs):
                return self._run(self._async_request("get", url, **kwargs))

            def post(self, url, **kwargs):
                return self._run(self._async_request("post", url, **kwargs))

            def put(self, url, **kwargs):
                return self._run(self._async_request("put", url, **kwargs))

            def delete(self, url, **kwargs):
                return self._run(self._async_request("delete", url, **kwargs))

            async def _async_request(self, method, url, **kwargs):
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=self.app),
                    base_url=self.base_url
                ) as client:
                    return await getattr(client, method)(url, **kwargs)

        client = SyncTestClient(app)
        yield client


@pytest.fixture
def sample_relationship_data():
    """Sample relationship data for testing."""
    return {
        "partner_a_name": "Test Partner A",
        "partner_b_name": "Test Partner B"
    }


@pytest.fixture
def default_relationship_id():
    """The default relationship ID (Adrian & Elara)."""
    return "00000000-0000-0000-0000-000000000000"
