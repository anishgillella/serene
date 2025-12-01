#!/usr/bin/env python3
"""
Agent startup script - Luna Mediator
Simple and efficient voice-based relationship mediator
Uses AgentServer pattern like Voice Agent RAG
"""
import logging
from livekit import agents
from app.agents.luna import mediator_entrypoint

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("agent-startup")

if __name__ == "__main__":
    import sys
    
    logger.info("🚀 Starting Luna Mediator Agent (Modular)")
    logger.info("📡 Waiting for job requests from LiveKit Cloud")
    
    if len(sys.argv) == 1:
        sys.argv.append("start")
    
    agents.cli.run_app(agents.WorkerOptions(
        entrypoint_fnc=mediator_entrypoint,
        num_idle_processes=1,    # Only keep 1 idle process ready (saves memory)
        job_memory_warn_mb=1024, # Increase warning threshold to 1GB
        initialization_timeout=15.0, # Give more time for VAD/model loading
    ))
