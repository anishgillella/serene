#!/usr/bin/env python3
"""
Simplified agent - directly use mediator agent as main entrypoint
Testing if the issue is with routing vs. the agent itself
"""
import os
import logging
from livekit.agents import cli, WorkerOptions
from app.agents.mediator_agent import mediator_entrypoint

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("simple-agent")

if __name__ == "__main__":
    logger.info("🚀 Starting Simple Mediator Agent (NO ROUTING)...")
    logger.info("This will handle ALL rooms as mediator rooms")
    
    # Use mediator directly without routing
    cli.run_app(WorkerOptions(entrypoint_fnc=mediator_entrypoint, agent_name="Luna"))
