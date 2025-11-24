"""RAG system for retrieving relevant transcript chunks and profile PDFs from Pinecone."""
import logging
from typing import Optional, List, Dict, Any
from app.services.pinecone_service import pinecone_service
from app.services.embeddings_service import embeddings_service
from app.services.reranker_service import reranker_service

logger = logging.getLogger(__name__)


class TranscriptRAGSystem:
    """Retrieval-Augmented Generation system for conversation transcripts and profile PDFs."""
    
    def __init__(
        self,
        k: int = 10,  # Increased default to get more context from entire corpus
        include_profiles: bool = True,
    ):
        """
        Initialize transcript RAG system.
        
        Args:
            k: Number of chunks to retrieve from entire corpus
            include_profiles: Whether to also query profile PDFs (Adrian/Elara profiles)
        """
        self.k = k
        self.include_profiles = include_profiles
        logger.info(f"Initialized TranscriptRAGSystem with k={k}, include_profiles={include_profiles}")
    
    def rag_lookup(
        self,
        query: str,
        conflict_id: Optional[str] = None,
        relationship_id: Optional[str] = None,
    ) -> str:
        """
        Perform RAG lookup across ENTIRE corpus (all transcripts + profiles).
        Returns top relevant chunks from entire corpus for contextualized responses.
        
        Args:
            query: User query string
            conflict_id: Current conflict ID (for prioritization, not filtering)
            relationship_id: Relationship ID (for profile filtering)
            
        Returns:
            Formatted context string for LLM injection
        """
        try:
            # Generate query embedding
            query_embedding = embeddings_service.embed_query(query)
            
            # Query ENTIRE corpus - get candidate chunks from ALL sources (transcripts + profiles)
            # Then rerank ALL together to get most relevant ones (saves tokens, better context)
            logger.info(f"Querying ENTIRE corpus (transcripts + profiles) for query: {query[:50]}...")
            
            # Step 1: Query transcript chunks from entire corpus (no filter)
            candidate_top_k = 30  # Get 30 candidate chunks from transcripts
            transcript_candidates = []
            transcript_results = pinecone_service.index.query(
                vector=query_embedding,
                top_k=candidate_top_k,
                namespace="transcript_chunks",
                include_metadata=True,
                # No filter - query entire corpus
            )
            
            if transcript_results and hasattr(transcript_results, 'matches') and transcript_results.matches:
                for match in transcript_results.matches:
                    metadata = match.metadata if hasattr(match, 'metadata') else {}
                    text = metadata.get("text", "")
                    if text:
                        transcript_candidates.append({
                            'text': text,
                            'match': match,
                            'type': 'transcript',
                            'conflict_id': metadata.get("conflict_id", ""),
                            'speaker': metadata.get("speaker", "Unknown"),
                        })
                logger.info(f"Found {len(transcript_candidates)} transcript candidate chunks")
            
            # Step 2: Query profile chunks from entire corpus (no filter)
            profile_candidates = []
            if self.include_profiles and relationship_id:
                try:
                    # Query boyfriend profile chunks
                    bf_results = pinecone_service.query(
                        query_embedding=query_embedding,
                        top_k=15,  # Get candidate chunks
                        namespace="profiles",
                        filter={
                            "relationship_id": {"$eq": relationship_id},
                            "pdf_type": {"$eq": "boyfriend_profile"}
                        }
                    )
                    
                    # Query girlfriend profile chunks
                    gf_results = pinecone_service.query(
                        query_embedding=query_embedding,
                        top_k=15,  # Get candidate chunks
                        namespace="profiles",
                        filter={
                            "relationship_id": {"$eq": relationship_id},
                            "pdf_type": {"$eq": "girlfriend_profile"}
                        }
                    )
                    
                    if bf_results and bf_results.matches:
                        for match in bf_results.matches:
                            text = match.metadata.get("extracted_text", "") if hasattr(match, 'metadata') else ""
                            if text:
                                profile_candidates.append({
                                    'text': text,
                                    'match': match,
                                    'type': 'profile',
                                    'profile_type': 'boyfriend',
                                    'speaker': 'Adrian',
                                })
                    
                    if gf_results and gf_results.matches:
                        for match in gf_results.matches:
                            text = match.metadata.get("extracted_text", "") if hasattr(match, 'metadata') else ""
                            if text:
                                profile_candidates.append({
                                    'text': text,
                                    'match': match,
                                    'type': 'profile',
                                    'profile_type': 'girlfriend',
                                    'speaker': 'Elara',
                                })
                    
                    logger.info(f"Found {len(profile_candidates)} profile candidate chunks")
                except Exception as e:
                    logger.warning(f"Error querying profiles for reranking (non-fatal): {e}")
            
            # Step 3: Combine ALL candidates (transcripts + profiles)
            all_candidates = transcript_candidates + profile_candidates
            logger.info(f"Total candidates: {len(all_candidates)} ({len(transcript_candidates)} transcripts + {len(profile_candidates)} profiles)")
            
            # Step 4: Rerank ALL candidates together to get most relevant ones
            chunks = []
            if all_candidates:
                logger.info(f"Reranking {len(all_candidates)} candidate chunks (transcripts + profiles) to get top {self.k} most relevant...")
                candidate_texts = [c['text'] for c in all_candidates]
                reranked_results = reranker_service.rerank(
                    query=query,
                    documents=candidate_texts,
                    top_k=self.k  # Get top_k most relevant after reranking
                )
                
                # Map reranked results back to original chunks
                reranked_chunks = []
                for doc_text, score in reranked_results:
                    # Find the original candidate that matches this text
                    for candidate in all_candidates:
                        if candidate['text'] == doc_text:
                            reranked_chunks.append(candidate['match'])
                            break
                
                chunks = reranked_chunks
                logger.info(f"✅ Reranked to {len(chunks)} most relevant chunks from entire corpus (transcripts + profiles)")
            
            # Format reranked chunks into context (mix of transcripts and profiles)
            if not chunks:
                logger.warning(f"No relevant chunks found for query: {query[:50]}...")
                return "No relevant information found in the conversation transcript or profiles."
            
            context_parts = []
            for idx, chunk in enumerate(chunks, 1):
                metadata = chunk.metadata if hasattr(chunk, 'metadata') else {}
                
                # Determine if this is a transcript chunk or profile chunk
                if 'pdf_type' in metadata:
                    # Profile chunk
                    profile_type = metadata.get("pdf_type", "")
                    speaker = "Adrian" if "boyfriend" in profile_type else "Elara"
                    text = metadata.get("extracted_text", "")
                    context_parts.append(
                        f"[{speaker}'s Profile - Background & Personality]:\n{text}\n"
                    )
                else:
                    # Transcript chunk
                    speaker = metadata.get("speaker", "Unknown")
                    text = metadata.get("text", "")
                    chunk_idx = metadata.get("chunk_index", "?")
                    conflict_id_chunk = metadata.get("conflict_id", "unknown")
                    context_parts.append(
                        f"[Chunk {idx} from conflict {conflict_id_chunk}, chunk {chunk_idx}, {speaker}]:\n{text}\n"
                    )
            
            context = "\n".join(context_parts)
            logger.info(f"Retrieved {len(chunks)} most relevant chunks from entire corpus (transcripts + profiles) for query: {query[:50]}...")
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
        return f"""Additional information relevant to the user's question from the ENTIRE conversation corpus and partner profiles:

{context}

CRITICAL: Use ALL available context to provide empathetic, contextualized responses:

1. **Transcript Context**: What was said in conversations (from current and past conflicts)
   - Reference specific speakers: Adrian or Elara
   - Relate current situation to past conversations when relevant

2. **Profile Context**: Adrian's and Elara's backgrounds, personalities, preferences, values
   - Use profile information to understand WHY someone feels a certain way
   - Example: If Adrian is passionate about sports (from profile) and hurt about a missed game (from transcript), 
     connect these: "I understand you're coming from a sports background and passionate about football, 
     so it hurt when Elara didn't attend the game even though she said 'sure'."

3. **Empathetic Understanding**: 
   - Show deep understanding by connecting transcript events to profile traits
   - Validate feelings by explaining WHY they make sense given the person's background
   - Be specific: "Given your passion for sports and how much football means to you..."

4. **Cross-Reference**: 
   - Connect current conflict to patterns from past conversations
   - Use profile information to explain emotional reactions
   - Show you understand the FULL context, not just the immediate situation

Reference specific speakers and their statements when relevant. Always connect transcript events to profile traits to show deep understanding."""

