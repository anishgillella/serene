"""
Pinecone vector database service for storing transcripts and analysis
"""
import logging
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class PineconeService:
    """Service for interacting with Pinecone vector database"""
    
    def __init__(self):
        try:
            self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            self.index_name = "serene"
            self.index = self.pc.Index(self.index_name)
            logger.info(f"✅ Connected to Pinecone index: {self.index_name}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Pinecone: {e}")
            self.pc = None
            self.index = None
    
    def upsert_transcript(
        self,
        conflict_id: str,
        embedding: List[float],
        transcript_data: Dict[str, Any],
        namespace: str = "transcripts"
    ):
        """Store transcript in Pinecone with full text"""
        if not self.index:
            logger.warning("⚠️ Pinecone index not initialized, skipping transcript storage")
            return
            
        try:
            full_transcript = transcript_data["transcript_text"]
            # Store full transcript (up to 35KB to leave room for other metadata)
            transcript_for_metadata = full_transcript[:35000] if len(full_transcript) <= 35000 else full_transcript[:35000]
            
            metadata = {
                "conflict_id": transcript_data["conflict_id"],
                "relationship_id": transcript_data["relationship_id"],
                "timestamp": transcript_data["timestamp"].isoformat() if isinstance(transcript_data["timestamp"], type) else str(transcript_data["timestamp"]),
                "duration": transcript_data["duration"],
                "partner_a_id": transcript_data["partner_a_id"],
                "partner_b_id": transcript_data["partner_b_id"],
                "transcript_text": transcript_for_metadata,  # Full transcript (up to 35KB)
                "transcript_length": len(full_transcript),
            }
            
            # Add optional fields
            if "start_time" in transcript_data and transcript_data["start_time"]:
                metadata["start_time"] = transcript_data["start_time"].isoformat() if isinstance(transcript_data["start_time"], type) else str(transcript_data["start_time"])
            if "end_time" in transcript_data and transcript_data["end_time"]:
                metadata["end_time"] = transcript_data["end_time"].isoformat() if isinstance(transcript_data["end_time"], type) else str(transcript_data["end_time"])
            if "speaker_labels" in transcript_data:
                # Convert dict to string for metadata
                metadata["speaker_labels"] = str(transcript_data["speaker_labels"])
            
            self.index.upsert(
                vectors=[{
                    "id": f"transcript_{conflict_id}",
                    "values": embedding,
                    "metadata": metadata
                }],
                namespace=namespace
            )
            logger.info(f"✅ Stored transcript for conflict {conflict_id} in namespace {namespace}")
        except Exception as e:
            logger.error(f"❌ Error storing transcript: {e}")
            raise
    
    def upsert_analysis(
        self,
        conflict_id: str,
        embedding: List[float],
        analysis_data: Dict[str, Any],
        namespace: str = "analysis"
    ):
        """Store analysis results in Pinecone with full JSON"""
        if not self.index:
            logger.warning("⚠️ Pinecone index not initialized, skipping analysis storage")
            return

        try:
            import json
            # Store full analysis as JSON string (Pinecone metadata can handle up to ~40KB)
            analysis_json = json.dumps(analysis_data, default=str)
            
            metadata = {
                "conflict_id": analysis_data["conflict_id"],
                "fight_summary": analysis_data.get("fight_summary", "")[:500],
                "root_causes": str(analysis_data.get("root_causes", [])),
                "analyzed_at": analysis_data.get("analyzed_at", "").isoformat() if hasattr(analysis_data.get("analyzed_at"), "isoformat") else str(analysis_data.get("analyzed_at", "")),
                "full_analysis_json": analysis_json[:35000] if len(analysis_json) <= 35000 else analysis_json[:35000]  # Store full JSON if fits
            }
            
            self.index.upsert(
                vectors=[{
                    "id": f"analysis_{conflict_id}",
                    "values": embedding,
                    "metadata": metadata
                }],
                namespace=namespace
            )
            logger.info(f"✅ Stored analysis for conflict {conflict_id} in namespace {namespace}")
        except Exception as e:
            logger.error(f"❌ Error storing analysis: {e}")
            raise
    
    def query(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        namespace: str = "transcripts",
        filter: Optional[Dict[str, Any]] = None
    ):
        """Query Pinecone for similar vectors"""
        if not self.index:
            logger.warning("⚠️ Pinecone index not initialized, skipping query")
            return None

        try:
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace=namespace,
                include_metadata=True,
                filter=filter
            )
            return results
        except Exception as e:
            logger.error(f"❌ Error querying Pinecone: {e}")
            raise
    
    def upsert_repair_plan(
        self,
        conflict_id: str,
        embedding: List[float],
        repair_plan_data: Dict[str, Any],
        namespace: str = "repair_plans"
    ):
        """Store repair plan in Pinecone with full JSON"""
        if not self.index:
            logger.warning("⚠️ Pinecone index not initialized, skipping repair plan storage")
            return

        try:
            import json
            # Store full repair plan as JSON string
            repair_plan_json = json.dumps(repair_plan_data, default=str)
            
            metadata = {
                "conflict_id": repair_plan_data["conflict_id"],
                "partner_requesting": repair_plan_data.get("partner_requesting", ""),
                "steps": str(repair_plan_data.get("steps", [])),
                "apology_script": repair_plan_data.get("apology_script", "")[:500],
                "timing_suggestion": repair_plan_data.get("timing_suggestion", "")[:200],
                "generated_at": repair_plan_data.get("generated_at", "").isoformat() if hasattr(repair_plan_data.get("generated_at"), "isoformat") else str(repair_plan_data.get("generated_at", "")),
                "full_repair_plan_json": repair_plan_json[:35000] if len(repair_plan_json) <= 35000 else repair_plan_json[:35000]  # Store full JSON if fits
            }
            
            self.index.upsert(
                vectors=[{
                    "id": f"repair_plan_{conflict_id}",
                    "values": embedding,
                    "metadata": metadata
                }],
                namespace=namespace
            )
            logger.info(f"✅ Stored repair plan for conflict {conflict_id} in namespace {namespace}")
        except Exception as e:
            logger.error(f"❌ Error storing repair plan: {e}")
            raise
    
    def get_by_conflict_id(
        self,
        conflict_id: str,
        namespace: str = "transcripts"
    ):
        """Retrieve a specific conflict by ID"""
        if not self.index:
            logger.warning("⚠️ Pinecone index not initialized, skipping retrieval")
            return None

        try:
            # Query with filter
            results = self.index.query(
                vector=[0.0] * 1024,  # Dummy vector, we're filtering by metadata
                top_k=1,
                namespace=namespace,
                include_metadata=True,
                filter={"conflict_id": {"$eq": conflict_id}}
            )
            if results.matches:
                logger.info(f"✅ Found conflict {conflict_id} in namespace {namespace}")
                return results.matches[0]
            else:
                logger.warning(f"⚠️ No conflict found with conflict_id={conflict_id} in namespace {namespace}")
                # Try fetching by direct ID format (transcript_{conflict_id}, analysis_{conflict_id}, etc.)
                id_prefix = namespace.rstrip('s')  # transcripts -> transcript, analysis -> analysis
                direct_id = f"{id_prefix}_{conflict_id}"
                logger.info(f"🔄 Trying direct ID fetch: {direct_id}")
                try:
                    fetch_result = self.index.fetch(
                        ids=[direct_id],
                        namespace=namespace
                    )
                    if fetch_result.vectors and direct_id in fetch_result.vectors:
                        vector_data = fetch_result.vectors[direct_id]
                        # Create a match-like object
                        class MatchResult:
                            def __init__(self, metadata):
                                self.metadata = metadata
                        logger.info(f"✅ Found conflict {conflict_id} via direct ID fetch")
                        return MatchResult(vector_data.get('metadata', {}))
                except Exception as fetch_error:
                    logger.error(f"❌ Error fetching by direct ID: {fetch_error}")
            return None
        except Exception as e:
            logger.error(f"❌ Error retrieving conflict {conflict_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def upsert_transcript_chunks(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        namespace: str = "transcript_chunks"
    ):
        """
        Store multiple transcript chunks in Pinecone.
        
        Args:
            chunks: List of chunk dictionaries with metadata
            embeddings: List of embeddings (one per chunk)
            namespace: Pinecone namespace for transcript chunks
        """
        if not self.index:
            logger.warning("⚠️ Pinecone index not initialized, skipping chunk storage")
            return
        
        if len(chunks) != len(embeddings):
            logger.error(f"❌ Mismatch: {len(chunks)} chunks but {len(embeddings)} embeddings")
            return
        
        try:
            vectors = []
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                conflict_id = chunk.get("conflict_id", "unknown")
                chunk_index = chunk.get("chunk_index", idx)
                chunk_id = f"chunk_{conflict_id}_{chunk_index}"
                
                metadata = chunk.get("metadata", {})
                # Ensure all required fields are present
                metadata.update({
                    "conflict_id": chunk.get("conflict_id", ""),
                    "relationship_id": chunk.get("relationship_id", ""),
                    "chunk_index": chunk_index,
                    "speaker": chunk.get("speaker", "Unknown"),
                    "text": chunk.get("content", "")[:10000],  # Limit text size for metadata
                })
                
                if "timestamp" in chunk:
                    metadata["timestamp"] = str(chunk["timestamp"])
                
                vectors.append({
                    "id": chunk_id,
                    "values": embedding,
                    "metadata": metadata
                })
            
            # Upsert in batches if needed (Pinecone supports up to 100 vectors per upsert)
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(
                    vectors=batch,
                    namespace=namespace
                )
            
            logger.info(f"✅ Stored {len(chunks)} transcript chunks in namespace {namespace}")
        except Exception as e:
            logger.error(f"❌ Error storing transcript chunks: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def query_transcript_chunks(
        self,
        query_embedding: List[float],
        conflict_id: Optional[str] = None,
        relationship_id: Optional[str] = None,
        top_k: int = 5,
        namespace: str = "transcript_chunks"
    ):
        """
        Query Pinecone for relevant transcript chunks.
        
        Args:
            query_embedding: Query embedding vector
            conflict_id: Filter by conflict_id (priority)
            relationship_id: Filter by relationship_id (fallback)
            top_k: Number of results to return
            namespace: Pinecone namespace
            
        Returns:
            Query results with matches
        """
        if not self.index:
            logger.warning("⚠️ Pinecone index not initialized, skipping query")
            return None
        
        try:
            filter_dict = None
            if conflict_id:
                filter_dict = {"conflict_id": {"$eq": conflict_id}}
            elif relationship_id:
                filter_dict = {"relationship_id": {"$eq": relationship_id}}
            
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace=namespace,
                include_metadata=True,
                filter=filter_dict
            )
            
            return results
        except Exception as e:
            logger.error(f"❌ Error querying transcript chunks: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

# Singleton instance
pinecone_service = PineconeService()

