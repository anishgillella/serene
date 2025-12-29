"""
Partner Messaging WebSocket

Real-time message delivery between partners.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict
import json
import logging

from app.services.db_service import db_service

logger = logging.getLogger(__name__)
router = APIRouter()


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
                    message = db_service.save_partner_message(
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

                    # If recipient is connected, mark as delivered
                    if manager.is_partner_connected(conversation_id, other_partner):
                        db_service.update_message_status(
                            message_id=message["id"],
                            status="delivered",
                            timestamp_field="delivered_at"
                        )
                        await websocket.send_json({
                            "type": "delivered",
                            "message_id": message["id"]
                        })
                except Exception as e:
                    logger.error(f"Error saving message: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Failed to send message"
                    })

            elif msg_type == "typing":
                # Broadcast typing indicator to other partner
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
                # Mark message as read
                message_id = data.get("message_id")
                if message_id:
                    db_service.update_message_status(
                        message_id=message_id,
                        status="read",
                        timestamp_field="read_at"
                    )

                    # Notify sender their message was read
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
