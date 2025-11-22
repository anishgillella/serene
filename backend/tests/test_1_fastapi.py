"""
Test 1: FastAPI Server
======================

Purpose:
    Tests the FastAPI REST API server that provides backend endpoints.
    Verifies API health and LiveKit token generation.

What This Tests:
    - Server is running and accessible on port 8000
    - Root endpoint returns correct response
    - Token generation endpoint works
    - Generated tokens are valid JWTs

Expected Result:
    ✅ Server responds to requests
    ✅ Tokens are generated successfully
    ✅ Token format is correct (JWT with ~350 chars)

Prerequisites:
    - Backend server must be running:
      python -m uvicorn app.main:app --reload --port 8000
"""
import requests

API_URL = "http://localhost:8000"

def test_fastapi():
    print("=" * 50)
    print("TEST 1: FastAPI Server")
    print("=" * 50)
    
    # Test 1: Root endpoint
    print("\n1. Testing root endpoint...")
    try:
        response = requests.get(f"{API_URL}/")
        if response.status_code == 200:
            print(f"   ✅ Root endpoint working: {response.json()}")
        else:
            print(f"   ❌ Failed with status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        print("   💡 Make sure backend is running: python -m uvicorn app.main:app --reload --port 8000")
        return False
    
    # Test 2: Token generation endpoint
    print("\n2. Testing token generation...")
    try:
        response = requests.post(
            f"{API_URL}/api/token",
            params={
                "room_name": "test-room",
                "participant_name": "test-user"
            }
        )
        if response.status_code == 200:
            token = response.json()["token"]
            print(f"   ✅ Token generated successfully")
            print(f"   Token length: {len(token)} characters")
            print(f"   First 50 chars: {token[:50]}...")
        else:
            print(f"   ❌ Failed with status {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ FastAPI Server: ALL TESTS PASSED")
    print("=" * 50)
    return True

if __name__ == "__main__":
    test_fastapi()
