#!/usr/bin/env python3
"""
Agent startup script - Luna Mediator
Simple and efficient voice-based relationship mediator
Uses AgentServer pattern like Voice Agent RAG
"""
import logging
from livekit import agents
from app.agents.mediator_agent import mediator_entrypoint

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("agent-startup")

if __name__ == "__main__":
    import sys
    
    logger.info("🚀 Starting Luna Mediator Agent")
    logger.info("📡 Waiting for job requests from LiveKit Cloud")
    logger.info("🎯 Model: gpt-4o-mini | Voice: ElevenLabs | STT: Deepgram")
    logger.info("🔄 Using AgentServer pattern (like Voice Agent RAG)")
    
    # For cloud deployment, LiveKit may call without arguments
    # Add 'start' as default command if no arguments provided
    if len(sys.argv) == 1:
        sys.argv.append("start")
    
    # Use AgentServer pattern - EXACTLY like Voice Agent RAG
    # Pass the entrypoint function (decorated with @server.rtc_session())
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=mediator_entrypoint))
