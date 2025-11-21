"""Twilio integration for handling incoming/outbound phone calls."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)

# Twilio configuration
TWILIO_SID = os.environ.get("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "+19786437767")
CALLING_PHONE_NUMBER = os.environ.get("CALLING_PHONE_NUMBER", "+14698674545")

# Initialize Twilio client (lazy - only if credentials are present)
twilio_client = None
if TWILIO_SID and TWILIO_AUTH_TOKEN:
    from twilio.rest import Client
    from twilio.twiml.voice_response import VoiceResponse
    twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
else:
    logger.warning("Twilio credentials not found in environment")


class TwilioCallManager:
    """Manages incoming and outgoing calls via Twilio."""

    def __init__(self):
        self.client = twilio_client
        self.call_sessions: dict[str, dict] = {}

    def handle_incoming_call(self, twilio_request: dict) -> dict:
        """Handle incoming call from Twilio."""
        call_sid = twilio_request.get("CallSid")
        from_number = twilio_request.get("From")
        to_number = twilio_request.get("To")
        
        logger.info(f"Incoming call: {call_sid} from {from_number} to {to_number}")
        
        # Store call session info
        self.call_sessions[call_sid] = {
            "from": from_number,
            "to": to_number,
            "direction": "inbound",
            "status": "active",
            "transcript": [],
        }
        
        # Return TwiML to connect to media stream
        response = VoiceResponse()
        response.say("Hello! I am Serene. I am listening.")
        connect = response.connect()
        stream = connect.stream(url=f"wss://{os.environ.get('BACKEND_HOST', 'localhost')}/media-stream")
        
        # Add parameters if needed
        # stream.parameter(name="callSid", value=call_sid)
        
        return str(response)

    def make_call(self, to_number: str) -> str:
        """Initiate an outbound call to the user.
        
        Args:
            to_number: The number to call (e.g., +14698674545)
            
        Returns:
            Call SID (call identifier)
        """
        if not self.client:
            raise RuntimeError("Twilio client not initialized")
            
        # URL that Twilio will webhook to when the call connects
        # This should point to our /twilio/incoming endpoint
        # Since we are local, we need the public URL (ngrok)
        base_url = os.environ.get("BACKEND_URL") or f"https://{os.environ.get('BACKEND_HOST')}"
        webhook_url = f"{base_url}/twilio/incoming"
        
        logger.info(f"Making outbound call FROM {TWILIO_PHONE_NUMBER} TO {to_number}")
        
        call = self.client.calls.create(
            to=to_number,
            from_=TWILIO_PHONE_NUMBER,
            url=webhook_url
        )
        
        # Store call session info
        self.call_sessions[call.sid] = {
            "from": TWILIO_PHONE_NUMBER,
            "to": to_number,
            "direction": "outbound",
            "status": "initiated",
            "transcript": [],
        }
        
        logger.info(f"✅ Initiated outbound call: {call.sid}")
        return call.sid

    def get_call_transcript(self, call_sid: str) -> list[dict]:
        """Get transcript for a completed call."""
        if call_sid in self.call_sessions:
            return self.call_sessions[call_sid].get("transcript", [])
        return []


# Global instance
twilio_manager = TwilioCallManager()

