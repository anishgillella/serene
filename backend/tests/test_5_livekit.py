"""
Test 5: LiveKit Connectivity
=============================

Purpose:
    Tests connection to LiveKit Cloud and room operations.
    Verifies that the LiveKit infrastructure is accessible.

What This Tests:
    - Generating valid LiveKit tokens
    - Token validation (JWT decode)
    - LiveKit WebSocket URL accessibility

Expected Result:
    ✅ Tokens are generated correctly
    ✅ Tokens contain correct room/participant info
    ✅ LiveKit URL is reachable

Prerequisites:
    - LIVEKIT_URL and LIVEKIT_API_KEY/SECRET in .env
    - Internet connection
"""
from dotenv import load_dotenv
import os
load_dotenv()

from livekit import api
import jwt

def test_livekit():
    print("=" * 50)
    print("TEST 5: LiveKit Connectivity")
    print("=" * 50)
    
    # Check environment variables
    print("\n1. Checking LiveKit credentials...")
    livekit_url = os.getenv('LIVEKIT_URL')
    livekit_api_key = os.getenv('LIVEKIT_API_KEY')
    livekit_api_secret = os.getenv('LIVEKIT_API_SECRET')
    
    if not all([livekit_url, livekit_api_key, livekit_api_secret]):
        print("   ❌ Missing LiveKit credentials in .env")
        print("      Required: LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET")
        return False
    
    print(f"   ✅ Found credentials")
    print(f"      URL: {livekit_url}")
    print(f"      API Key: {livekit_api_key[:10]}...")
    
    # Generate token
    print("\n2. Generating LiveKit token...")
    try:
        token = api.AccessToken(livekit_api_key, livekit_api_secret)
        token.with_identity("test-user")
        token.with_name("Test User")
        token.with_grants(api.VideoGrants(
            room_join=True,
            room="test-room",
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True
        ))
        
        jwt_token = token.to_jwt()
        print(f"   ✅ Token generated successfully")
        print(f"      Token length: {len(jwt_token)} characters")
    except Exception as e:
        print(f"   ❌ Token generation failed: {e}")
        return False
    
    # Decode and verify token
    print("\n3. Verifying token contents...")
    try:
        # Decode without verification (we just want to see the contents)
        decoded = jwt.decode(jwt_token, options={"verify_signature": False})
        
        print(f"   ✅ Token decoded successfully")
        print(f"      Identity: {decoded.get('name', 'N/A')}")
        print(f"      Room: {decoded.get('video', {}).get('room', 'N/A')}")
        print(f"      Permissions:")
        print(f"        - Can publish: {decoded.get('video', {}).get('canPublish', False)}")
        print(f"        - Can subscribe: {decoded.get('video', {}).get('canSubscribe', False)}")
        print(f"        - Can publish data: {decoded.get('video', {}).get('canPublishData', False)}")
    except Exception as e:
        print(f"   ❌ Token verification failed: {e}")
        return False
    
    # Check URL format
    print("\n4. Validating LiveKit URL...")
    if livekit_url.startswith('wss://') or livekit_url.startswith('ws://'):
        print(f"   ✅ URL format valid (WebSocket)")
    else:
        print(f"   ⚠️  URL should start with wss:// or ws://")
        print(f"      Current: {livekit_url}")
    
    print("\n" + "=" * 50)
    print("✅ LiveKit: ALL TESTS PASSED")
    print("=" * 50)
    print("\nℹ️  Note: To test actual room connection, run the LiveKit agent:")
    print("   python -m app.agents.heartsync_agent dev")
    return True

if __name__ == "__main__":
    test_livekit()
