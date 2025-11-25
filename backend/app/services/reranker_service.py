"""
Voyage Reranker service for retrieving relevant information from documents
"""
import logging
from voyageai import Client as VoyageClient
from typing import List, Dict, Any, Tuple
from app.config import settings

logger = logging.getLogger(__name__)

class RerankerService:
    """Service for reranking search results using Voyage Rerank-2"""
    
    def __init__(self):
        self.client = VoyageClient(api_key=settings.VOYAGE_API_KEY)
        self.model = "rerank-2"
        logger.info("✅ Initialized Voyage Reranker service")
    
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 3
    ) -> List[Tuple[str, float]]:
        """
        Rerank documents based on relevance to query
        
        Args:
            query: The search query
            documents: List of document texts to rerank
            top_k: Number of top results to return
            
        Returns:
            List of tuples (document_text, relevance_score) sorted by relevance
        """
        try:
            if not documents:
                return []
            
            result = self.client.rerank(
                query=query,
                documents=documents,
                model=self.model,
                top_k=min(top_k, len(documents))
            )
            
            # Extract results with scores
            reranked = [
                (documents[item.index], item.relevance_score)
                for item in result.results
            ]
            
            logger.info(f"✅ Reranked {len(documents)} documents, returning top {len(reranked)}")
            return reranked
            
        except Exception as e:
            logger.error(f"❌ Error reranking documents: {e}")
            # Fallback: return documents as-is
            return [(doc, 0.0) for doc in documents]

# Singleton instance
reranker_service = RerankerService()








