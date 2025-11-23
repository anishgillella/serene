"""
Voyage AI embeddings service for generating 1024-dimensional vectors
"""
import logging
import time
from voyageai import Client as VoyageClient
from voyageai.error import RateLimitError
from typing import List
from app.config import settings

logger = logging.getLogger(__name__)

class EmbeddingsService:
    """Service for generating embeddings using Voyage AI"""
    
    def __init__(self):
        self.client = VoyageClient(api_key=settings.VOYAGE_API_KEY)
        self.model = "voyage-3"  # 1024 dimensions
        logger.info("✅ Initialized Voyage embeddings service")
    
    def _embed_with_retry(self, texts: List[str], input_type: str = "document", max_retries: int = 3, initial_delay: float = 1.0):
        """Embed with exponential backoff retry for rate limits"""
        delay = initial_delay
        for attempt in range(max_retries):
            try:
                result = self.client.embed(
                    texts=texts,
                    model=self.model,
                    input_type=input_type
                )
                return result.embeddings
            except RateLimitError as e:
                if attempt < max_retries - 1:
                    wait_time = delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"⚠️ Rate limit hit (attempt {attempt + 1}/{max_retries}). Waiting {wait_time:.1f}s before retry...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Rate limit exceeded after {max_retries} attempts: {e}")
                    raise
            except Exception as e:
                logger.error(f"❌ Error generating embedding: {e}")
                raise
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        try:
            embeddings = self._embed_with_retry([text], input_type="document")
            return embeddings[0]
        except Exception as e:
            logger.error(f"❌ Error generating embedding: {e}")
            raise
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        try:
            return self._embed_with_retry(texts, input_type="document")
        except Exception as e:
            logger.error(f"❌ Error generating batch embeddings: {e}")
            raise
    
    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a query (optimized for search)"""
        try:
            embeddings = self._embed_with_retry([text], input_type="query")
            return embeddings[0]
        except Exception as e:
            logger.error(f"❌ Error generating query embedding: {e}")
            raise

# Singleton instance
embeddings_service = EmbeddingsService()

