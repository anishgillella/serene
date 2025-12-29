"""
Partner Messaging WebSocket

Real-time message delivery between partners.
Supports demo mode where partner_b is simulated by an LLM.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Optional
import json
import logging
import asyncio

from app.services.db_service import db_service
from app.services.demo_partner_service import demo_partner_service

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_partner_preference(
    relationship_id: str,
    partner_id: str,
    pref_key: str
) -> bool:
    """Get a specific preference for a partner. Returns True if not found (default behavior)."""
    try:
        prefs = await asyncio.to_thread(
            db_service.get_messaging_preferences, relationship_id, partner_id
        )
        return prefs.get(pref_key, True)
    except Exception as e:
        logger.error(f"Error getting preference {pref_key}: {e}")
        return True  # Default to True on error


class ConnectionManager:
    """Manages WebSocket connections for partner messaging."""

    def __init__(self):
        # {conversation_id: {partner_id: websocket}}
        self.connections: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        conversation_id: str,
        partner_id: str
    ):
        """Accept and store a new connection."""
        await websocket.accept()

        if conversation_id not in self.connections:
            self.connections[conversation_id] = {}

        self.connections[conversation_id][partner_id] = websocket
        logger.info(f"Partner {partner_id} connected to conversation {conversation_id}")

    def disconnect(self, conversation_id: str, partner_id: str):
        """Remove a connection."""
        if conversation_id in self.connections:
            if partner_id in self.connections[conversation_id]:
                del self.connections[conversation_id][partner_id]
                logger.info(f"Partner {partner_id} disconnected from {conversation_id}")

            # Clean up empty conversations
            if not self.connections[conversation_id]:
                del self.connections[conversation_id]

    async def send_to_partner(
        self,
        conversation_id: str,
        recipient_partner_id: str,
        message: dict
    ):
        """Send a message to a specific partner."""
        if conversation_id in self.connections:
            if recipient_partner_id in self.connections[conversation_id]:
                websocket = self.connections[conversation_id][recipient_partner_id]
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to {recipient_partner_id}: {e}")

    def is_partner_connected(self, conversation_id: str, partner_id: str) -> bool:
        """Check if a partner is currently connected."""
        if conversation_id in self.connections:
            return partner_id in self.connections[conversation_id]
        return False

    @staticmethod
    def get_other_partner(partner_id: str) -> str:
        """Get the other partner's ID."""
        return "partner_b" if partner_id == "partner_a" else "partner_a"


# Global connection manager
manager = ConnectionManager()


@router.websocket("/api/realtime/partner-chat")
async def websocket_partner_chat(
    websocket: WebSocket,
    conversation_id: str = Query(...),
    partner_id: str = Query(...)
):
    """
    WebSocket endpoint for real-time partner messaging.

    Connect with: ws://host/api/realtime/partner-chat?conversation_id=xxx&partner_id=partner_a

    Client -> Server messages:
    - {"type": "message", "content": "Hello"}
    - {"type": "typing", "is_typing": true}
    - {"type": "read", "message_id": "xxx"}

    Server -> Client messages:
    - {"type": "new_message", "message": {...}}
    - {"type": "message_sent", "message": {...}}
    - {"type": "typing", "partner_id": "partner_b", "is_typing": true}
    - {"type": "read_receipt", "message_id": "xxx", "read_by": "partner_b"}
    - {"type": "delivered", "message_id": "xxx"}
    - {"type": "error", "message": "..."}
    """
    # Look up relationship_id for preference checks
    conversation = db_service.get_conversation_by_id(conversation_id)
    if not conversation:
        await websocket.close(code=4004, reason="Conversation not found")
        return
    relationship_id = conversation["relationship_id"]

    await manager.connect(websocket, conversation_id, partner_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "message":
                # Save message to database
                content = data.get("content", "").strip()
                if not content:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Message content cannot be empty"
                    })
                    continue

                try:
                    # Run DB save in thread pool to avoid blocking
                    message = await asyncio.to_thread(
                        db_service.save_partner_message,
                        conversation_id=conversation_id,
                        sender_id=partner_id,
                        content=content
                    )

                    # Send confirmation to sender
                    await websocket.send_json({
                        "type": "message_sent",
                        "message": message
                    })

                    # Send to recipient
                    other_partner = manager.get_other_partner(partner_id)
                    await manager.send_to_partner(
                        conversation_id,
                        other_partner,
                        {
                            "type": "new_message",
                            "message": message
                        }
                    )

                    # If recipient is connected, mark as delivered (non-blocking)
                    if manager.is_partner_connected(conversation_id, other_partner):
                        asyncio.create_task(asyncio.to_thread(
                            db_service.update_message_status,
                            message["id"],
                            "delivered",
                            "delivered_at"
                        ))
                        await websocket.send_json({
                            "type": "delivered",
                            "message_id": message["id"]
                        })

                    # Check if demo mode is enabled (partner_a is chatting)
                    # If so, generate an LLM response as partner_b
                    if partner_id == "partner_a" and demo_partner_service:
                        demo_mode_enabled = await get_partner_preference(
                            relationship_id, "partner_a", "demo_mode_enabled"
                        )
                        if demo_mode_enabled:
                            # Trigger LLM response generation in background
                            asyncio.create_task(
                                generate_demo_response(
                                    websocket=websocket,
                                    relationship_id=relationship_id,
                                    conversation_id=conversation_id,
                                    user_message=content
                                )
                            )

                except Exception as e:
                    logger.error(f"Error saving message: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Failed to send message"
                    })

            elif msg_type == "typing":
                # Broadcast typing indicator to other partner
                # Only broadcast if the typing partner has show_typing_indicators enabled
                # (i.e., they allow their typing status to be shared)
                if await get_partner_preference(relationship_id, partner_id, "show_typing_indicators"):
                    is_typing = data.get("is_typing", False)
                    other_partner = manager.get_other_partner(partner_id)
                    await manager.send_to_partner(
                        conversation_id,
                        other_partner,
                        {
                            "type": "typing",
                            "partner_id": partner_id,
                            "is_typing": is_typing
                        }
                    )

            elif msg_type == "read":
                # Mark message as read (non-blocking)
                message_id = data.get("message_id")
                if message_id:
                    asyncio.create_task(asyncio.to_thread(
                        db_service.update_message_status,
                        message_id,
                        "read",
                        "read_at"
                    ))

                    # Notify sender their message was read
                    # Only send read receipt if the reading partner has show_read_receipts enabled
                    # (i.e., they allow their read status to be shared)
                    if await get_partner_preference(relationship_id, partner_id, "show_read_receipts"):
                        other_partner = manager.get_other_partner(partner_id)
                        await manager.send_to_partner(
                            conversation_id,
                            other_partner,
                            {
                                "type": "read_receipt",
                                "message_id": message_id,
                                "read_by": partner_id
                            }
                        )

            elif msg_type == "ping":
                # Keep-alive ping
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(conversation_id, partner_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(conversation_id, partner_id)


async def generate_demo_response(
    websocket: WebSocket,
    relationship_id: str,
    conversation_id: str,
    user_message: str
):
    """
    Generate an LLM response as partner_b in demo mode.
    This runs asynchronously after the user's message is sent.
    """
    try:
        # Send typing indicator immediately (no artificial delay)
        await websocket.send_json({
            "type": "typing",
            "partner_id": "partner_b",
            "is_typing": True
        })

        # Fetch chat history and profiles in parallel for speed
        import asyncio as aio
        from app.services.profile_service import profile_service

        # Run profile fetches concurrently
        profile_a_task = profile_service.get_full_partner_profile(relationship_id, "partner_a")
        profile_b_task = profile_service.get_full_partner_profile(relationship_id, "partner_b")
        messages_task = aio.to_thread(db_service.get_partner_messages, conversation_id, 20)

        profile_a, profile_b, messages = await aio.gather(
            profile_a_task, profile_b_task, messages_task,
            return_exceptions=True
        )

        # Handle any exceptions from gather
        if isinstance(profile_a, Exception):
            logger.warning(f"Could not fetch partner_a profile: {profile_a}")
            profile_a = None
        if isinstance(profile_b, Exception):
            logger.warning(f"Could not fetch partner_b profile: {profile_b}")
            profile_b = None
        if isinstance(messages, Exception):
            logger.warning(f"Could not fetch messages: {messages}")
            messages = []

        partner_a_name = profile_a.get("name", "Partner A") if profile_a else "Partner A"
        partner_b_name = profile_b.get("name", "Partner B") if profile_b else "Partner B"

        # Generate LLM response - pass the profile to avoid duplicate fetch
        response_text = await demo_partner_service.generate_partner_response(
            relationship_id=relationship_id,
            conversation_id=conversation_id,
            user_message=user_message,
            chat_history=messages,
            partner_a_name=partner_a_name,
            partner_b_name=partner_b_name,
            partner_b_profile=profile_b  # Pass pre-fetched profile
        )

        # Clear typing indicator
        await websocket.send_json({
            "type": "typing",
            "partner_id": "partner_b",
            "is_typing": False
        })

        if response_text:
            # Save the LLM response as a partner_b message
            demo_message = db_service.save_partner_message(
                conversation_id=conversation_id,
                sender_id="partner_b",
                content=response_text
            )

            # Send the message to partner_a (the user)
            await websocket.send_json({
                "type": "new_message",
                "message": demo_message
            })

            logger.info(f"✅ Demo partner response sent: {response_text[:50]}...")
        else:
            logger.warning("Demo partner service returned no response")

    except Exception as e:
        logger.error(f"❌ Error generating demo response: {e}")
        # Clear typing indicator on error
        try:
            await websocket.send_json({
                "type": "typing",
                "partner_id": "partner_b",
                "is_typing": False
            })
        except:
            pass
