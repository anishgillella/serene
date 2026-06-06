import logging
import uuid

from livekit.agents import llm

from app.services.moss_service import moss_service

logger = logging.getLogger("luna-moss-tools")


def get_moss_tools(
    relationship_id: str | None = None,
    conflict_id: str | None = None,
    room=None,
):
    if not moss_service.enabled:
        return []

    rel_id = relationship_id or ""
    conflict = conflict_id or ""

    @llm.function_tool(
        description="Search past conflict transcripts and relationship context for relevant history. "
        "Call when the user asks about patterns, past fights, or what happened before."
    )
    async def search_transcripts(query: str) -> str:
        metadata_filter = None
        if rel_id:
            metadata_filter = {
                "field": "relationship_id",
                "condition": {"$eq": rel_id},
            }
        result = await moss_service.query(
            moss_service.transcripts_index,
            query,
            top_k=3,
            metadata_filter=metadata_filter,
        )
        await moss_service.publish_context(room, query, result)
        return moss_service.format_query_result(result)

    @llm.function_tool(
        description="Search Gottman-method and repair knowledge for communication guidance. "
        "Call when the user needs advice on how to repair, apologize, or communicate better."
    )
    async def search_knowledge(query: str) -> str:
        result = await moss_service.query(
            moss_service.knowledge_index,
            query,
            top_k=3,
        )
        await moss_service.publish_context(room, query, result)
        return moss_service.format_query_result(result)

    @llm.function_tool(
        description="Remember a durable fact about this relationship or user preference "
        "(e.g. triggers, love languages, communication style)."
    )
    async def remember_fact(fact: str) -> str:
        if not rel_id:
            return "Cannot remember facts without a relationship context."
        doc_id = f"{rel_id}-{uuid.uuid4()}"
        ok = await moss_service.add_memory_doc(
            doc_id=doc_id,
            text=fact,
            metadata={"relationship_id": rel_id, "conflict_id": conflict},
        )
        return "Got it, I'll remember that." if ok else "I couldn't save that right now."

    @llm.function_tool(
        description="Recall facts previously shared about this relationship. "
        "Call before answering questions that depend on past context."
    )
    async def recall_facts(query: str) -> str:
        if not rel_id:
            return "No relationship context available to recall from."
        result = await moss_service.query(
            moss_service.memory_index,
            query,
            top_k=5,
            metadata_filter={
                "field": "relationship_id",
                "condition": {"$eq": rel_id},
            },
        )
        await moss_service.publish_context(room, query, result)
        return moss_service.format_query_result(result)

    logger.info("Moss tools registered for relationship=%s conflict=%s", rel_id, conflict)
    return [search_transcripts, search_knowledge, remember_fact, recall_facts]
