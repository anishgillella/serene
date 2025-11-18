"""Flask API server for Twilio webhooks and Serene backend."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from flask import Flask, request, jsonify
from dotenv import load_dotenv

from .twilio_handler import twilio_manager
from .serene_agent import serene, get_serene_response
from .tts_handler import speak

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration
TWILIO_CALLBACK_URL = os.environ.get(
    "TWILIO_CALLBACK_URL",
    "http://localhost:8000"
)
BACKEND_HOST = os.environ.get("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", 8000))


@app.route("/health", methods=["GET"])
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "Serene Voice Agent"}


@app.route("/twilio/incoming", methods=["POST"])
def handle_incoming_call() -> str:
    """Handle incoming call from Twilio.
    
    Twilio will POST call metadata here.
    We respond with TwiML to tell Twilio what to do.
    
    Returns:
        TwiML XML string
    """
    try:
        twilio_request = request.form.to_dict()
        logger.info(f"Incoming call request: {twilio_request}")
        
        # Generate TwiML response
        twiml_response = twilio_manager.handle_incoming_call(twilio_request)
        
        return twiml_response, 200, {"Content-Type": "application/xml"}
        
    except Exception as e:
        logger.error(f"Error handling incoming call: {e}")
        return '<?xml version="1.0" encoding="UTF-8"?><Response><Say>Error processing call</Say></Response>', 500


@app.route("/twilio/gather-speech", methods=["POST"])
def handle_speech_input() -> str:
    """Handle user speech input from Twilio gather.
    
    After user speaks, Twilio sends the transcription here.
    We generate Serene's response and return it.
    
    Returns:
        TwiML XML with Serene's response
    """
    try:
        twilio_request = request.form.to_dict()
        logger.info(f"Speech input: {twilio_request}")
        
        call_sid = twilio_request.get("CallSid")
        speech_result = twilio_request.get("SpeechResult", "")
        
        # Reset Serene's conversation for this call if it's the first message
        if call_sid not in twilio_manager.call_sessions:
            serene.reset_conversation()
        
        # Get Serene's response (async function, so we need to run it)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        serene_response = loop.run_until_complete(get_serene_response(speech_result))
        loop.close()
        
        logger.info(f"Serene response: {serene_response}")
        
        # Acknowledge to Twilio
        return twilio_manager.handle_speech_input(twilio_request), 200, {"Content-Type": "application/xml"}
        
    except Exception as e:
        logger.error(f"Error handling speech input: {e}")
        return '<?xml version="1.0" encoding="UTF-8"?><Response><Say>Error processing your message</Say></Response>', 500


@app.route("/serene/respond", methods=["POST"])
def get_response() -> dict[str, Any]:
    """Get Serene's response to a message (for testing/integration).
    
    POST JSON:
        {
            "message": "I don't understand why she got upset",
            "call_sid": "CA..." (optional)
        }
    
    Returns:
        JSON with Serene's response and audio
    """
    try:
        data = request.get_json()
        user_message = data.get("message", "")
        call_sid = data.get("call_sid")
        
        if not user_message:
            return {"error": "No message provided"}, 400
        
        logger.info(f"Processing message: {user_message}")
        
        # Get Serene's response
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        serene_response = loop.run_until_complete(get_serene_response(user_message))
        loop.close()
        
        logger.info(f"Serene response: {serene_response}")
        
        # Generate speech (TODO: integrate with Twilio for real calls)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        audio_bytes = loop.run_until_complete(speak(serene_response))
        loop.close()
        
        return {
            "call_sid": call_sid,
            "user_message": user_message,
            "serene_response": serene_response,
            "audio_generated": audio_bytes is not None,
        }, 200
        
    except Exception as e:
        logger.error(f"Error getting response: {e}")
        return {"error": str(e)}, 500


@app.route("/serene/reset", methods=["POST"])
def reset_conversation() -> dict[str, str]:
    """Reset Serene's conversation history.
    
    Returns:
        Status message
    """
    serene.reset_conversation()
    return {"status": "Conversation reset"}, 200


@app.route("/twilio/call/<call_sid>", methods=["GET"])
def get_call_status(call_sid: str) -> dict[str, Any]:
    """Get status of a call.
    
    Args:
        call_sid: Twilio call SID
        
    Returns:
        Call status and transcript
    """
    if call_sid in twilio_manager.call_sessions:
        session = twilio_manager.call_sessions[call_sid]
        return {
            "call_sid": call_sid,
            "status": session.get("status"),
            "from": session.get("from"),
            "to": session.get("to"),
            "direction": session.get("direction"),
            "transcript": session.get("transcript", []),
        }, 200
    else:
        return {"error": "Call not found"}, 404


@app.route("/twilio/call/<call_sid>", methods=["DELETE"])
def end_call(call_sid: str) -> dict[str, str]:
    """End a call.
    
    Args:
        call_sid: Twilio call SID
        
    Returns:
        Status message
    """
    if twilio_manager.end_call(call_sid):
        return {"status": "Call terminated"}, 200
    else:
        return {"error": "Failed to terminate call"}, 500


def run_server(host: str = BACKEND_HOST, port: int = BACKEND_PORT) -> None:
    """Run the Flask server.
    
    Args:
        host: Host to bind to
        port: Port to listen on
    """
    logger.info(f"Starting Serene API server on {host}:{port}")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    run_server()

