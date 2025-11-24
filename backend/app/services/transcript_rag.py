"""RAG system for retrieving relevant transcript chunks from Pinecone."""
import logging
from typing import Optional, List, Dict, Any
from app.services.pinecone_service import pinecone_service
from app.services.embeddings_service import embeddings_service

logger = logging.getLogger(__name__)


class TranscriptRAGSystem:
    """Retrieval-Augmented Generation system for conversation transcripts."""
    
    def __init__(
        self,
        k: int = 5,
    ):
        """
        Initialize transcript RAG system.
        
        Args:
            k: Number of chunks to retrieve
        """
        self.k = k
        logger.info(f"Initialized TranscriptRAGSystem with k={k}")
    
    def rag_lookup(
        self,
        query: str,
        conflict_id: Optional[str] = None,
        relationship_id: Optional[str] = None,
    ) -> str:
        """
        Perform RAG lookup and return formatted context.
        
        Args:
            query: User query string
            conflict_id: Current conflict ID (priority filter)
            relationship_id: Relationship ID (fallback filter)
            
        Returns:
            Formatted context string for LLM injection
        """
        try:
            # Generate query embedding
            query_embedding = embeddings_service.embed_query(query)
            
            # Primary: Query current conflict chunks
            chunks = []
            if conflict_id:
                logger.info(f"Querying transcript chunks for conflict {conflict_id}")
                results = pinecone_service.query_transcript_chunks(
                    query_embedding=query_embedding,
                    conflict_id=conflict_id,
                    top_k=self.k,
                )
                
                if results and hasattr(results, 'matches') and results.matches:
                    chunks = results.matches
                    logger.info(f"Found {len(chunks)} chunks for conflict {conflict_id}")
            
            # Fallback: Query relationship-level chunks if insufficient results
            if len(chunks) < self.k and relationship_id:
                logger.info(f"Querying relationship-level chunks for relationship {relationship_id}")
                fallback_results = pinecone_service.query_transcript_chunks(
                    query_embedding=query_embedding,
                    relationship_id=relationship_id,
                    top_k=self.k - len(chunks),
                )
                
                if fallback_results and hasattr(fallback_results, 'matches') and fallback_results.matches:
                    # Avoid duplicates
                    existing_conflict_ids = {chunk.metadata.get("conflict_id") for chunk in chunks if hasattr(chunk, 'metadata')}
                    for match in fallback_results.matches:
                        if hasattr(match, 'metadata') and match.metadata.get("conflict_id") not in existing_conflict_ids:
                            chunks.append(match)
                    logger.info(f"Added {len(fallback_results.matches)} relationship-level chunks")
            
            if not chunks:
                logger.warning(f"No relevant transcript chunks found for query: {query[:50]}...")
                return "No relevant information found in the conversation transcript."
            
            # Format retrieved chunks into context
            context_parts = []
            for idx, chunk in enumerate(chunks[:self.k], 1):
                metadata = chunk.metadata if hasattr(chunk, 'metadata') else {}
                speaker = metadata.get("speaker", "Unknown")
                text = metadata.get("text", "")
                chunk_idx = metadata.get("chunk_index", "?")
                conflict_id_chunk = metadata.get("conflict_id", "unknown")
                
                context_parts.append(
                    f"[Chunk {idx} from conflict {conflict_id_chunk}, chunk {chunk_idx}, {speaker}]:\n{text}\n"
                )
            
            context = "\n".join(context_parts)
            
            logger.info(f"Retrieved {len(chunks)} transcript chunks for query: {query[:50]}...")
            return context
            
        except Exception as e:
            logger.error(f"Error in transcript RAG lookup: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return "Error retrieving information from the conversation transcript."
    
    def format_context_for_llm(self, context: str) -> str:
        """
        Format context for injection into LLM chat context.
        
        Args:
            context: Raw context string
            
        Returns:
            Formatted context string
        """
        return f"""Additional information relevant to the user's question from the conversation transcript:

{context}

Use this information to provide accurate and detailed answers about what was said in the conversation. Reference specific speakers and their statements when relevant. If the information doesn't directly answer the question, say so and provide what information is available."""

