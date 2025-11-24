#!/usr/bin/env python3
"""
Debug version of agent startup with verbose logging
"""
import logging
import sys
import os

# Maximum verbosity
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from livekit.agents import cli, JobContext
from app.agents.mediator_agent import mediator_entrypoint

logger = logging.getLogger("agent-router-debug")

async def router_entrypoint(ctx: JobContext):
    """Route to appropriate agent based on room name"""
    room_name = ctx.room.name
    
    logger.error("=" * 100)
    logger.error("🔴 ========== JOB RECEIVED FROM LIVEKIT ==========")
    logger.error("=" * 100)
    logger.error(f"🎯 Room Name: {room_name}")
    logger.error(f"📋 Room ID: {ctx.room.sid}")
    logger.error(f"🆔 Job ID: {ctx.job.id}")
    logger.error(f"👥 Participants: {len(ctx.room.remote_participants)}")
    logger.error(f"🔀 Mediator room? {room_name.startswith('mediator-')}")
    logger.error("=" * 100)
    
    try:
        if room_name.startswith("mediator-"):
            logger.error(f"✅ Routing to Mediator Agent")
            await mediator_entrypoint(ctx)
        else:
            logger.error(f"✅ Routing to Default Agent")
            logger.error(f"❌ But we only support mediator- rooms right now!")
    except Exception as e:
        logger.error(f"❌ Error in router: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    logger.error("🚀 Starting DEBUG agent router...")
    logger.error("📡 Waiting for job requests...")
    
    from livekit.agents import WorkerOptions
    cli.run_app(WorkerOptions(entrypoint_fnc=router_entrypoint, agent_name="Luna"))
