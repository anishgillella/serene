"""
Voyage AI embeddings service for generating 1024-dimensional vectors
"""
import logging
from voyageai import Client as VoyageClient
from typing import List
from app.config import settings

logger = logging.getLogger(__name__)

class EmbeddingsService:
    """Service for generating embeddings using Voyage AI"""
    
    def __init__(self):
        self.client = VoyageClient(api_key=settings.VOYAGE_API_KEY)
        self.model = "voyage-3"  # 1024 dimensions
        logger.info("✅ Initialized Voyage embeddings service")
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        try:
            result = self.client.embed(
                texts=[text],
                model=self.model,
                input_type="document"
            )
            return result.embeddings[0]
        except Exception as e:
            logger.error(f"❌ Error generating embedding: {e}")
            raise
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        try:
            result = self.client.embed(
                texts=texts,
                model=self.model,
                input_type="document"
            )
            return result.embeddings
        except Exception as e:
            logger.error(f"❌ Error generating batch embeddings: {e}")
            raise
    
    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a query (optimized for search)"""
        try:
            result = self.client.embed(
                texts=[text],
                model=self.model,
                input_type="query"
            )
            return result.embeddings[0]
        except Exception as e:
            logger.error(f"❌ Error generating query embedding: {e}")
            raise

# Singleton instance
embeddings_service = EmbeddingsService()

