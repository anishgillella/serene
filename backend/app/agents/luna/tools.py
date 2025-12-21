import logging
from livekit.agents import llm
from app.agents.tools.mediator_tools import MediatorTools

logger = logging.getLogger("luna-tools")


def get_tools(conflict_id: str = None, relationship_id: str = None, partner_b_name: str = "Partner"):
    """
    Initialize and return the list of tools for the agent.

    Args:
        conflict_id: Current conflict ID
        relationship_id: Relationship ID for profile filtering
        partner_b_name: Name of partner B (for dynamic tool descriptions)
    """
    tool_list = []

    if MediatorTools:
        logger.info("Initializing MediatorTools...")
        tools_instance = MediatorTools(conflict_id=conflict_id, relationship_id=relationship_id)

        # Create wrapper functions to avoid AttributeError on bound methods
        @llm.function_tool(description="Find similar past conflicts to see patterns. Returns a summary of what happened before.")
        async def find_similar_conflicts(topic_keywords: str) -> str:
            return await tools_instance.find_similar_conflicts(topic_keywords)

        @llm.function_tool(description=f"Get {partner_b_name}'s likely perspective on the current situation based on their profile.")
        async def get_partner_perspective(situation_description: str) -> str:
            return await tools_instance.get_partner_perspective(situation_description)

        tool_list = [find_similar_conflicts, get_partner_perspective]
        logger.info(f"   Tools registered: find_similar_conflicts, get_partner_perspective")

    return tool_list
