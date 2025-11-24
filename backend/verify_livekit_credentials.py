#!/usr/bin/env python3
"""
Script to verify LiveKit credentials match the subdomain
"""
import os
from dotenv import load_dotenv
from livekit import api

load_dotenv()

api_key = os.getenv("LIVEKIT_API_KEY")
api_secret = os.getenv("LIVEKIT_API_SECRET")
url = os.getenv("LIVEKIT_URL")

print("=" * 60)
print("LiveKit Credentials Verification")
print("=" * 60)
print(f"URL: {url}")
print(f"API Key: {api_key[:10]}..." if api_key else "NOT SET")
print(f"API Secret: {'SET' if api_secret else 'NOT SET'}")
print()

if not api_key or not api_secret:
    print("❌ ERROR: Missing API credentials!")
    print("Please set LIVEKIT_API_KEY and LIVEKIT_API_SECRET in .env")
    exit(1)

# Extract subdomain from URL
if url:
    if "wss://" in url:
        subdomain = url.replace("wss://", "").split(".")[0]
    elif "https://" in url:
        subdomain = url.replace("https://", "").split(".")[0]
    else:
        subdomain = url.split(".")[0]
    print(f"Subdomain: {subdomain}")
    print()

# Try to generate a test token
try:
    token = api.AccessToken(api_key, api_secret)
    token.with_identity("test-user")
    token.with_grants(api.VideoGrants(room_join=True, room="test-room"))
    test_token = token.to_jwt()
    print("✅ Token generation successful!")
    print(f"   Token preview: {test_token[:50]}...")
    print()
    print("If you're still getting 'invalid API key' errors:")
    print("1. Verify the API key matches the subdomain in LiveKit Cloud dashboard")
    print("2. Check that LIVEKIT_URL matches your project subdomain")
    print("3. Regenerate API credentials in LiveKit Cloud if needed")
except Exception as e:
    print(f"❌ ERROR generating token: {e}")
    print()
    print("Possible issues:")
    print("1. API key/secret mismatch")
    print("2. API key doesn't belong to this subdomain")
    print("3. Credentials need to be regenerated in LiveKit Cloud")

