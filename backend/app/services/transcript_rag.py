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
            import time
            start_time = time.time()
            
            # Generate query embedding
            embedding_start = time.time()
            query_embedding = embeddings_service.embed_query(query)
            embedding_time = time.time() - embedding_start
            logger.info(f"⏱️ Embedding generation: {embedding_time:.2f}s")
            
            # Query ENTIRE corpus - get candidate chunks from ALL sources (transcripts + profiles)
            # Then rerank ALL together to get most relevant ones (saves tokens, better context)
            logger.info(f"Querying ENTIRE corpus (transcripts + profiles) for query: {query[:50]}...")
            
            # Step 1: Query BOTH namespaces (they're separate in Pinecone, so we query each)
            # Strategy: Get top_k=10 TOTAL candidates (7 transcripts + 3 profiles) for faster reranking
            # This is faster than querying top_k=10 from each (20 total) because reranking 10 is faster than 20
            
            transcript_candidates = []
            profile_candidates = []
            
            pinecone_start = time.time()
            
            # Query transcript_chunks namespace - get top 5 most relevant
            transcript_results = pinecone_service.index.query(
                vector=query_embedding,
                top_k=5,  # Get top 5 from transcripts (optimized for faster reranking)
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
            
            # Query profiles namespace - get top 3 most relevant (if profiles enabled)
            if self.include_profiles and relationship_id:
                try:
                    profile_results = pinecone_service.index.query(
                        vector=query_embedding,
                        top_k=2,  # Get top 2 from profiles (optimized for faster reranking)
                        namespace="profiles",
                        filter={"relationship_id": {"$eq": relationship_id}},
                        include_metadata=True
                    )
                    
                    if profile_results and hasattr(profile_results, 'matches') and profile_results.matches:
                        for match in profile_results.matches:
                            metadata = match.metadata if hasattr(match, 'metadata') else {}
                            text = metadata.get("extracted_text", "")
                            pdf_type = metadata.get("pdf_type", "")
                            if text:
                                speaker = "Adrian" if "boyfriend" in pdf_type else "Elara"
                                profile_candidates.append({
                                    'text': text,
                                    'match': match,
                                    'type': 'profile',
                                    'profile_type': pdf_type,
                                    'speaker': speaker,
                                })
                    
                    logger.info(f"Found {len(profile_candidates)} profile candidate chunks")
                except Exception as e:
                    logger.warning(f"Error querying profiles for reranking (non-fatal): {e}")
            
            pinecone_time = time.time() - pinecone_start
            logger.info(f"⏱️ Pinecone queries (both namespaces): {pinecone_time:.2f}s")
            
            # Step 3: Combine ALL candidates (transcripts + profiles) into SINGLE corpus
            # This ensures we get top k from the ENTIRE combined corpus, not separate top k's
            all_candidates = transcript_candidates + profile_candidates
            logger.info(f"Total candidates from COMBINED corpus: {len(all_candidates)} ({len(transcript_candidates)} transcripts + {len(profile_candidates)} profiles)")
            
            # Step 4: Rerank ALL candidates together to get top k from ENTIRE COMBINED CORPUS
            # This ensures we get the k most relevant chunks from transcripts + profiles combined
            chunks = []
            rerank_time = 0.0
            if all_candidates:
                rerank_start = time.time()
                logger.info(f"Reranking {len(all_candidates)} candidate chunks from COMBINED corpus (transcripts + profiles) to get top {self.k} most relevant...")
                candidate_texts = [c['text'] for c in all_candidates]
                reranked_results = reranker_service.rerank(
                    query=query,
                    documents=candidate_texts,
                    top_k=self.k  # Get top_k most relevant from ENTIRE COMBINED CORPUS
                )
                rerank_time = time.time() - rerank_start
                logger.info(f"⏱️ Reranking {len(all_candidates)} candidates: {rerank_time:.2f}s")
                
                # Map reranked results back to original chunks
                # Store both match object AND text for proper formatting
                reranked_chunks = []
                for doc_text, score in reranked_results:
                    # Find the original candidate that matches this text
                    for candidate in all_candidates:
                        if candidate['text'] == doc_text:
                            # Store candidate dict (has both match and text) instead of just match
                            reranked_chunks.append(candidate)
                            break
                
                chunks = reranked_chunks
                logger.info(f"✅ Reranked to top {len(chunks)} most relevant chunks from ENTIRE COMBINED CORPUS (transcripts + profiles)")
            
            # Format reranked chunks into context (mix of transcripts and profiles)
            if not chunks:
                logger.warning(f"No relevant chunks found for query: {query[:50]}...")
                return "No relevant information found in the conversation transcript or profiles."
            
            context_parts = []
            for idx, chunk_data in enumerate(chunks, 1):
                # chunk_data is now a candidate dict with 'text', 'match', 'type', etc.
                # Use the text we already extracted (more reliable than reading from metadata again)
                text = chunk_data.get('text', '')
                chunk_type = chunk_data.get('type', 'unknown')
                
                if not text:
                    logger.warning(f"Chunk {idx} ({chunk_type}) has empty text - skipping")
                    continue
                
                # Get metadata from match object for additional info
                match_obj = chunk_data.get('match')
                metadata = match_obj.metadata if (match_obj and hasattr(match_obj, 'metadata')) else {}
                
                if chunk_type == 'profile':
                    # Profile chunk - Limit to 1000 chars for faster LLM processing
                    # Full profile chunks can be very large, but we only need the most relevant parts
                    profile_type = chunk_data.get('profile_type', '')
                    speaker = chunk_data.get('speaker', 'Unknown')
                    max_profile_chars = 1000
                    if len(text) > max_profile_chars:
                        text = text[:max_profile_chars] + "... [truncated for relevance]"
                    context_parts.append(
                        f"[{speaker}'s Profile - Background & Personality]:\n{text}\n"
                    )
                    logger.debug(f"Added profile chunk {idx}: {len(text)} chars from {speaker} (truncated from {len(chunk_data.get('text', ''))} chars)")
                else:
                    # Transcript chunk
                    speaker = chunk_data.get('speaker', metadata.get('speaker', 'Unknown'))
                    chunk_idx = metadata.get('chunk_index', '?')
                    conflict_id_chunk = chunk_data.get('conflict_id', metadata.get('conflict_id', 'unknown'))
                    context_parts.append(
                        f"[Chunk {idx} from conflict {conflict_id_chunk}, chunk {chunk_idx}, {speaker}]:\n{text}\n"
                    )
                    logger.debug(f"Added transcript chunk {idx}: {len(text)} chars from {speaker}")
            
            context = "\n".join(context_parts)
            total_time = time.time() - start_time
            rag_timing_msg = f"⏱️ Total RAG lookup time: {total_time:.2f}s (embedding: {embedding_time:.2f}s, pinecone: {pinecone_time:.2f}s, rerank: {rerank_time:.2f}s)"
            logger.info(f"✅ Retrieved {len(chunks)} most relevant chunks from entire corpus (transcripts + profiles) for query: {query[:50]}...")
            logger.info(rag_timing_msg)
            print(rag_timing_msg)  # Also print to stdout for visibility
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

