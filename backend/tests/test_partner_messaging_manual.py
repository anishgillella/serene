#!/usr/bin/env python3
"""
Manual test script for Partner Messaging Phase 1

Run this script to manually test all endpoints against a running server.
Make sure the backend server is running before executing.

Usage:
    cd backend
    python tests/test_partner_messaging_manual.py

Or with a custom API URL:
    API_URL=https://your-api.com python tests/test_partner_messaging_manual.py
"""

import os
import sys
import json
import requests
import asyncio
import websockets
from datetime import datetime

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
TEST_RELATIONSHIP_ID = "00000000-0000-0000-0000-000000000000"

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")


def print_test(name, success, details=""):
    status = f"{GREEN}✅ PASS{RESET}" if success else f"{RED}❌ FAIL{RESET}"
    print(f"{status} {name}")
    if details:
        print(f"   {YELLOW}{details}{RESET}")


def test_health():
    """Test API health endpoint"""
    try:
        response = requests.get(f"{API_URL}/")
        return response.status_code == 200
    except Exception as e:
        print(f"   Error: {e}")
        return False


def test_get_conversation():
    """Test getting/creating a conversation"""
    try:
        response = requests.get(
            f"{API_URL}/api/partner-messages/conversation",
            params={"relationship_id": TEST_RELATIONSHIP_ID}
        )

        if response.status_code != 200:
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

        data = response.json()
        if "id" in data and "relationship_id" in data:
            return data
        return None
    except Exception as e:
        print(f"   Error: {e}")
        return None


def test_send_message(conversation_id, sender="partner_a", content=None):
    """Test sending a message"""
    if content is None:
        content = f"Test message from {sender} at {datetime.now().isoformat()}"

    try:
        response = requests.post(
            f"{API_URL}/api/partner-messages/send",
            json={
                "conversation_id": conversation_id,
                "sender_id": sender,
                "content": content
            }
        )

        if response.status_code != 200:
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

        data = response.json()
        if "message" in data and "id" in data["message"]:
            return data["message"]
        return None
    except Exception as e:
        print(f"   Error: {e}")
        return None


def test_get_messages(conversation_id, limit=50):
    """Test getting messages"""
    try:
        response = requests.get(
            f"{API_URL}/api/partner-messages/messages",
            params={"conversation_id": conversation_id, "limit": limit}
        )

        if response.status_code != 200:
            print(f"   Status: {response.status_code}")
            return None

        data = response.json()
        return data
    except Exception as e:
        print(f"   Error: {e}")
        return None


def test_mark_delivered(message_id):
    """Test marking message as delivered"""
    try:
        response = requests.patch(
            f"{API_URL}/api/partner-messages/messages/{message_id}/delivered"
        )
        return response.status_code == 200
    except Exception as e:
        print(f"   Error: {e}")
        return False


def test_mark_read(message_id):
    """Test marking message as read"""
    try:
        response = requests.patch(
            f"{API_URL}/api/partner-messages/messages/{message_id}/read"
        )
        return response.status_code == 200
    except Exception as e:
        print(f"   Error: {e}")
        return False


def test_get_preferences(partner_id="partner_a"):
    """Test getting preferences"""
    try:
        response = requests.get(
            f"{API_URL}/api/partner-messages/preferences",
            params={
                "relationship_id": TEST_RELATIONSHIP_ID,
                "partner_id": partner_id
            }
        )

        if response.status_code != 200:
            print(f"   Status: {response.status_code}")
            return None

        return response.json()
    except Exception as e:
        print(f"   Error: {e}")
        return None


async def test_websocket(conversation_id, partner_id="partner_a"):
    """Test WebSocket connection"""
    ws_url = API_URL.replace("http://", "ws://").replace("https://", "wss://")
    uri = f"{ws_url}/api/realtime/partner-chat?conversation_id={conversation_id}&partner_id={partner_id}"

    try:
        async with websockets.connect(uri) as websocket:
            # Send a ping
            await websocket.send(json.dumps({"type": "ping"}))

            # Wait for pong
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)

            if data.get("type") == "pong":
                return True

            # Also test sending a message
            await websocket.send(json.dumps({
                "type": "message",
                "content": "WebSocket test message"
            }))

            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)

            return data.get("type") == "message_sent"

    except asyncio.TimeoutError:
        print("   Timeout waiting for WebSocket response")
        return False
    except Exception as e:
        print(f"   WebSocket error: {e}")
        return False


def run_all_tests():
    """Run all manual tests"""
    print_header("🧪 PARTNER MESSAGING PHASE 1 - MANUAL TESTS")
    print(f"API URL: {API_URL}")
    print(f"Test Relationship ID: {TEST_RELATIONSHIP_ID}")

    results = {"passed": 0, "failed": 0}

    # Test 1: API Health
    print_header("1. API Health Check")
    success = test_health()
    print_test("API is running", success)
    results["passed" if success else "failed"] += 1

    if not success:
        print(f"\n{RED}Cannot proceed - API is not running!{RESET}")
        print(f"Start the server with: cd backend && uvicorn app.main:app --reload")
        return False

    # Test 2: Get/Create Conversation
    print_header("2. Conversation Endpoints")
    conversation = test_get_conversation()
    success = conversation is not None
    print_test("Get/create conversation", success,
               f"ID: {conversation['id']}" if success else "")
    results["passed" if success else "failed"] += 1

    if not conversation:
        print(f"\n{RED}Cannot proceed - conversation creation failed!{RESET}")
        return False

    conversation_id = conversation["id"]

    # Test 3: Send Messages
    print_header("3. Send Message Endpoints")

    message_a = test_send_message(conversation_id, "partner_a", "Hello from Partner A!")
    success = message_a is not None
    print_test("Send message from partner_a", success,
               f"ID: {message_a['id']}" if success else "")
    results["passed" if success else "failed"] += 1

    message_b = test_send_message(conversation_id, "partner_b", "Hello from Partner B!")
    success = message_b is not None
    print_test("Send message from partner_b", success,
               f"ID: {message_b['id']}" if success else "")
    results["passed" if success else "failed"] += 1

    # Test 4: Get Messages
    print_header("4. Get Messages Endpoint")
    messages_data = test_get_messages(conversation_id)
    success = messages_data is not None and "messages" in messages_data
    print_test("Get messages", success,
               f"Count: {len(messages_data['messages'])}" if success else "")
    results["passed" if success else "failed"] += 1

    # Test 5: Message Status
    print_header("5. Message Status Endpoints")
    if message_a:
        success = test_mark_delivered(message_a["id"])
        print_test("Mark message as delivered", success)
        results["passed" if success else "failed"] += 1

        success = test_mark_read(message_a["id"])
        print_test("Mark message as read", success)
        results["passed" if success else "failed"] += 1

    # Test 6: Preferences
    print_header("6. Preferences Endpoints")
    prefs = test_get_preferences("partner_a")
    success = prefs is not None
    print_test("Get preferences for partner_a", success,
               f"Luna enabled: {prefs.get('luna_assistance_enabled')}" if success else "")
    results["passed" if success else "failed"] += 1

    prefs_b = test_get_preferences("partner_b")
    success = prefs_b is not None
    print_test("Get preferences for partner_b", success)
    results["passed" if success else "failed"] += 1

    # Test 7: WebSocket
    print_header("7. WebSocket Connection")
    try:
        success = asyncio.run(test_websocket(conversation_id, "partner_a"))
        print_test("WebSocket ping/pong", success)
        results["passed" if success else "failed"] += 1
    except Exception as e:
        print_test("WebSocket ping/pong", False, str(e))
        results["failed"] += 1

    # Summary
    print_header("📊 TEST SUMMARY")
    total = results["passed"] + results["failed"]
    print(f"{GREEN}Passed: {results['passed']}/{total}{RESET}")
    print(f"{RED}Failed: {results['failed']}/{total}{RESET}")

    if results["failed"] == 0:
        print(f"\n{GREEN}🎉 All tests passed!{RESET}")
    else:
        print(f"\n{RED}⚠️  Some tests failed. Check the output above.{RESET}")

    return results["failed"] == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
