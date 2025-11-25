"""RAG system for retrieving relevant transcript chunks and profile PDFs from Pinecone."""
import logging
from typing import Optional, List, Dict, Any
from app.services.pinecone_service import pinecone_service
from app.services.embeddings_service import embeddings_service
from app.services.reranker_service import reranker_service

logger = logging.getLogger(__name__)

# Import calendar service for calendar context
try:
    from app.services.calendar_service import calendar_service
except ImportError:
    calendar_service = None
    logger.warning("Calendar service not available - calendar insights will be disabled")


class TranscriptRAGSystem:
    """Retrieval-Augmented Generation system for conversation transcripts and profile PDFs.
    
    IMPORTANT: This system prioritizes the CURRENT conflict's transcript as PRIMARY context.
    When a user is viewing a specific conflict session, questions about "this conversation" 
    or "summarize what happened" should use ONLY that conflict's transcript.
    
    Secondary context (profiles, past conflicts) is added for deeper understanding but
    the current conflict is always the primary source.
    """
    
    def __init__(
        self,
        k: int = 7,  # Number of chunks from secondary sources
        include_profiles: bool = True,
        include_calendar: bool = True,  # NEW: Include calendar insights
    ):
        """
        Initialize transcript RAG system.
        
        Args:
            k: Number of additional chunks from secondary sources (profiles, past conflicts)
            include_profiles: Whether to also query profile PDFs (Adrian/Elara profiles)
            include_calendar: Whether to include calendar insights (cycle phase, upcoming events)
        """
        self.k = k
        self.include_profiles = include_profiles
        self.include_calendar = include_calendar
        logger.info(f"Initialized TranscriptRAGSystem with k={k}, include_profiles={include_profiles}, include_calendar={include_calendar}")
    
    def rag_lookup(
        self,
        query: str,
        conflict_id: Optional[str] = None,
        relationship_id: Optional[str] = None,
    ) -> str:
        """
        Perform RAG lookup with CURRENT CONFLICT as PRIMARY context.
        
        Strategy:
        1. FIRST: Fetch ALL chunks from the current conflict (using filter) - PRIMARY CONTEXT
        2. THEN: Optionally fetch relevant chunks from profiles and past conflicts - SECONDARY CONTEXT
        3. Rerank secondary context to get most relevant supplementary info
        
        This ensures that when the user asks about "this conversation" or "summarize",
        the current conflict's full transcript is always the primary source.
        
        Args:
            query: User query string
            conflict_id: Current conflict ID (REQUIRED for primary context)
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
            
            primary_chunks = []  # Chunks from CURRENT conflict (always included)
            secondary_candidates = []  # Chunks from profiles and past conflicts (reranked)
            
            pinecone_start = time.time()
            
            # =====================================================================
            # STEP 1: FETCH PRIMARY CONTEXT - ALL chunks from CURRENT conflict
            # =====================================================================
            if conflict_id:
                logger.info(f"📌 Fetching PRIMARY context: ALL chunks from current conflict {conflict_id}...")
                
                # Query with filter to get ONLY current conflict's chunks
                current_conflict_results = pinecone_service.index.query(
                    vector=query_embedding,
                    top_k=20,  # Get up to 20 chunks from current conflict
                    namespace="transcript_chunks",
                    filter={"conflict_id": {"$eq": conflict_id}},  # FILTER by conflict_id
                    include_metadata=True,
                )
                
                if current_conflict_results and hasattr(current_conflict_results, 'matches') and current_conflict_results.matches:
                    for match in current_conflict_results.matches:
                        metadata = match.metadata if hasattr(match, 'metadata') else {}
                        text = metadata.get("text", "")
                        if text:
                            primary_chunks.append({
                                'text': text,
                                'match': match,
                                'type': 'transcript',
                                'is_current_conflict': True,
                                'conflict_id': conflict_id,
                                'speaker': metadata.get("speaker", "Unknown"),
                                'chunk_index': metadata.get("chunk_index", 0),
                            })
                    
                    # Sort by chunk_index to maintain conversation order
                    primary_chunks.sort(key=lambda c: c.get('chunk_index', 0))
                    logger.info(f"   ✅ Found {len(primary_chunks)} chunks from CURRENT conflict (primary context)")
                else:
                    logger.warning(f"   ⚠️ No chunks found for current conflict {conflict_id}")
            
            # =====================================================================
            # STEP 2: FETCH SECONDARY CONTEXT - Profiles and past conflicts
            # =====================================================================
            logger.info(f"📚 Fetching SECONDARY context: profiles and past conflicts...")
            
            # Query profiles (if enabled)
            if self.include_profiles and relationship_id:
                try:
                    profile_results = pinecone_service.index.query(
                        vector=query_embedding,
                        top_k=3,  # Get top 3 profile chunks
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
                                secondary_candidates.append({
                                    'text': text,
                                    'match': match,
                                    'type': 'profile',
                                    'is_current_conflict': False,
                                    'profile_type': pdf_type,
                                    'speaker': speaker,
                                })
                        logger.info(f"   Found {len([c for c in secondary_candidates if c['type'] == 'profile'])} profile chunks")
                except Exception as e:
                    logger.warning(f"   Error querying profiles (non-fatal): {e}")
            
            # Query past conflicts (excluding current conflict)
            if conflict_id:
                try:
                    # Query transcripts WITHOUT the current conflict
                    past_conflict_results = pinecone_service.index.query(
                        vector=query_embedding,
                        top_k=5,  # Get top 5 from past conflicts
                        namespace="transcript_chunks",
                        filter={"conflict_id": {"$ne": conflict_id}},  # EXCLUDE current conflict
                        include_metadata=True,
                    )
                    
                    if past_conflict_results and hasattr(past_conflict_results, 'matches') and past_conflict_results.matches:
                        for match in past_conflict_results.matches:
                            metadata = match.metadata if hasattr(match, 'metadata') else {}
                            text = metadata.get("text", "")
                            if text:
                                secondary_candidates.append({
                                    'text': text,
                                    'match': match,
                                    'type': 'past_transcript',
                                    'is_current_conflict': False,
                                    'conflict_id': metadata.get("conflict_id", "unknown"),
                                    'speaker': metadata.get("speaker", "Unknown"),
                                    'chunk_index': metadata.get("chunk_index", 0),
                                })
                        logger.info(f"   Found {len([c for c in secondary_candidates if c['type'] == 'past_transcript'])} past conflict chunks")
                except Exception as e:
                    logger.warning(f"   Error querying past conflicts (non-fatal): {e}")
            
            pinecone_time = time.time() - pinecone_start
            logger.info(f"⏱️ Pinecone queries: {pinecone_time:.2f}s")
            
            # =====================================================================
            # STEP 3: RERANK SECONDARY CONTEXT (if any)
            # =====================================================================
            reranked_secondary = []
            rerank_time = 0.0
            
            if secondary_candidates:
                rerank_start = time.time()
                logger.info(f"🔄 Reranking {len(secondary_candidates)} secondary candidates to get top {self.k}...")
                
                candidate_texts = [c['text'] for c in secondary_candidates]
                reranked_results = reranker_service.rerank(
                    query=query,
                    documents=candidate_texts,
                    top_k=self.k
                )
                
                # Map reranked results back to original chunks
                for doc_text, score in reranked_results:
                    for candidate in secondary_candidates:
                        if candidate['text'] == doc_text:
                            candidate['rerank_score'] = score
                            reranked_secondary.append(candidate)
                            break
                
                rerank_time = time.time() - rerank_start
                logger.info(f"⏱️ Reranking: {rerank_time:.2f}s")
                logger.info(f"   ✅ Selected {len(reranked_secondary)} secondary chunks")
            
            # =====================================================================
            # STEP 4: GET CALENDAR INSIGHTS (if enabled)
            # =====================================================================
            calendar_context = ""
            if self.include_calendar and calendar_service:
                try:
                    logger.info("📅 Fetching calendar insights...")
                    calendar_context = calendar_service.get_calendar_insights_for_llm(
                        relationship_id=relationship_id or "00000000-0000-0000-0000-000000000000"
                    )
                    if calendar_context and calendar_context != "No calendar insights available.":
                        logger.info(f"   ✅ Calendar insights retrieved ({len(calendar_context)} chars)")
                    else:
                        calendar_context = ""
                except Exception as e:
                    logger.warning(f"   ⚠️ Error fetching calendar insights (non-fatal): {e}")
                    calendar_context = ""
            
            # =====================================================================
            # STEP 5: FORMAT CONTEXT - Calendar first, then Primary, then Secondary
            # =====================================================================
            if not primary_chunks and not reranked_secondary and not calendar_context:
                logger.warning(f"No relevant chunks found for query: {query[:50]}...")
                return "No relevant information found in the conversation transcript or profiles."
            
            context_parts = []
            
            # Add CALENDAR INSIGHTS header (first, as it affects interpretation)
            if calendar_context:
                context_parts.append("=" * 60)
                context_parts.append("📅 RELATIONSHIP CALENDAR INSIGHTS")
                context_parts.append("Current cycle phase, upcoming events, and patterns.")
                context_parts.append("Use this to understand emotional context and timing.")
                context_parts.append("=" * 60)
                context_parts.append("")
                context_parts.append(calendar_context)
                context_parts.append("")
            
            # Add PRIMARY context header
            if primary_chunks:
                context_parts.append("=" * 60)
                context_parts.append("📌 CURRENT CONVERSATION TRANSCRIPT (PRIMARY CONTEXT)")
                context_parts.append("This is the conversation the user is currently viewing.")
                context_parts.append("Use this as the PRIMARY source for questions about 'this conversation'.")
                context_parts.append("=" * 60)
                context_parts.append("")
                
                for idx, chunk_data in enumerate(primary_chunks, 1):
                    text = chunk_data.get('text', '')
                    speaker = chunk_data.get('speaker', 'Unknown')
                    chunk_idx = chunk_data.get('chunk_index', '?')
                    
                    context_parts.append(f"[Current Conversation - {speaker} (part {chunk_idx})]:")
                    context_parts.append(text)
                    context_parts.append("")
            
            # Add SECONDARY context header
            if reranked_secondary:
                context_parts.append("")
                context_parts.append("=" * 60)
                context_parts.append("📚 ADDITIONAL CONTEXT (SECONDARY - for deeper understanding)")
                context_parts.append("Profiles and past conversations for context, NOT the primary source.")
                context_parts.append("=" * 60)
                context_parts.append("")
                
                for idx, chunk_data in enumerate(reranked_secondary, 1):
                    text = chunk_data.get('text', '')
                    chunk_type = chunk_data.get('type', 'unknown')
                    
                    if chunk_type == 'profile':
                        speaker = chunk_data.get('speaker', 'Unknown')
                        # Limit profile text
                        max_profile_chars = 800
                        if len(text) > max_profile_chars:
                            text = text[:max_profile_chars] + "... [truncated]"
                        context_parts.append(f"[{speaker}'s Profile - Background & Personality]:")
                        context_parts.append(text)
                        context_parts.append("")
                    else:
                        # Past transcript
                        speaker = chunk_data.get('speaker', 'Unknown')
                        past_conflict_id = chunk_data.get('conflict_id', 'unknown')
                        context_parts.append(f"[Past Conversation - {speaker} (conflict: {past_conflict_id[:8]}...)]:")
                        context_parts.append(text)
                        context_parts.append("")
            
            context = "\n".join(context_parts)
            total_time = time.time() - start_time
            
            rag_timing_msg = (
                f"⏱️ RAG lookup: {total_time:.2f}s | "
                f"Primary: {len(primary_chunks)} chunks | "
                f"Secondary: {len(reranked_secondary)} chunks | "
                f"(embed: {embedding_time:.2f}s, pinecone: {pinecone_time:.2f}s, rerank: {rerank_time:.2f}s)"
            )
            logger.info(rag_timing_msg)
            print(rag_timing_msg)
            
            return context
            
        except Exception as e:
            logger.error(f"Error in transcript RAG lookup: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return "Error retrieving information from the conversation transcript."
    
    def get_current_conflict_transcript(self, conflict_id: str) -> str:
        """
        Fetch the FULL transcript for a specific conflict.
        Used when the user explicitly asks about "this conversation" or wants a summary.
        
        Args:
            conflict_id: The conflict ID to fetch
            
        Returns:
            Full transcript text or error message
        """
        try:
            logger.info(f"📌 Fetching FULL transcript for conflict {conflict_id}...")
            
            # First try to get all chunks from Pinecone
            from app.services.embeddings_service import embeddings_service
            
            # Use a generic embedding to query all chunks
            generic_query = "conversation discussion"
            query_embedding = embeddings_service.embed_query(generic_query)
            
            results = pinecone_service.index.query(
                vector=query_embedding,
                top_k=50,  # Get up to 50 chunks
                namespace="transcript_chunks",
                filter={"conflict_id": {"$eq": conflict_id}},
                include_metadata=True,
            )
            
            if results and hasattr(results, 'matches') and results.matches:
                # Sort by chunk_index to maintain order
                chunks = []
                for match in results.matches:
                    metadata = match.metadata if hasattr(match, 'metadata') else {}
                    text = metadata.get("text", "")
                    if text:
                        chunks.append({
                            'text': text,
                            'chunk_index': metadata.get("chunk_index", 0),
                            'speaker': metadata.get("speaker", "Unknown"),
                        })
                
                chunks.sort(key=lambda c: c.get('chunk_index', 0))
                
                # Format as continuous transcript
                transcript_parts = []
                for chunk in chunks:
                    transcript_parts.append(chunk['text'])
                
                full_transcript = "\n\n".join(transcript_parts)
                logger.info(f"   ✅ Retrieved full transcript ({len(full_transcript)} chars, {len(chunks)} chunks)")
                return full_transcript
            else:
                logger.warning(f"   ⚠️ No chunks found for conflict {conflict_id}")
                return "No transcript found for this conversation."
                
        except Exception as e:
            logger.error(f"Error fetching full transcript: {e}")
            return "Error retrieving transcript."
    
    def format_context_for_llm(self, context: str) -> str:
        """
        Format context for injection into LLM chat context.
        
        Args:
            context: Raw context string
            
        Returns:
            Formatted context string
        """
        return f"""CONTEXT FOR YOUR RESPONSE:

{context}

IMPORTANT INSTRUCTIONS:
1. **CURRENT CONVERSATION is PRIMARY**: When the user asks about "this conversation", "what happened", 
   "summarize", or refers to the current conflict - use ONLY the CURRENT CONVERSATION TRANSCRIPT section.
   
2. **Secondary context is supplementary**: Use profiles and past conversations to provide deeper 
   understanding, but they are NOT the primary source for questions about "this" conversation.

3. **Be specific**: Reference specific speakers (Adrian or Elara) and their actual statements.

4. **Connect insights**: Use profile information to explain WHY someone feels a certain way.
   Example: "Given Adrian's passion for sports, it makes sense that missing the game hurt him deeply."

5. **Stay focused**: If asked to summarize THIS conversation, summarize ONLY the current conversation,
   not past ones.

6. **CALENDAR AWARENESS (IMPORTANT)**: If calendar insights are provided:
   - Consider Elara's current cycle phase when discussing emotional dynamics
   - If she's in PMS/menstruation phase, acknowledge that hormonal shifts may amplify emotions
   - Don't dismiss her feelings, but help Adrian understand the biological context
   - When suggesting timing for conversations, consider upcoming events and cycle predictions
   - If conflicts correlate with certain cycle phases, mention this pattern sensitively
   - Use phrases like "This might be a more sensitive time" rather than "She's just hormonal"
   
7. **TIMING RECOMMENDATIONS**: When suggesting when to have conversations:
   - Avoid high-risk cycle phases if possible
   - Consider upcoming anniversaries/events that could be positive opportunities
   - Be mindful of predicted period dates when planning repair conversations"""
