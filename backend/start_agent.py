#!/usr/bin/env python3
"""
Agent startup script for LiveKit Cloud deployment
"""
from livekit.agents import cli
from app.agents.heartsync_agent import entrypoint
from livekit.agents import WorkerOptions

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

