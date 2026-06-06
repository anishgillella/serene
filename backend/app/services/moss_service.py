import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("moss-service")

try:
    from moss import DocumentInfo, MossClient, QueryOptions
    MOSS_AVAILABLE = True
except ImportError:
    MOSS_AVAILABLE = False
    MossClient = None
    DocumentInfo = None
    QueryOptions = None


class MossService:
    def __init__(self):
        self._client: Optional[Any] = None
        self._indexes_loaded: set[str] = set()
        self._enabled = False

        if not MOSS_AVAILABLE:
            logger.warning("moss package not installed — Moss retrieval disabled")
            return

        project_id = os.getenv("MOSS_PROJECT_ID", "")
        project_key = os.getenv("MOSS_PROJECT_KEY", "")
        if not project_id or not project_key:
            logger.warning("MOSS_PROJECT_ID / MOSS_PROJECT_KEY not set — Moss retrieval disabled")
            return

        self._client = MossClient(project_id, project_key)
        self._enabled = True
        self.transcripts_index = os.getenv("MOSS_TRANSCRIPTS_INDEX", "serene-transcripts")
        self.memory_index = os.getenv("MOSS_MEMORY_INDEX", "serene-memory")
        self.knowledge_index = os.getenv("MOSS_KNOWLEDGE_INDEX", "serene-knowledge")

    @property
    def enabled(self) -> bool:
        return self._enabled and self._client is not None

    async def load_index(self, index_name: str) -> bool:
        if not self.enabled:
            return False
        if index_name in self._indexes_loaded:
            return True
        try:
            await self._client.load_index(index_name)
            self._indexes_loaded.add(index_name)
            logger.info("Loaded Moss index: %s", index_name)
            return True
        except Exception as e:
            logger.error("Failed to load Moss index %s: %s", index_name, e)
            return False

    async def preload_session_indexes(self) -> None:
        if not self.enabled:
            return
        for index_name in (self.transcripts_index, self.memory_index, self.knowledge_index):
            await self.load_index(index_name)

    async def query(
        self,
        index_name: str,
        query: str,
        top_k: int = 3,
        metadata_filter: Optional[dict] = None,
    ):
        if not self.enabled:
            return None
        await self.load_index(index_name)
        options = QueryOptions(top_k=top_k)
        if metadata_filter:
            options.filter = metadata_filter
        return await self._client.query(index_name, query, options)

    async def add_memory_doc(
        self,
        doc_id: str,
        text: str,
        metadata: dict,
    ) -> bool:
        if not self.enabled:
            return False
        await self.load_index(self.memory_index)
        doc = DocumentInfo(
            id=doc_id,
            text=text,
            metadata={str(k): str(v) for k, v in metadata.items()},
        )
        await self._client.add_docs(self.memory_index, [doc])
        await self.load_index(self.memory_index)
        return True

    @staticmethod
    def format_query_result(result) -> str:
        if result is None:
            return "Moss retrieval is not available."
        docs = getattr(result, "docs", None) or []
        snippets = [(getattr(d, "text", "") or "").strip() for d in docs]
        snippets = [s for s in snippets if s]
        if not snippets:
            return "No relevant matches were found."
        return "\n\n".join(snippets)

    @staticmethod
    def build_context_payload(query: str, result) -> dict:
        matches: list[dict] = []
        for doc in getattr(result, "docs", None) or []:
            entry: dict = {"text": (getattr(doc, "text", "") or "").strip()}
            score = getattr(doc, "score", None)
            if score is not None:
                try:
                    entry["score"] = float(score)
                except (TypeError, ValueError):
                    pass
            metadata = getattr(doc, "metadata", None)
            if metadata:
                entry["metadata"] = metadata
            matches.append(entry)

        return {
            "type": "moss_context",
            "data": {
                "query": query,
                "matches": matches,
                "time_taken_ms": getattr(result, "time_taken_ms", None),
                "timestamp": datetime.now(timezone.utc).timestamp(),
            },
        }

    async def publish_context(self, room, query: str, result) -> None:
        if room is None or result is None:
            return
        try:
            payload = self.build_context_payload(query, result)
            encoded = json.dumps(payload, default=str).encode("utf-8")
            await room.local_participant.publish_data(payload=encoded, reliable=True)
        except Exception as e:
            logger.error("Failed to publish moss_context: %s", e)


moss_service = MossService()
