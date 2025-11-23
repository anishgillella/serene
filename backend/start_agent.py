#!/usr/bin/env python3
"""
Agent startup script for LiveKit Cloud deployment
Routes to appropriate agent based on room name
"""
import logging
import sys
from livekit.agents import cli, JobContext
from app.agents.heartsync_agent import entrypoint as heartsync_entrypoint
from app.agents.mediator_agent import mediator_entrypoint
from livekit.agents import WorkerOptions

print("🚀 STARTING AGENT SCRIPT...")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("agent-router")

async def router_entrypoint(ctx: JobContext):
    """Route to appropriate agent based on room name"""
    room_name = ctx.room.name
    
    # Enhanced logging to debug why agent isn't being triggered
    logger.info("=" * 80)
    logger.info(f"🔵 Router called for room: {room_name}")
    logger.info(f"📋 Room ID: {ctx.room.sid}, Job ID: {ctx.job.id}")
    logger.info(f"👥 Participants in room: {len(ctx.room.remote_participants)}")
    logger.info(f"🏷️ Room name pattern check: starts with 'mediator-' = {room_name.startswith('mediator-')}")
    logger.info("=" * 80)
    
    try:
        # Route mediator rooms to mediator agent
        if room_name.startswith("mediator-"):
            logger.info(f"🎙️ Routing to Mediator Agent for room: {room_name}")
            await mediator_entrypoint(ctx)
        else:
            # Default to Fight Capture agent
            logger.info(f"🎤 Routing to Fight Capture Agent for room: {room_name}")
            await heartsync_entrypoint(ctx)
    except Exception as e:
        logger.error(f"❌ Error in router_entrypoint: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    logger.info("🚀 Starting agent server...")
    logger.info("📡 Waiting for job requests from LiveKit Cloud...")
    logger.info("💡 Make sure your agent is configured in LiveKit Cloud dashboard")
    cli.run_app(WorkerOptions(entrypoint_fnc=router_entrypoint, agent_name="Luna"))

