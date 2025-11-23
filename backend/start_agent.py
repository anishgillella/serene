#!/usr/bin/env python3
"""
Agent startup script for LiveKit Cloud deployment
"""
from livekit.agents import cli, JobContext
from app.agents.heartsync_agent import entrypoint as heartsync_entrypoint
from livekit.agents import WorkerOptions

async def router_entrypoint(ctx: JobContext):
    """Route to Fight Capture agent"""
    room_name = ctx.room.name
    import logging
    import sys
    logger = logging.getLogger("agent-router")
    
    logger.info(f"🔵 Router called for room: {room_name}")
    
    try:
        # All rooms use Fight Capture agent
        await heartsync_entrypoint(ctx)
    except Exception as e:
        logger.error(f"❌ Error in router_entrypoint: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=router_entrypoint))

