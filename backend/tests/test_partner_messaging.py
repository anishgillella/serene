"""
Integration tests for Partner Messaging - Phase 1

Tests cover:
1. Conversation creation/retrieval
2. Message sending
3. Message retrieval with pagination
4. Message status updates
5. WebSocket connection (basic)
6. Preferences retrieval
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from uuid import uuid4
import json

from app.main import app
from app.services.db_service import db_service


client = TestClient(app)

# Test data
TEST_RELATIONSHIP_ID = "00000000-0000-0000-0000-000000000000"  # Default test relationship
TEST_CONVERSATION_ID = None  # Will be set after creation


class TestConversationEndpoints:
    """Test /api/partner-messages/conversation endpoint"""

    def test_get_or_create_conversation_success(self):
        """Test creating/getting a conversation for a relationship"""
        response = client.get(
            f"/api/partner-messages/conversation?relationship_id={TEST_RELATIONSHIP_ID}"
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert "relationship_id" in data
        assert data["relationship_id"] == TEST_RELATIONSHIP_ID
        assert "message_count" in data
        assert isinstance(data["message_count"], int)

        # Store for later tests
        global TEST_CONVERSATION_ID
        TEST_CONVERSATION_ID = data["id"]
        print(f"✅ Created/retrieved conversation: {TEST_CONVERSATION_ID}")

    def test_get_conversation_returns_same_id(self):
        """Test that getting conversation again returns same ID"""
        response1 = client.get(
            f"/api/partner-messages/conversation?relationship_id={TEST_RELATIONSHIP_ID}"
        )
        response2 = client.get(
            f"/api/partner-messages/conversation?relationship_id={TEST_RELATIONSHIP_ID}"
        )

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json()["id"] == response2.json()["id"]
        print("✅ Conversation ID is consistent across requests")

    def test_get_conversation_missing_relationship_id(self):
        """Test error when relationship_id is missing"""
        response = client.get("/api/partner-messages/conversation")
        assert response.status_code == 422  # Validation error
        print("✅ Missing relationship_id returns 422")


class TestMessageEndpoints:
    """Test message send/retrieve endpoints"""

    def test_send_message_success(self):
        """Test sending a message"""
        # First get conversation
        conv_response = client.get(
            f"/api/partner-messages/conversation?relationship_id={TEST_RELATIONSHIP_ID}"
        )
        conversation_id = conv_response.json()["id"]

        # Send message
        response = client.post(
            "/api/partner-messages/send",
            json={
                "conversation_id": conversation_id,
                "sender_id": "partner_a",
                "content": "Hello from Phase 1 test!"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "message" in data
        message = data["message"]
        assert message["content"] == "Hello from Phase 1 test!"
        assert message["sender_id"] == "partner_a"
        assert message["status"] == "sent"
        assert "id" in message
        assert "sent_at" in message

        print(f"✅ Message sent successfully: {message['id']}")
        return message["id"]

    def test_send_message_partner_b(self):
        """Test sending a message from partner_b"""
        conv_response = client.get(
            f"/api/partner-messages/conversation?relationship_id={TEST_RELATIONSHIP_ID}"
        )
        conversation_id = conv_response.json()["id"]

        response = client.post(
            "/api/partner-messages/send",
            json={
                "conversation_id": conversation_id,
                "sender_id": "partner_b",
                "content": "Reply from partner B!"
            }
        )

        assert response.status_code == 200
        assert response.json()["message"]["sender_id"] == "partner_b"
        print("✅ Partner B can send messages")

    def test_send_message_invalid_sender(self):
        """Test error with invalid sender_id"""
        conv_response = client.get(
            f"/api/partner-messages/conversation?relationship_id={TEST_RELATIONSHIP_ID}"
        )
        conversation_id = conv_response.json()["id"]

        response = client.post(
            "/api/partner-messages/send",
            json={
                "conversation_id": conversation_id,
                "sender_id": "invalid_partner",
                "content": "This should fail"
            }
        )

        assert response.status_code == 422  # Validation error
        print("✅ Invalid sender_id returns 422")

    def test_send_message_empty_content(self):
        """Test error with empty content"""
        conv_response = client.get(
            f"/api/partner-messages/conversation?relationship_id={TEST_RELATIONSHIP_ID}"
        )
        conversation_id = conv_response.json()["id"]

        response = client.post(
            "/api/partner-messages/send",
            json={
                "conversation_id": conversation_id,
                "sender_id": "partner_a",
                "content": ""
            }
        )

        assert response.status_code == 422  # Validation error
        print("✅ Empty content returns 422")

    def test_get_messages_success(self):
        """Test retrieving messages"""
        conv_response = client.get(
            f"/api/partner-messages/conversation?relationship_id={TEST_RELATIONSHIP_ID}"
        )
        conversation_id = conv_response.json()["id"]

        response = client.get(
            f"/api/partner-messages/messages?conversation_id={conversation_id}&limit=50"
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "messages" in data
        assert "has_more" in data
        assert isinstance(data["messages"], list)

        # Should have at least the messages we sent
        if len(data["messages"]) > 0:
            message = data["messages"][0]
            assert "id" in message
            assert "content" in message
            assert "sender_id" in message
            assert "sent_at" in message

        print(f"✅ Retrieved {len(data['messages'])} messages")

    def test_get_messages_pagination(self):
        """Test message pagination with limit"""
        conv_response = client.get(
            f"/api/partner-messages/conversation?relationship_id={TEST_RELATIONSHIP_ID}"
        )
        conversation_id = conv_response.json()["id"]

        # Get with limit of 1
        response = client.get(
            f"/api/partner-messages/messages?conversation_id={conversation_id}&limit=1"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) <= 1
        print("✅ Pagination limit works correctly")


class TestMessageStatusEndpoints:
    """Test message status update endpoints"""

    def test_mark_delivered(self):
        """Test marking a message as delivered"""
        # First send a message
        conv_response = client.get(
            f"/api/partner-messages/conversation?relationship_id={TEST_RELATIONSHIP_ID}"
        )
        conversation_id = conv_response.json()["id"]

        send_response = client.post(
            "/api/partner-messages/send",
            json={
                "conversation_id": conversation_id,
                "sender_id": "partner_a",
                "content": "Test delivery status"
            }
        )
        message_id = send_response.json()["message"]["id"]

        # Mark as delivered
        response = client.patch(f"/api/partner-messages/messages/{message_id}/delivered")

        assert response.status_code == 200
        assert response.json()["success"] == True
        print("✅ Message marked as delivered")

    def test_mark_read(self):
        """Test marking a message as read"""
        # First send a message
        conv_response = client.get(
            f"/api/partner-messages/conversation?relationship_id={TEST_RELATIONSHIP_ID}"
        )
        conversation_id = conv_response.json()["id"]

        send_response = client.post(
            "/api/partner-messages/send",
            json={
                "conversation_id": conversation_id,
                "sender_id": "partner_b",
                "content": "Test read status"
            }
        )
        message_id = send_response.json()["message"]["id"]

        # Mark as read
        response = client.patch(f"/api/partner-messages/messages/{message_id}/read")

        assert response.status_code == 200
        assert response.json()["success"] == True
        print("✅ Message marked as read")

    def test_mark_nonexistent_message(self):
        """Test marking a non-existent message"""
        fake_id = str(uuid4())
        response = client.patch(f"/api/partner-messages/messages/{fake_id}/read")

        assert response.status_code == 404
        print("✅ Non-existent message returns 404")


class TestPreferencesEndpoints:
    """Test messaging preferences endpoints"""

    def test_get_preferences_creates_defaults(self):
        """Test that getting preferences creates defaults if none exist"""
        response = client.get(
            f"/api/partner-messages/preferences?relationship_id={TEST_RELATIONSHIP_ID}&partner_id=partner_a"
        )

        assert response.status_code == 200
        data = response.json()

        # Verify default values
        assert data["luna_assistance_enabled"] == True
        assert data["suggestion_mode"] == "on_request"
        assert data["intervention_enabled"] == True
        assert data["intervention_sensitivity"] == "medium"
        assert data["show_read_receipts"] == True
        assert data["show_typing_indicators"] == True

        print("✅ Preferences retrieved with defaults")

    def test_get_preferences_invalid_partner(self):
        """Test error with invalid partner_id"""
        response = client.get(
            f"/api/partner-messages/preferences?relationship_id={TEST_RELATIONSHIP_ID}&partner_id=invalid"
        )

        assert response.status_code == 422
        print("✅ Invalid partner_id returns 422")


class TestWebSocketBasic:
    """Basic WebSocket connectivity tests"""

    def test_websocket_endpoint_exists(self):
        """Test that WebSocket endpoint is registered"""
        # We can't fully test WebSocket with TestClient, but we can verify the route exists
        # by checking the app routes
        routes = [route.path for route in app.routes]
        assert "/api/realtime/partner-chat" in routes
        print("✅ WebSocket endpoint is registered")


class TestDatabaseIntegration:
    """Test database service methods directly"""

    def test_db_service_get_or_create_conversation(self):
        """Test db_service.get_or_create_partner_conversation"""
        conversation = db_service.get_or_create_partner_conversation(TEST_RELATIONSHIP_ID)

        assert conversation is not None
        assert "id" in conversation
        assert conversation["relationship_id"] == TEST_RELATIONSHIP_ID
        print("✅ DB service creates conversation correctly")

    def test_db_service_save_and_get_messages(self):
        """Test db_service save and get messages"""
        conversation = db_service.get_or_create_partner_conversation(TEST_RELATIONSHIP_ID)

        # Save a message
        message = db_service.save_partner_message(
            conversation_id=conversation["id"],
            sender_id="partner_a",
            content="Direct DB test message"
        )

        assert message is not None
        assert message["content"] == "Direct DB test message"

        # Get messages
        messages = db_service.get_partner_messages(
            conversation_id=conversation["id"],
            limit=10
        )

        assert isinstance(messages, list)
        # Find our message
        found = any(m["content"] == "Direct DB test message" for m in messages)
        assert found, "Saved message should be retrievable"

        print("✅ DB service save/get messages works correctly")

    def test_db_service_update_status(self):
        """Test db_service.update_message_status"""
        conversation = db_service.get_or_create_partner_conversation(TEST_RELATIONSHIP_ID)

        # Save a message
        message = db_service.save_partner_message(
            conversation_id=conversation["id"],
            sender_id="partner_b",
            content="Status update test"
        )

        # Update status
        success = db_service.update_message_status(
            message_id=message["id"],
            status="read",
            timestamp_field="read_at"
        )

        assert success == True
        print("✅ DB service updates message status correctly")


def run_all_tests():
    """Run all tests and print summary"""
    print("\n" + "="*60)
    print("🧪 PARTNER MESSAGING PHASE 1 TESTS")
    print("="*60 + "\n")

    test_classes = [
        TestConversationEndpoints,
        TestMessageEndpoints,
        TestMessageStatusEndpoints,
        TestPreferencesEndpoints,
        TestWebSocketBasic,
        TestDatabaseIntegration,
    ]

    passed = 0
    failed = 0

    for test_class in test_classes:
        print(f"\n📋 {test_class.__name__}")
        print("-" * 40)

        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    getattr(instance, method_name)()
                    passed += 1
                except Exception as e:
                    print(f"❌ {method_name}: {e}")
                    failed += 1

    print("\n" + "="*60)
    print(f"📊 RESULTS: {passed} passed, {failed} failed")
    print("="*60 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
