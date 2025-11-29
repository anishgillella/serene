import logging
import time
import asyncio
from livekit.agents import llm
from app.services.db_service import db_service

logger = logging.getLogger("luna-rag")

class RAGHandler:
    """Handles RAG lookups and context injection"""
    
    def __init__(self, rag_system, conflict_id, relationship_id, session_id):
        self.rag_system = rag_system
        self.conflict_id = conflict_id
        self.relationship_id = relationship_id
        self.session_id = session_id

    async def handle_user_turn(self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage):
        """
        Hook called when user completes a turn.
        Performs RAG lookup and injects context into chat context.
        """
        try:
            # Extract user's query
            user_query = self._extract_text(new_message)
            
            if not user_query or not user_query.strip():
                logger.warning("Empty user query, skipping RAG lookup")
                return
            
            # Log user message
            if self.session_id and db_service:
                self._log_user_message(user_query)

            logger.info(f"User query: {user_query}")
            
            turn_start = time.perf_counter()
            
            # Perform RAG lookup (ASYNC)
            rag_context = await self.rag_system.rag_lookup(
                query=user_query,
                conflict_id=self.conflict_id,
                relationship_id=self.relationship_id,
            )
            
            rag_time = time.perf_counter() - turn_start
            logger.info(f"⏱️ RAG Lookup Complete: {rag_time:.3f}s")
            
            # Format context for LLM
            formatted_context = self.rag_system.format_context_for_llm(rag_context)
            
            # Inject context into chat context before LLM generates response
            turn_ctx.add_message(
                role="assistant",
                content=formatted_context,
            )
            
            logger.info("RAG context injected into chat context")
            
        except Exception as e:
            logger.error(f"Error in on_user_turn_completed: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _extract_text(self, message):
        if hasattr(message, 'text_content'):
            try:
                return message.text_content()
            except TypeError:
                return message.text_content
        elif hasattr(message, 'content'):
            return str(message.content)
        return ""

    def _log_user_message(self, content):
        try:
            asyncio.create_task(asyncio.to_thread(
                db_service.save_mediator_message,
                session_id=self.session_id,
                role="user",
                content=content
            ))
        except Exception as e:
            logger.error(f"Error logging user message: {e}")
