"""
Post-fight session API endpoints
"""
import logging
import asyncio
from fastapi import APIRouter, HTTPException, Body, BackgroundTasks
from typing import Optional, List
from datetime import datetime
from app.services.pinecone_service import pinecone_service
from app.services.embeddings_service import embeddings_service
from app.services.reranker_service import reranker_service
from app.tools.conflict_analysis import analyze_conflict_transcript
from app.tools.repair_coaching import generate_repair_plan
from app.models.schemas import ConflictAnalysis, RepairPlan, ConflictTranscript, SpeakerSegment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/post-fight", tags=["post-fight"])

async def generate_analysis_and_repair_plan_background(
    conflict_id: str,
    transcript_text: str,
    relationship_id: str,
    partner_a_id: str,
    partner_b_id: str,
    speaker_labels: dict,
    duration: float,
    timestamp: datetime
):
    """Background task to generate analysis and repair plan in parallel"""
    try:
        logger.info(f"🚀 Starting background generation for conflict {conflict_id}")
        logger.info(f"📝 Full transcript length: {len(transcript_text)} characters")
        
        # Use RAG pipeline with reranker to get relevant profile information
        boyfriend_profile = None
        girlfriend_profile = None
        try:
            # Generate query embedding from transcript for semantic search
            query_embedding = embeddings_service.embed_query(transcript_text)
            
            # Search for boyfriend profile chunks
            boyfriend_results = pinecone_service.query(
                query_embedding=query_embedding,
                top_k=5,  # Get top 5 chunks
                namespace="profiles",
                filter={
                    "relationship_id": {"$eq": relationship_id},
                    "pdf_type": {"$eq": "boyfriend_profile"}
                }
            )
            
            # Extract text from results
            boyfriend_chunks = []
            if boyfriend_results.matches:
                for match in boyfriend_results.matches:
                    chunk_text = match.metadata.get("extracted_text", "")
                    if chunk_text:
                        boyfriend_chunks.append(chunk_text)
            
            # Rerank chunks based on transcript relevance
            if boyfriend_chunks:
                reranked_bf = reranker_service.rerank(
                    query=transcript_text[:500],  # Use first 500 chars as query
                    documents=boyfriend_chunks,
                    top_k=3  # Get top 3 most relevant chunks
                )
                boyfriend_profile = "\n\n".join([chunk for chunk, score in reranked_bf])
                logger.info(f"✅ Retrieved {len(reranked_bf)} relevant boyfriend profile chunks via reranker")
            
            # Search for girlfriend profile chunks
            girlfriend_results = pinecone_service.query(
                query_embedding=query_embedding,
                top_k=5,  # Get top 5 chunks
                namespace="profiles",
                filter={
                    "relationship_id": {"$eq": relationship_id},
                    "pdf_type": {"$eq": "girlfriend_profile"}
                }
            )
            
            # Extract text from results
            girlfriend_chunks = []
            if girlfriend_results.matches:
                for match in girlfriend_results.matches:
                    chunk_text = match.metadata.get("extracted_text", "")
                    if chunk_text:
                        girlfriend_chunks.append(chunk_text)
            
            # Rerank chunks based on transcript relevance
            if girlfriend_chunks:
                reranked_gf = reranker_service.rerank(
                    query=transcript_text[:500],  # Use first 500 chars as query
                    documents=girlfriend_chunks,
                    top_k=3  # Get top 3 most relevant chunks
                )
                girlfriend_profile = "\n\n".join([chunk for chunk, score in reranked_gf])
                logger.info(f"✅ Retrieved {len(reranked_gf)} relevant girlfriend profile chunks via reranker")
                
        except Exception as e:
            logger.info(f"⚠️ RAG retrieval failed, using transcript only: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Generate analysis first (repair plans need it)
        analysis = await analyze_conflict_transcript(
            conflict_id=conflict_id,
            transcript_text=transcript_text,
            relationship_id=relationship_id,
            partner_a_id=partner_a_id,
            partner_b_id=partner_b_id,
            speaker_labels=speaker_labels,
            duration=duration,
            timestamp=timestamp,
            partner_id=None,
            boyfriend_profile=boyfriend_profile,
            girlfriend_profile=girlfriend_profile
        )
        logger.info(f"✅ Analysis complete for {conflict_id}")
        
        # Generate repair plans for both partners in parallel (now that we have analysis)
        repair_plan_boyfriend, repair_plan_girlfriend = await asyncio.gather(
            generate_repair_plan(
                conflict_id=conflict_id,
                transcript_text=transcript_text,
                partner_requesting_id="partner_a",
                relationship_id=relationship_id,
                partner_a_id=partner_a_id,
                partner_b_id=partner_b_id,
                analysis=analysis,
                boyfriend_profile=boyfriend_profile,
                girlfriend_profile=girlfriend_profile
            ),
            generate_repair_plan(
                conflict_id=conflict_id,
                transcript_text=transcript_text,
                partner_requesting_id="partner_b",
                relationship_id=relationship_id,
                partner_a_id=partner_a_id,
                partner_b_id=partner_b_id,
                analysis=analysis,
                boyfriend_profile=boyfriend_profile,
                girlfriend_profile=girlfriend_profile
            )
        )
        
        # Store repair plans in Pinecone
        try:
            repair_plan_text_bf = f"{repair_plan_boyfriend.apology_script} {' '.join(repair_plan_boyfriend.steps)}"
            repair_plan_embedding_bf = embeddings_service.embed_text(repair_plan_text_bf)
            repair_plan_dict_bf = repair_plan_boyfriend.model_dump()
            repair_plan_dict_bf["generated_at"] = datetime.now()
            pinecone_service.upsert_repair_plan(
                conflict_id=f"{conflict_id}_boyfriend",
                embedding=repair_plan_embedding_bf,
                repair_plan_data=repair_plan_dict_bf,
                namespace="repair_plans"
            )
            
            repair_plan_text_gf = f"{repair_plan_girlfriend.apology_script} {' '.join(repair_plan_girlfriend.steps)}"
            repair_plan_embedding_gf = embeddings_service.embed_text(repair_plan_text_gf)
            repair_plan_dict_gf = repair_plan_girlfriend.model_dump()
            repair_plan_dict_gf["generated_at"] = datetime.now()
            pinecone_service.upsert_repair_plan(
                conflict_id=f"{conflict_id}_girlfriend",
                embedding=repair_plan_embedding_gf,
                repair_plan_data=repair_plan_dict_gf,
                namespace="repair_plans"
            )
            
            logger.info(f"✅ Repair plans stored for {conflict_id} (both partners)")
        except Exception as e:
            logger.error(f"❌ Error storing repair plans: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        logger.info(f"✅ Background generation complete for conflict {conflict_id}")
        
    except Exception as e:
        logger.error(f"❌ Error in background generation: {e}")
        import traceback
        logger.error(traceback.format_exc())

@router.post("/conflicts/{conflict_id}/store-transcript")
async def store_transcript(
    conflict_id: str,
    background_tasks: BackgroundTasks,
    request: dict = Body(...)
):
    """
    Store transcript in Pinecone after fight capture ends
    
    Request body:
    {
        "transcript": ["Boyfriend: text", "Girlfriend: text", ...],
        "relationship_id": "id",
        "partner_a_id": "id",
        "partner_b_id": "id",
        "duration": 120.0,
        "speaker_labels": {0: "Boyfriend", 1: "Girlfriend"}
    }
    """
    try:
        transcript_lines = request.get("transcript", [])
        relationship_id = request.get("relationship_id", "00000000-0000-0000-0000-000000000000")
        partner_a_id = request.get("partner_a_id", "partner_a")
        partner_b_id = request.get("partner_b_id", "partner_b")
        duration = request.get("duration", 0.0)
        speaker_labels = request.get("speaker_labels", {})
        
        logger.info(f"📝 Storing transcript for conflict {conflict_id}: {len(transcript_lines)} lines")
        
        if not transcript_lines or len(transcript_lines) == 0:
            logger.error(f"❌ Empty transcript lines received for conflict {conflict_id}")
            raise HTTPException(
                status_code=400,
                detail="Transcript is empty. Please ensure the fight was properly captured."
            )
        
        # Build transcript text and speaker segments
        import re
        # Handle both array of strings and array of objects
        if isinstance(transcript_lines[0], dict):
            # Format: [{speaker: "Boyfriend", text: "..."}, ...]
            transcript_text = "\n".join([f"{item.get('speaker', 'Unknown')}: {item.get('text', '')}" for item in transcript_lines])
        else:
            # Format: ["Boyfriend: text", "Girlfriend: text", ...]
            transcript_text = "\n".join([str(line) for line in transcript_lines])
        
        if not transcript_text or len(transcript_text.strip()) == 0:
            logger.error(f"❌ Empty transcript text for conflict {conflict_id}")
            raise HTTPException(
                status_code=400,
                detail="Transcript text is empty after processing."
            )
        
        logger.info(f"✅ Processed transcript: {len(transcript_text)} characters")
        speaker_segments: List[SpeakerSegment] = []
        
        for line in transcript_lines:
            if not isinstance(line, str):
                continue
                
            boyfriend_match = re.match(r'^(?:Boyfriend|Speaker\s+1):\s*(.+)$', line, re.IGNORECASE)
            girlfriend_match = re.match(r'^(?:Girlfriend|Speaker\s+2):\s*(.+)$', line, re.IGNORECASE)
            
            if boyfriend_match:
                speaker_segments.append(SpeakerSegment(
                    speaker="Boyfriend",
                    text=boyfriend_match.group(1),
                    start_time=None,
                    end_time=None
                ))
            elif girlfriend_match:
                speaker_segments.append(SpeakerSegment(
                    speaker="Girlfriend",
                    text=girlfriend_match.group(1),
                    start_time=None,
                    end_time=None
                ))
        
        # Create ConflictTranscript model
        conflict_transcript = ConflictTranscript(
            conflict_id=conflict_id,
            relationship_id=relationship_id,
            transcript_text=transcript_text,
            speaker_segments=speaker_segments,
            timestamp=datetime.now(),
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=duration,
            partner_a_id=partner_a_id,
            partner_b_id=partner_b_id,
            speaker_labels=speaker_labels
        )
        
        # Generate embedding and store in Pinecone
        embedding = embeddings_service.embed_text(transcript_text)
        pinecone_service.upsert_transcript(
            conflict_id=conflict_id,
            embedding=embedding,
            transcript_data=conflict_transcript.model_dump(),
            namespace="transcripts"
        )
        
        logger.info(f"✅ Stored transcript for conflict {conflict_id} in Pinecone")
        
        # Trigger background generation of analysis and repair plan
        background_tasks.add_task(
            generate_analysis_and_repair_plan_background,
            conflict_id=conflict_id,
            transcript_text=transcript_text,
            relationship_id=relationship_id,
            partner_a_id=partner_a_id,
            partner_b_id=partner_b_id,
            speaker_labels=speaker_labels,
            duration=duration,
            timestamp=datetime.now()
        )
        logger.info(f"🚀 Started background generation for conflict {conflict_id}")
        
        return {
            "success": True,
            "conflict_id": conflict_id,
            "message": "Transcript stored successfully. Analysis and repair plan are being generated in the background."
        }
        
    except Exception as e:
        logger.error(f"❌ Error storing transcript: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conflicts/{conflict_id}/analyze")
async def analyze_conflict(
    conflict_id: str,
    request: dict = Body(...)
):
    """
    Analyze a conflict transcript - returns cached analysis if available, otherwise generates new
    
    Request body:
    {
        "partner_id": "optional"  # For personalized analysis
    }
    """
    try:
        # First, check if analysis is already cached
        cached_analysis = pinecone_service.get_by_conflict_id(
            conflict_id=conflict_id,
            namespace="analysis"
        )
        
        if cached_analysis and cached_analysis.metadata:
            import json
            full_json = cached_analysis.metadata.get("full_analysis_json")
            if full_json:
                try:
                    logger.info(f"✅ Returning cached analysis for {conflict_id}")
                    analysis_data = json.loads(full_json)
                    # Convert back to ConflictAnalysis model
                    analysis = ConflictAnalysis(**analysis_data)
                    return {
                        "success": True,
                        "analysis": analysis.model_dump(),
                        "cached": True
                    }
                except Exception as e:
                    logger.warning(f"Failed to parse cached analysis: {e}, generating new one")
        
        # Get transcript from Pinecone
        transcript_result = pinecone_service.get_by_conflict_id(
            conflict_id=conflict_id,
            namespace="transcripts"
        )
        
        if not transcript_result or not transcript_result.metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Conflict {conflict_id} not found"
            )
        
        metadata = transcript_result.metadata
        transcript_text = metadata.get("transcript_text", "")
        
        # Extract metadata
        relationship_id = metadata.get("relationship_id", "")
        partner_a_id = metadata.get("partner_a_id", "partner_a")
        partner_b_id = metadata.get("partner_b_id", "partner_b")
        duration = metadata.get("duration", 0.0)
        
        # Parse speaker labels
        speaker_labels_str = metadata.get("speaker_labels", "{}")
        speaker_labels = eval(speaker_labels_str) if isinstance(speaker_labels_str, str) else speaker_labels_str
        
        # Parse timestamp
        timestamp_str = metadata.get("timestamp", datetime.now().isoformat())
        timestamp = datetime.fromisoformat(timestamp_str) if isinstance(timestamp_str, str) else timestamp_str
        
        # Use RAG pipeline with reranker to get relevant profile information
        boyfriend_profile = None
        girlfriend_profile = None
        try:
            # Generate query embedding from transcript for semantic search
            query_embedding = embeddings_service.embed_query(transcript_text)
            
            # Search for boyfriend profile chunks
            boyfriend_results = pinecone_service.query(
                query_embedding=query_embedding,
                top_k=5,
                namespace="profiles",
                filter={
                    "relationship_id": {"$eq": relationship_id},
                    "pdf_type": {"$eq": "boyfriend_profile"}
                }
            )
            
            boyfriend_chunks = []
            if boyfriend_results.matches:
                for match in boyfriend_results.matches:
                    chunk_text = match.metadata.get("extracted_text", "")
                    if chunk_text:
                        boyfriend_chunks.append(chunk_text)
            
            if boyfriend_chunks:
                reranked_bf = reranker_service.rerank(
                    query=transcript_text[:500],
                    documents=boyfriend_chunks,
                    top_k=3
                )
                boyfriend_profile = "\n\n".join([chunk for chunk, score in reranked_bf])
            
            # Search for girlfriend profile chunks
            girlfriend_results = pinecone_service.query(
                query_embedding=query_embedding,
                top_k=5,
                namespace="profiles",
                filter={
                    "relationship_id": {"$eq": relationship_id},
                    "pdf_type": {"$eq": "girlfriend_profile"}
                }
            )
            
            girlfriend_chunks = []
            if girlfriend_results.matches:
                for match in girlfriend_results.matches:
                    chunk_text = match.metadata.get("extracted_text", "")
                    if chunk_text:
                        girlfriend_chunks.append(chunk_text)
            
            if girlfriend_chunks:
                reranked_gf = reranker_service.rerank(
                    query=transcript_text[:500],
                    documents=girlfriend_chunks,
                    top_k=3
                )
                girlfriend_profile = "\n\n".join([chunk for chunk, score in reranked_gf])
                
        except Exception as e:
            logger.info(f"⚠️ RAG retrieval failed, using transcript only: {e}")
        
        # Generate analysis (will use transcript only if profiles unavailable)
        analysis = await analyze_conflict_transcript(
            conflict_id=conflict_id,
            transcript_text=transcript_text,
            relationship_id=relationship_id,
            partner_a_id=partner_a_id,
            partner_b_id=partner_b_id,
            speaker_labels=speaker_labels,
            duration=duration,
            timestamp=timestamp,
            partner_id=request.get("partner_id"),
            boyfriend_profile=boyfriend_profile,
            girlfriend_profile=girlfriend_profile
        )
        
        return {
            "success": True,
            "analysis": analysis.model_dump(),
            "cached": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error analyzing conflict: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error analyzing conflict: {str(e)}")


@router.post("/conflicts/{conflict_id}/repair-plan")
async def get_repair_plan(
    conflict_id: str,
    request: dict = Body(...)
):
    """
    Get repair plan - returns cached plan if available, otherwise generates new
    
    Request body:
    {
        "partner_id": "required"  # Partner requesting the plan (partner_a or partner_b)
    }
    """
    try:
        partner_id = request.get("partner_id")
        if not partner_id:
            raise HTTPException(
                status_code=400,
                detail="partner_id is required"
            )
        
        # Determine which cached plan to check (boyfriend or girlfriend)
        plan_suffix = "boyfriend" if partner_id == "partner_a" else "girlfriend"
        cached_plan_id = f"{conflict_id}_{plan_suffix}"
        
        # First, check if repair plan is already cached
        cached_plan = pinecone_service.get_by_conflict_id(
            conflict_id=cached_plan_id,
            namespace="repair_plans"
        )
        
        if cached_plan and cached_plan.metadata:
            import json
            full_json = cached_plan.metadata.get("full_repair_plan_json")
            if full_json:
                try:
                    logger.info(f"✅ Returning cached repair plan for {conflict_id} ({plan_suffix})")
                    repair_plan_data = json.loads(full_json)
                    repair_plan = RepairPlan(**repair_plan_data)
                    return {
                        "success": True,
                        "repair_plan": repair_plan.model_dump(),
                        "cached": True
                    }
                except Exception as e:
                    logger.warning(f"Failed to parse cached repair plan: {e}, generating new one")
        
        # Get transcript from Pinecone
        transcript_result = pinecone_service.get_by_conflict_id(
            conflict_id=conflict_id,
            namespace="transcripts"
        )
        
        if not transcript_result or not transcript_result.metadata:
            logger.error(f"❌ Transcript not found for conflict {conflict_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Conflict {conflict_id} not found. Please ensure the fight was properly captured."
            )
        
        metadata = transcript_result.metadata
        transcript_text = metadata.get("transcript_text", "")
        
        if not transcript_text or len(transcript_text.strip()) == 0:
            logger.error(f"❌ Empty transcript for conflict {conflict_id}")
            raise HTTPException(
                status_code=400,
                detail=f"Transcript is empty for conflict {conflict_id}. Please ensure the fight was properly captured."
            )
        
        relationship_id = metadata.get("relationship_id", "")
        partner_a_id = metadata.get("partner_a_id", "partner_a")
        partner_b_id = metadata.get("partner_b_id", "partner_b")
        
        logger.info(f"📝 Retrieved transcript for repair plan {conflict_id}: {len(transcript_text)} chars")
        
        # Try to get analysis if available
        analysis_result = pinecone_service.get_by_conflict_id(
            conflict_id=conflict_id,
            namespace="analysis"
        )
        analysis = None
        if analysis_result and analysis_result.metadata:
            import json
            analysis_json = analysis_result.metadata.get("full_analysis_json")
            if analysis_json:
                try:
                    analysis_data = json.loads(analysis_json)
                    analysis = ConflictAnalysis(**analysis_data)
                except Exception:
                    pass
        
        # Use RAG pipeline with reranker to get relevant profile information
        boyfriend_profile = None
        girlfriend_profile = None
        try:
            # Generate query embedding from transcript for semantic search
            query_embedding = embeddings_service.embed_query(transcript_text)
            
            # Search for boyfriend profile chunks
            boyfriend_results = pinecone_service.query(
                query_embedding=query_embedding,
                top_k=5,
                namespace="profiles",
                filter={
                    "relationship_id": {"$eq": relationship_id},
                    "pdf_type": {"$eq": "boyfriend_profile"}
                }
            )
            
            boyfriend_chunks = []
            if boyfriend_results.matches:
                for match in boyfriend_results.matches:
                    chunk_text = match.metadata.get("extracted_text", "")
                    if chunk_text:
                        boyfriend_chunks.append(chunk_text)
            
            if boyfriend_chunks:
                reranked_bf = reranker_service.rerank(
                    query=transcript_text[:500],
                    documents=boyfriend_chunks,
                    top_k=3
                )
                boyfriend_profile = "\n\n".join([chunk for chunk, score in reranked_bf])
            
            # Search for girlfriend profile chunks
            girlfriend_results = pinecone_service.query(
                query_embedding=query_embedding,
                top_k=5,
                namespace="profiles",
                filter={
                    "relationship_id": {"$eq": relationship_id},
                    "pdf_type": {"$eq": "girlfriend_profile"}
                }
            )
            
            girlfriend_chunks = []
            if girlfriend_results.matches:
                for match in girlfriend_results.matches:
                    chunk_text = match.metadata.get("extracted_text", "")
                    if chunk_text:
                        girlfriend_chunks.append(chunk_text)
            
            if girlfriend_chunks:
                reranked_gf = reranker_service.rerank(
                    query=transcript_text[:500],
                    documents=girlfriend_chunks,
                    top_k=3
                )
                girlfriend_profile = "\n\n".join([chunk for chunk, score in reranked_gf])
                
        except Exception as e:
            logger.info(f"⚠️ RAG retrieval failed, using transcript only: {e}")
        
        # Generate repair plan (will use transcript only if profiles unavailable)
        repair_plan = await generate_repair_plan(
            conflict_id=conflict_id,
            transcript_text=transcript_text,
            partner_requesting_id=partner_id,
            relationship_id=relationship_id,
            partner_a_id=partner_a_id,
            partner_b_id=partner_b_id,
            analysis=analysis,
            boyfriend_profile=boyfriend_profile,
            girlfriend_profile=girlfriend_profile
        )
        
        return {
            "success": True,
            "repair_plan": repair_plan.model_dump(),
            "cached": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating repair plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conflicts/{conflict_id}/rant")
async def store_rant(
    conflict_id: str,
    request: dict = Body(...)
):
    """
    Handle private rant chat messages with HeartSync AI that has full context
    
    Request body:
    {
        "message": "user's message",
        "partner_id": "id",
        "conversation_history": [{"role": "user|assistant", "content": "..."}]
    }
    """
    try:
        from app.services.llm_service import llm_service
        
        message = request.get("message", "")
        partner_id = request.get("partner_id", "partner_a")
        conversation_history = request.get("conversation_history", [])
        
        if not message:
            raise HTTPException(
                status_code=400,
                detail="message is required"
            )
        
        # Get full context: transcript, analysis, profiles
        transcript_text = ""
        analysis_summary = ""
        boyfriend_profile = None
        girlfriend_profile = None
        relationship_id = ""
        
        try:
            # Get transcript
            transcript_result = pinecone_service.get_by_conflict_id(
                conflict_id=conflict_id,
                namespace="transcripts"
            )
            
            if transcript_result and transcript_result.metadata:
                metadata = transcript_result.metadata
                transcript_text = metadata.get("transcript_text", "")
                relationship_id = metadata.get("relationship_id", "")
                
                # Get analysis if available
                analysis_result = pinecone_service.get_by_conflict_id(
                    conflict_id=conflict_id,
                    namespace="analysis"
                )
                if analysis_result and analysis_result.metadata:
                    import json
                    analysis_json = analysis_result.metadata.get("full_analysis_json")
                    if analysis_json:
                        try:
                            analysis_data = json.loads(analysis_json)
                            analysis_summary = analysis_data.get("fight_summary", "")
                            root_causes = analysis_data.get("root_causes", [])
                            if root_causes:
                                analysis_summary += f"\n\nRoot causes: {', '.join(root_causes[:3])}"
                        except Exception:
                            pass
                
                # Get profiles via RAG
                try:
                    query_embedding = embeddings_service.embed_query(message)
                    
                    boyfriend_results = pinecone_service.query(
                        query_embedding=query_embedding,
                        top_k=3,
                        namespace="profiles",
                        filter={
                            "relationship_id": {"$eq": relationship_id},
                            "pdf_type": {"$eq": "boyfriend_profile"}
                        }
                    )
                    boyfriend_chunks = [match.metadata.get("extracted_text", "") for match in boyfriend_results.matches if match.metadata.get("extracted_text", "")]
                    if boyfriend_chunks:
                        reranked_bf = reranker_service.rerank(query=message[:500], documents=boyfriend_chunks, top_k=2)
                        boyfriend_profile = "\n\n".join([chunk for chunk, score in reranked_bf])
                    
                    girlfriend_results = pinecone_service.query(
                        query_embedding=query_embedding,
                        top_k=3,
                        namespace="profiles",
                        filter={
                            "relationship_id": {"$eq": relationship_id},
                            "pdf_type": {"$eq": "girlfriend_profile"}
                        }
                    )
                    girlfriend_chunks = [match.metadata.get("extracted_text", "") for match in girlfriend_results.matches if match.metadata.get("extracted_text", "")]
                    if girlfriend_chunks:
                        reranked_gf = reranker_service.rerank(query=message[:500], documents=girlfriend_chunks, top_k=2)
                        girlfriend_profile = "\n\n".join([chunk for chunk, score in reranked_gf])
                except Exception as e:
                    logger.info(f"⚠️ RAG retrieval failed for rant: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Could not retrieve full context: {e}")
        
        # Build context for HeartSync
        context_parts = []
        if transcript_text:
            context_parts.append(f"CONFLICT TRANSCRIPT:\n{transcript_text[:2000]}...")  # Truncate for context
        if analysis_summary:
            context_parts.append(f"CONFLICT ANALYSIS:\n{analysis_summary}")
        if boyfriend_profile:
            context_parts.append(f"BOYFRIEND'S PROFILE:\n{boyfriend_profile}")
        if girlfriend_profile:
            context_parts.append(f"GIRLFRIEND'S PROFILE:\n{girlfriend_profile}")
        
        context = "\n\n".join(context_parts)
        
        # Build conversation messages
        system_message = """You are HeartSync, a compassionate AI relationship mediator. You're having a private conversation with someone who just had a conflict with their partner.

You have full context of:
- The entire conflict transcript
- Analysis of what went wrong
- Both partners' profiles and preferences

Your role:
- Listen empathetically
- Help them process their feelings
- Provide gentle, personalized guidance
- Reference specific moments from the conflict when helpful
- Be warm, understanding, and non-judgmental
- Help them understand their partner's perspective without invalidating their feelings

Keep responses conversational, supportive, and under 200 words."""
        
        messages = [{"role": "system", "content": system_message}]
        
        if context:
            messages.append({
                "role": "system",
                "content": f"CONTEXT ABOUT THIS CONFLICT:\n{context}"
            })
        
        # Add conversation history
        for msg in conversation_history[-6:]:  # Last 6 messages for context
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        # Add current message
        messages.append({
            "role": "user",
            "content": message
        })
        
        # Get HeartSync's response
        response = llm_service.chat_completion(
            messages=messages,
            temperature=0.8,
            max_tokens=300
        )
        
        logger.info(f"💬 HeartSync responded to rant for conflict {conflict_id}")
        
        return {
            "success": True,
            "response": response,
            "conflict_id": conflict_id,
            "partner_id": partner_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error handling rant: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

