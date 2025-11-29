import logging
import asyncio
from livekit.agents import llm
from app.services.db_service import db_service

logger = logging.getLogger("luna-agent")

class LoggingLLMStream(llm.LLMStream):
    """Wrapper for LLMStream that logs generated text to the database"""
    def __init__(self, wrapped_stream: llm.LLMStream, session_id: str):
        super().__init__(chat_ctx=wrapped_stream.chat_ctx, tools=wrapped_stream.tools)
        self._wrapped_stream = wrapped_stream
        self.session_id = session_id
        self._accumulated_text = ""
        self._logged = False

    async def _run(self):
        async for chunk in self._wrapped_stream:
            if chunk.choices:
                for choice in chunk.choices:
                    if choice.delta.content:
                        content = choice.delta.content
                        self._accumulated_text += content
                        logger.info(f"📝 Yielding chunk: {content[:20]}...") 
            yield chunk
            
        # Stream finished, log the message
        if not self._logged and self._accumulated_text.strip() and db_service:
            self._logged = True
            asyncio.create_task(self._log_message())

    async def aclose(self) -> None:
        # If closed (e.g. interrupted), log what we have so far
        if not self._logged and self._accumulated_text.strip() and db_service:
            self._logged = True
            asyncio.create_task(self._log_message())
        
        await self._wrapped_stream.aclose()
        
    async def _log_message(self):
        try:
            await asyncio.to_thread(
                db_service.save_mediator_message,
                session_id=self.session_id,
                role="assistant",
                content=self._accumulated_text
            )
        except Exception as e:
            logger.error(f"Error logging assistant message: {e}")
