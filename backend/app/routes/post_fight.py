"""
Post-fight session API endpoints
"""
import logging
import json
from fastapi import APIRouter, HTTPException, Body, BackgroundTasks
from typing import Optional, List
from datetime import datetime
from app.services.pinecone_service import pinecone_service
from app.services.embeddings_service import embeddings_service
from app.services.reranker_service import reranker_service
from app.services.s3_service import s3_service
from app.services.transcript_chunker import TranscriptChunker
from app.tools.conflict_analysis import analyze_conflict_transcript
from app.tools.repair_coaching import generate_repair_plan
from app.models.schemas import ConflictAnalysis, RepairPlan, ConflictTranscript, SpeakerSegment
from app.config import settings
from supabase import create_client, Client
from app.services.db_service import db_service

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
        
        # Generate ALL LLM calls in parallel: analysis + both repair plans
        # Repair plans can work without analysis (they use transcript + profiles)
        # This maximizes parallelism and reduces total generation time
        logger.info(f"🚀 Starting parallel LLM generation: analysis + 2 repair plans")
        analysis, repair_plan_boyfriend, repair_plan_girlfriend = await asyncio.gather(
            # Analysis generation
            analyze_conflict_transcript(
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
            ),
            # Boyfriend repair plan (works with transcript + profile, analysis optional)
            generate_repair_plan(
                conflict_id=conflict_id,
                transcript_text=transcript_text,
                partner_requesting_id="partner_a",
                relationship_id=relationship_id,
                partner_a_id=partner_a_id,
                partner_b_id=partner_b_id,
                analysis=None,  # Generated in parallel, repair plan works without it
                boyfriend_profile=boyfriend_profile,
                girlfriend_profile=girlfriend_profile
            ),
            # Girlfriend repair plan (works with transcript + profile, analysis optional)
            generate_repair_plan(
                conflict_id=conflict_id,
                transcript_text=transcript_text,
                partner_requesting_id="partner_b",
                relationship_id=relationship_id,
                partner_a_id=partner_a_id,
                partner_b_id=partner_b_id,
                analysis=None,  # Generated in parallel, repair plan works without it
                boyfriend_profile=boyfriend_profile,
                girlfriend_profile=girlfriend_profile
            )
        )
        logger.info(f"✅ All LLM calls completed in parallel: analysis + 2 repair plans")
        
        # Store analysis in AWS S3 and Database
        try:
            import json
            
            analysis_path = f"analysis/{relationship_id}/{conflict_id}_analysis.json"
            analysis_json = json.dumps(analysis.model_dump(), default=str, indent=2)
            
            # Store in S3
            s3_url = s3_service.upload_file(
                file_path=analysis_path,
                file_content=analysis_json.encode('utf-8'),
                content_type="application/json"
            )
            if s3_url:
                logger.info(f"✅ Stored analysis in S3: {analysis_path} (URL: {s3_url})")
                
                # Store metadata in database (with S3 URL/path)
                if db_service:
                    db_service.create_conflict_analysis(
                        conflict_id=conflict_id,
                        relationship_id=relationship_id,
                        analysis_path=s3_url or analysis_path  # Store S3 URL or path
                    )
                    logger.info(f"✅ Stored analysis metadata in database")
            else:
                logger.error(f"❌ Failed to upload analysis to S3: {analysis_path}")
        except Exception as e:
            logger.error(f"❌ Error storing analysis in S3: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Continue even if S3 fails
        
        # Store repair plans in Pinecone (with error handling for rate limits)
        try:
            repair_plan_text_bf = f"{repair_plan_boyfriend.apology_script} {' '.join(repair_plan_boyfriend.steps)}"
            try:
                repair_plan_embedding_bf = embeddings_service.embed_text(repair_plan_text_bf)
                repair_plan_dict_bf = repair_plan_boyfriend.model_dump()
                repair_plan_dict_bf["generated_at"] = datetime.now()
                pinecone_service.upsert_repair_plan(
                    conflict_id=f"{conflict_id}_boyfriend",
                    embedding=repair_plan_embedding_bf,
                    repair_plan_data=repair_plan_dict_bf,
                    namespace="repair_plans"
                )
            except Exception as e:
                logger.warning(f"⚠️ Failed to store boyfriend repair plan embedding (rate limit?): {e}")
            
            repair_plan_text_gf = f"{repair_plan_girlfriend.apology_script} {' '.join(repair_plan_girlfriend.steps)}"
            try:
                repair_plan_embedding_gf = embeddings_service.embed_text(repair_plan_text_gf)
                repair_plan_dict_gf = repair_plan_girlfriend.model_dump()
                repair_plan_dict_gf["generated_at"] = datetime.now()
                pinecone_service.upsert_repair_plan(
                    conflict_id=f"{conflict_id}_girlfriend",
                    embedding=repair_plan_embedding_gf,
                    repair_plan_data=repair_plan_dict_gf,
                    namespace="repair_plans"
                )
            except Exception as e:
                logger.warning(f"⚠️ Failed to store girlfriend repair plan embedding (rate limit?): {e}")
            
            logger.info(f"✅ Repair plans stored in Pinecone for {conflict_id} (both partners)")
        except Exception as e:
            logger.error(f"❌ Error storing repair plans in Pinecone: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Store repair plans in AWS S3 and Database
        try:
            import json
            
            # Store boyfriend repair plan in S3
            plan_path_bf = f"repair_plans/{relationship_id}/{conflict_id}_repair_partner_a.json"
            plan_json_bf = json.dumps(repair_plan_boyfriend.model_dump(), default=str, indent=2)
            s3_url_bf = s3_service.upload_file(
                file_path=plan_path_bf,
                file_content=plan_json_bf.encode('utf-8'),
                content_type="application/json"
            )
            if s3_url_bf:
                logger.info(f"✅ Stored boyfriend repair plan in S3: {plan_path_bf} (URL: {s3_url_bf})")
            
            # Store girlfriend repair plan in S3
            plan_path_gf = f"repair_plans/{relationship_id}/{conflict_id}_repair_partner_b.json"
            plan_json_gf = json.dumps(repair_plan_girlfriend.model_dump(), default=str, indent=2)
            s3_url_gf = s3_service.upload_file(
                file_path=plan_path_gf,
                file_content=plan_json_gf.encode('utf-8'),
                content_type="application/json"
            )
            if s3_url_gf:
                logger.info(f"✅ Stored girlfriend repair plan in S3: {plan_path_gf} (URL: {s3_url_gf})")
            
            # Store metadata in database (with S3 URLs/paths)
            if db_service:
                db_service.create_repair_plan(
                    conflict_id=conflict_id,
                    relationship_id=relationship_id,
                    partner_requesting="partner_a",
                    plan_path=s3_url_bf or plan_path_bf  # Store S3 URL or path
                )
                db_service.create_repair_plan(
                    conflict_id=conflict_id,
                    relationship_id=relationship_id,
                    partner_requesting="partner_b",
                    plan_path=s3_url_gf or plan_path_gf  # Store S3 URL or path
                )
                logger.info(f"✅ Stored repair plan metadata in database")
        except Exception as e:
            logger.error(f"❌ Error storing repair plans in S3: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Continue even if S3 fails
        
        logger.info(f"✅ Background generation complete for conflict {conflict_id}")
        
    except Exception as e:
        logger.error(f"❌ Error in background generation: {e}")
        import traceback
        logger.error(traceback.format_exc())

@router.post("/conflicts/{conflict_id}/generate-all")
async def generate_all_analysis_and_repair(
    conflict_id: str,
    request: dict = Body(...)
):
    """
    Generate analysis AND repair plan in parallel (synchronous - waits for completion)
    Returns the generated analysis and repair plans directly
    
    Request body:
    {
        "relationship_id": "id",
        "partner_a_id": "id", 
        "partner_b_id": "id"
    }
    """
    try:
        relationship_id = request.get("relationship_id", "00000000-0000-0000-0000-000000000000")
        partner_a_id = request.get("partner_a_id", "partner_a")
        partner_b_id = request.get("partner_b_id", "partner_b")
        
        logger.info(f"🚀 Starting parallel analysis and repair plan generation for {conflict_id}")
        
        # Get transcript from Pinecone (with fallback to S3)
        transcript_text = ""
        transcript_result = pinecone_service.get_by_conflict_id(
            conflict_id=conflict_id,
            namespace="transcripts"
        )
        
        duration = 0.0
        speaker_labels = {}
        
        if transcript_result and transcript_result.metadata:
            transcript_text = transcript_result.metadata.get("transcript_text", "")
            duration = transcript_result.metadata.get("duration", 0.0)
            speaker_labels = transcript_result.metadata.get("speaker_labels", {})
        else:
            # Fallback: Try to get from database/S3
            try:
                supabase_url = getattr(settings, 'SUPABASE_URL', None) or os.getenv("SUPABASE_URL")
                supabase_key = getattr(settings, 'SUPABASE_KEY', None) or os.getenv("SUPABASE_KEY")
                
                if supabase_url and supabase_key:
                    supabase: Client = create_client(supabase_url, supabase_key)
                    conflict_response = supabase.table("conflicts").select("*").eq("id", conflict_id).execute()
                    
                    if conflict_response.data and len(conflict_response.data) > 0:
                        conflict = conflict_response.data[0]
                        transcript_path = conflict.get("transcript_path")
                        
                        if transcript_path:
                            # Extract S3 key from URL if it's a full URL
                            s3_key = transcript_path
                            if s3_key.startswith(f"s3://{settings.S3_BUCKET_NAME}/"):
                                s3_key = s3_key.replace(f"s3://{settings.S3_BUCKET_NAME}/", "")
                            
                            file_response = s3_service.download_file(s3_key)
                            if file_response:
                                import json
                                transcript_data = json.loads(file_response.decode('utf-8'))
                                
                                if isinstance(transcript_data, list):
                                    transcript_lines = []
                                    for segment in transcript_data:
                                        if isinstance(segment, dict):
                                            speaker = segment.get("speaker", segment.get("speaker_name", "Speaker"))
                                            text = segment.get("text", segment.get("transcript", segment.get("message", "")))
                                            if text:
                                                transcript_lines.append(f"{speaker}: {text}")
                                    transcript_text = "\n".join(transcript_lines)
                                elif isinstance(transcript_data, dict):
                                    if "transcript_text" in transcript_data:
                                        transcript_text = transcript_data["transcript_text"]
                                    elif "segments" in transcript_data:
                                        transcript_lines = []
                                        for segment in transcript_data["segments"]:
                                            speaker = segment.get("speaker", "Speaker")
                                            text = segment.get("text", "")
                                            if text:
                                                transcript_lines.append(f"{speaker}: {text}")
                                        transcript_text = "\n".join(transcript_lines)
                                
                                duration = conflict.get("duration", 0.0)
                                speaker_labels = conflict.get("speaker_labels", {})
            except Exception as e:
                logger.warning(f"⚠️ Failed to fetch transcript from S3: {e}")
        
        if not transcript_text:
            raise HTTPException(
                status_code=404,
                detail=f"Transcript not found for conflict {conflict_id}. Please ensure the fight was properly captured."
            )
        
        logger.info(f"📝 Using transcript: {len(transcript_text)} characters")
        
        # Use RAG pipeline with reranker to get relevant profile information
        boyfriend_profile = None
        girlfriend_profile = None
        try:
            query_embedding = embeddings_service.embed_query(transcript_text)
            
            boyfriend_results = pinecone_service.query(
                query_embedding=query_embedding, top_k=5, namespace="profiles",
                filter={"relationship_id": {"$eq": relationship_id}, "pdf_type": {"$eq": "boyfriend_profile"}}
            )
            boyfriend_chunks = [match.metadata.get("extracted_text", "") for match in boyfriend_results.matches if match.metadata.get("extracted_text")]
            if boyfriend_chunks:
                reranked_bf = reranker_service.rerank(query=transcript_text[:500], documents=boyfriend_chunks, top_k=3)
                boyfriend_profile = "\n\n".join([chunk for chunk, score in reranked_bf])
                logger.info(f"✅ Retrieved {len(reranked_bf)} relevant boyfriend profile chunks via reranker")
            
            girlfriend_results = pinecone_service.query(
                query_embedding=query_embedding, top_k=5, namespace="profiles",
                filter={"relationship_id": {"$eq": relationship_id}, "pdf_type": {"$eq": "girlfriend_profile"}}
            )
            girlfriend_chunks = [match.metadata.get("extracted_text", "") for match in girlfriend_results.matches if match.metadata.get("extracted_text")]
            if girlfriend_chunks:
                reranked_gf = reranker_service.rerank(query=transcript_text[:500], documents=girlfriend_chunks, top_k=3)
                girlfriend_profile = "\n\n".join([chunk for chunk, score in reranked_gf])
                logger.info(f"✅ Retrieved {len(reranked_gf)} relevant girlfriend profile chunks via reranker")
        except Exception as e:
            logger.warning(f"⚠️ RAG retrieval failed, using transcript only: {e}")
        
        # Generate ALL LLM calls in parallel: 2 analyses (boyfriend POV + girlfriend POV) + 2 repair plans
        timestamp_now = datetime.now()
        analysis_boyfriend, analysis_girlfriend, repair_plan_boyfriend, repair_plan_girlfriend = await asyncio.gather(
            # Analysis from Boyfriend's POV (personalized)
            analyze_conflict_transcript(
            conflict_id=conflict_id,
            transcript_text=transcript_text,
            relationship_id=relationship_id,
            partner_a_id=partner_a_id,
            partner_b_id=partner_b_id,
            speaker_labels=speaker_labels,
            duration=duration,
                timestamp=timestamp_now,
                partner_id="partner_a",  # Boyfriend's perspective
                boyfriend_profile=boyfriend_profile,
                girlfriend_profile=girlfriend_profile
            ),
            # Analysis from Girlfriend's POV (personalized)
            analyze_conflict_transcript(
                conflict_id=conflict_id,
                transcript_text=transcript_text,
                relationship_id=relationship_id,
                partner_a_id=partner_a_id,
                partner_b_id=partner_b_id,
                speaker_labels=speaker_labels,
                duration=duration,
                timestamp=timestamp_now,
                partner_id="partner_b",  # Girlfriend's perspective
                boyfriend_profile=boyfriend_profile,
                girlfriend_profile=girlfriend_profile
            ),
            # Boyfriend repair plan (personalized)
            generate_repair_plan(
                conflict_id=conflict_id,
                transcript_text=transcript_text,
                partner_requesting_id="partner_a",
                relationship_id=relationship_id,
                partner_a_id=partner_a_id,
                partner_b_id=partner_b_id,
                analysis=None,  # Generated in parallel, repair plan works without it
                boyfriend_profile=boyfriend_profile,
                girlfriend_profile=girlfriend_profile
            ),
            # Girlfriend repair plan (personalized)
            generate_repair_plan(
                conflict_id=conflict_id,
                transcript_text=transcript_text,
                partner_requesting_id="partner_b",
                relationship_id=relationship_id,
                partner_a_id=partner_a_id,
                partner_b_id=partner_b_id,
                analysis=None,  # Generated in parallel, repair plan works without it
                boyfriend_profile=boyfriend_profile,
                girlfriend_profile=girlfriend_profile
            )
        )
        
        logger.info(f"✅ All LLM calls completed in parallel: 2 analyses (boyfriend + girlfriend POV) + 2 repair plans")
        
        # Store both analyses in Pinecone and S3
        try:
            import json
            
            # Store boyfriend analysis in S3
            analysis_path_bf = f"analysis/{relationship_id}/{conflict_id}_analysis_boyfriend.json"
            analysis_json_bf = json.dumps(analysis_boyfriend.model_dump(), default=str, indent=2)
            s3_url_bf = s3_service.upload_file(
                file_path=analysis_path_bf,
                file_content=analysis_json_bf.encode('utf-8'),
                content_type="application/json"
            )
            if s3_url_bf:
                logger.info(f"✅ Stored boyfriend analysis in S3: {analysis_path_bf}")
                # Store in Pinecone
                analysis_embedding_bf = embeddings_service.embed_text(analysis_boyfriend.fight_summary)
                analysis_dict_bf = analysis_boyfriend.model_dump()
                analysis_dict_bf["analyzed_at"] = datetime.now()
                analysis_dict_bf["partner_pov"] = "boyfriend"
                pinecone_service.upsert_analysis(
                    conflict_id=f"{conflict_id}_boyfriend",
                    embedding=analysis_embedding_bf,
                    analysis_data=analysis_dict_bf,
                    namespace="analysis"
                )
            
            # Store girlfriend analysis in S3
            analysis_path_gf = f"analysis/{relationship_id}/{conflict_id}_analysis_girlfriend.json"
            analysis_json_gf = json.dumps(analysis_girlfriend.model_dump(), default=str, indent=2)
            s3_url_gf = s3_service.upload_file(
                file_path=analysis_path_gf,
                file_content=analysis_json_gf.encode('utf-8'),
                content_type="application/json"
            )
            if s3_url_gf:
                logger.info(f"✅ Stored girlfriend analysis in S3: {analysis_path_gf}")
                # Store in Pinecone
                analysis_embedding_gf = embeddings_service.embed_text(analysis_girlfriend.fight_summary)
                analysis_dict_gf = analysis_girlfriend.model_dump()
                analysis_dict_gf["analyzed_at"] = datetime.now()
                analysis_dict_gf["partner_pov"] = "girlfriend"
                pinecone_service.upsert_analysis(
                    conflict_id=f"{conflict_id}_girlfriend",
                    embedding=analysis_embedding_gf,
                    analysis_data=analysis_dict_gf,
                    namespace="analysis"
                )
            
            # Store metadata in database
            if db_service:
                if s3_url_bf:
                    db_service.create_conflict_analysis(
                        conflict_id=conflict_id,
                        relationship_id=relationship_id,
                        analysis_path=s3_url_bf
                    )
                if s3_url_gf:
                    db_service.create_conflict_analysis(
                        conflict_id=conflict_id,
                        relationship_id=relationship_id,
                        analysis_path=s3_url_gf
                    )
                logger.info(f"✅ Stored both analyses metadata in database")
        except Exception as e:
            logger.error(f"❌ Error storing analyses: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Store repair plans in Pinecone and S3
        try:
            # Store boyfriend repair plan in S3
            plan_path_bf = f"repair_plans/{relationship_id}/{conflict_id}_repair_partner_a.json"
            plan_json_bf = json.dumps(repair_plan_boyfriend.model_dump(), default=str, indent=2)
            s3_url_bf = s3_service.upload_file(
                file_path=plan_path_bf,
                file_content=plan_json_bf.encode('utf-8'),
                content_type="application/json"
            )
            if s3_url_bf:
                logger.info(f"✅ Stored boyfriend repair plan in S3: {plan_path_bf}")
                if db_service:
                    db_service.create_repair_plan(
                        conflict_id=conflict_id,
                        relationship_id=relationship_id,
                        partner_requesting="partner_a",
                        plan_path=s3_url_bf
                    )
            
            # Store girlfriend repair plan in S3
            plan_path_gf = f"repair_plans/{relationship_id}/{conflict_id}_repair_partner_b.json"
            plan_json_gf = json.dumps(repair_plan_girlfriend.model_dump(), default=str, indent=2)
            s3_url_gf = s3_service.upload_file(
                file_path=plan_path_gf,
                file_content=plan_json_gf.encode('utf-8'),
                content_type="application/json"
            )
            if s3_url_gf:
                logger.info(f"✅ Stored girlfriend repair plan in S3: {plan_path_gf}")
                if db_service:
                    db_service.create_repair_plan(
                        conflict_id=conflict_id,
                        relationship_id=relationship_id,
                        partner_requesting="partner_b",
                        plan_path=s3_url_gf
                    )
            
            # Store repair plans in Pinecone
            try:
                repair_plan_text_bf = f"{repair_plan_boyfriend.apology_script} {' '.join(repair_plan_boyfriend.steps)}"
                repair_plan_embedding_bf = embeddings_service.embed_text(repair_plan_text_bf)
                pinecone_service.upsert_repair_plan(
                    conflict_id=f"{conflict_id}_boyfriend",
                    embedding=repair_plan_embedding_bf,
                    repair_plan_data=repair_plan_boyfriend.model_dump(),
                    namespace="repair_plans"
                )
                
                repair_plan_text_gf = f"{repair_plan_girlfriend.apology_script} {' '.join(repair_plan_girlfriend.steps)}"
                repair_plan_embedding_gf = embeddings_service.embed_text(repair_plan_text_gf)
                pinecone_service.upsert_repair_plan(
                    conflict_id=f"{conflict_id}_girlfriend",
                    embedding=repair_plan_embedding_gf,
                    repair_plan_data=repair_plan_girlfriend.model_dump(),
                    namespace="repair_plans"
                )
                logger.info(f"✅ Stored repair plans in Pinecone")
            except Exception as e:
                logger.warning(f"⚠️ Failed to store repair plan embeddings: {e}")
        except Exception as e:
            logger.error(f"❌ Error storing repair plans: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return {
            "success": True,
            "analysis_boyfriend": analysis_boyfriend.model_dump(),
            "analysis_girlfriend": analysis_girlfriend.model_dump(),
            "repair_plan_boyfriend": repair_plan_boyfriend.model_dump(),
            "repair_plan_girlfriend": repair_plan_girlfriend.model_dump()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating analysis and repair plans: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conflicts/{conflict_id}/generate-analysis")
async def generate_analysis_only(
    conflict_id: str,
    request: dict = Body(...)
):
    """
    Generate analysis from both perspectives (boyfriend + girlfriend POV)
    """
    try:
        relationship_id = request.get("relationship_id", "00000000-0000-0000-0000-000000000000")
        partner_a_id = request.get("partner_a_id", "partner_a")
        partner_b_id = request.get("partner_b_id", "partner_b")
        
        logger.info(f"🚀 Generating analysis for {conflict_id}")
        
        # Get transcript (same logic as generate-all)
        transcript_text = ""
        transcript_result = pinecone_service.get_by_conflict_id(
            conflict_id=conflict_id,
            namespace="transcripts"
        )
        
        duration = 0.0
        speaker_labels = {}
        
        if transcript_result and transcript_result.metadata:
            transcript_text = transcript_result.metadata.get("transcript_text", "")
            duration = transcript_result.metadata.get("duration", 0.0)
            speaker_labels = transcript_result.metadata.get("speaker_labels", {})
        else:
            # Fallback to S3
            try:
                supabase_url = getattr(settings, 'SUPABASE_URL', None) or os.getenv("SUPABASE_URL")
                supabase_key = getattr(settings, 'SUPABASE_KEY', None) or os.getenv("SUPABASE_KEY")
                
                if supabase_url and supabase_key:
                    supabase: Client = create_client(supabase_url, supabase_key)
                    conflict_response = supabase.table("conflicts").select("*").eq("id", conflict_id).execute()
                    
                    if conflict_response.data and len(conflict_response.data) > 0:
                        conflict = conflict_response.data[0]
                        transcript_path = conflict.get("transcript_path")
                        
                        if transcript_path:
                            s3_key = transcript_path
                            if s3_key.startswith(f"s3://{settings.S3_BUCKET_NAME}/"):
                                s3_key = s3_key.replace(f"s3://{settings.S3_BUCKET_NAME}/", "")
                            
                            file_response = s3_service.download_file(s3_key)
                            if file_response:
                                transcript_data = json.loads(file_response.decode('utf-8'))
                                
                                if isinstance(transcript_data, list):
                                    transcript_lines = []
                                    for segment in transcript_data:
                                        if isinstance(segment, dict):
                                            speaker = segment.get("speaker", segment.get("speaker_name", "Speaker"))
                                            text = segment.get("text", segment.get("transcript", segment.get("message", "")))
                                            if text:
                                                transcript_lines.append(f"{speaker}: {text}")
                                    transcript_text = "\n".join(transcript_lines)
                                elif isinstance(transcript_data, dict):
                                    if "transcript_text" in transcript_data:
                                        transcript_text = transcript_data["transcript_text"]
                                    elif "segments" in transcript_data:
                                        transcript_lines = []
                                        for segment in transcript_data["segments"]:
                                            speaker = segment.get("speaker", "Speaker")
                                            text = segment.get("text", "")
                                            if text:
                                                transcript_lines.append(f"{speaker}: {text}")
                                        transcript_text = "\n".join(transcript_lines)
                                
                                duration = conflict.get("duration", 0.0)
                                speaker_labels = conflict.get("speaker_labels", {})
            except Exception as e:
                logger.warning(f"⚠️ Failed to fetch transcript from S3: {e}")
        
        if not transcript_text:
            raise HTTPException(
                status_code=404,
                detail=f"Transcript not found for conflict {conflict_id}"
            )
        
        # Get profiles via RAG (OPTIONAL - skip if slow, can be done in parallel or skipped)
        boyfriend_profile = None
        girlfriend_profile = None
        # Skip RAG for faster analysis - profiles are optional
        # Uncomment below if you want profile-based personalization (adds ~2-3s latency)
        # try:
        #     query_embedding = embeddings_service.embed_query(transcript_text)
        #     boyfriend_results = pinecone_service.query(...)
        #     girlfriend_results = pinecone_service.query(...)
        # except Exception as e:
        #     logger.warning(f"⚠️ RAG retrieval skipped for speed: {e}")
        
        # Generate both analyses in parallel (FAST - just LLM calls)
        timestamp_now = datetime.now()
        analysis_boyfriend, analysis_girlfriend = await asyncio.gather(
            analyze_conflict_transcript(
                conflict_id=conflict_id,
                transcript_text=transcript_text,
                relationship_id=relationship_id,
                partner_a_id=partner_a_id,
                partner_b_id=partner_b_id,
                speaker_labels=speaker_labels,
                duration=duration,
                timestamp=timestamp_now,
                partner_id="partner_a",
                boyfriend_profile=boyfriend_profile,
                girlfriend_profile=girlfriend_profile
            ),
            analyze_conflict_transcript(
                conflict_id=conflict_id,
                transcript_text=transcript_text,
                relationship_id=relationship_id,
                partner_a_id=partner_a_id,
                partner_b_id=partner_b_id,
                speaker_labels=speaker_labels,
                duration=duration,
                timestamp=timestamp_now,
                partner_id="partner_b",
                boyfriend_profile=boyfriend_profile,
                girlfriend_profile=girlfriend_profile
            )
        )
        
        # Store analyses
        try:
            analysis_path_bf = f"analysis/{relationship_id}/{conflict_id}_analysis_boyfriend.json"
            analysis_json_bf = json.dumps(analysis_boyfriend.model_dump(), default=str, indent=2)
            s3_url_bf = s3_service.upload_file(
                file_path=analysis_path_bf,
                file_content=analysis_json_bf.encode('utf-8'),
                content_type="application/json"
            )
            if s3_url_bf:
                analysis_embedding_bf = embeddings_service.embed_text(analysis_boyfriend.fight_summary)
                analysis_dict_bf = analysis_boyfriend.model_dump()
                analysis_dict_bf["analyzed_at"] = datetime.now()
                analysis_dict_bf["partner_pov"] = "boyfriend"
                pinecone_service.upsert_analysis(
                    conflict_id=f"{conflict_id}_boyfriend",
                    embedding=analysis_embedding_bf,
                    analysis_data=analysis_dict_bf,
                    namespace="analysis"
                )
            
            analysis_path_gf = f"analysis/{relationship_id}/{conflict_id}_analysis_girlfriend.json"
            analysis_json_gf = json.dumps(analysis_girlfriend.model_dump(), default=str, indent=2)
            s3_url_gf = s3_service.upload_file(
                file_path=analysis_path_gf,
                file_content=analysis_json_gf.encode('utf-8'),
                content_type="application/json"
            )
            if s3_url_gf:
                analysis_embedding_gf = embeddings_service.embed_text(analysis_girlfriend.fight_summary)
                analysis_dict_gf = analysis_girlfriend.model_dump()
                analysis_dict_gf["analyzed_at"] = datetime.now()
                analysis_dict_gf["partner_pov"] = "girlfriend"
                pinecone_service.upsert_analysis(
                    conflict_id=f"{conflict_id}_girlfriend",
                    embedding=analysis_embedding_gf,
                    analysis_data=analysis_dict_gf,
                    namespace="analysis"
                )
            
            if db_service:
                if s3_url_bf:
                    db_service.create_conflict_analysis(
                        conflict_id=conflict_id,
                        relationship_id=relationship_id,
                        analysis_path=s3_url_bf
                    )
                if s3_url_gf:
                    db_service.create_conflict_analysis(
                        conflict_id=conflict_id,
                        relationship_id=relationship_id,
                        analysis_path=s3_url_gf
                    )
        except Exception as e:
            logger.error(f"❌ Error storing analyses: {e}")
        
        return {
            "success": True,
            "analysis_boyfriend": analysis_boyfriend.model_dump(),
            "analysis_girlfriend": analysis_girlfriend.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conflicts/{conflict_id}/generate-repair-plans")
async def generate_repair_plans_only(
    conflict_id: str,
    request: dict = Body(...)
):
    """
    Generate repair plans for both perspectives (boyfriend + girlfriend)
    """
    try:
        relationship_id = request.get("relationship_id", "00000000-0000-0000-0000-000000000000")
        partner_a_id = request.get("partner_a_id", "partner_a")
        partner_b_id = request.get("partner_b_id", "partner_b")
        
        logger.info(f"🚀 Generating repair plans for {conflict_id}")
        
        # Get transcript (same logic)
        transcript_text = ""
        transcript_result = pinecone_service.get_by_conflict_id(
            conflict_id=conflict_id,
            namespace="transcripts"
        )
        
        duration = 0.0
        speaker_labels = {}
        
        if transcript_result and transcript_result.metadata:
            transcript_text = transcript_result.metadata.get("transcript_text", "")
            duration = transcript_result.metadata.get("duration", 0.0)
            speaker_labels = transcript_result.metadata.get("speaker_labels", {})
        else:
            # Fallback to S3
            try:
                supabase_url = getattr(settings, 'SUPABASE_URL', None) or os.getenv("SUPABASE_URL")
                supabase_key = getattr(settings, 'SUPABASE_KEY', None) or os.getenv("SUPABASE_KEY")
                
                if supabase_url and supabase_key:
                    supabase: Client = create_client(supabase_url, supabase_key)
                    conflict_response = supabase.table("conflicts").select("*").eq("id", conflict_id).execute()
                    
                    if conflict_response.data and len(conflict_response.data) > 0:
                        conflict = conflict_response.data[0]
                        transcript_path = conflict.get("transcript_path")
                        
                        if transcript_path:
                            s3_key = transcript_path
                            if s3_key.startswith(f"s3://{settings.S3_BUCKET_NAME}/"):
                                s3_key = s3_key.replace(f"s3://{settings.S3_BUCKET_NAME}/", "")
                            
                            file_response = s3_service.download_file(s3_key)
                            if file_response:
                                transcript_data = json.loads(file_response.decode('utf-8'))
                                
                                if isinstance(transcript_data, list):
                                    transcript_lines = []
                                    for segment in transcript_data:
                                        if isinstance(segment, dict):
                                            speaker = segment.get("speaker", segment.get("speaker_name", "Speaker"))
                                            text = segment.get("text", segment.get("transcript", segment.get("message", "")))
                                            if text:
                                                transcript_lines.append(f"{speaker}: {text}")
                                    transcript_text = "\n".join(transcript_lines)
                                elif isinstance(transcript_data, dict):
                                    if "transcript_text" in transcript_data:
                                        transcript_text = transcript_data["transcript_text"]
                                    elif "segments" in transcript_data:
                                        transcript_lines = []
                                        for segment in transcript_data["segments"]:
                                            speaker = segment.get("speaker", "Speaker")
                                            text = segment.get("text", "")
                                            if text:
                                                transcript_lines.append(f"{speaker}: {text}")
                                        transcript_text = "\n".join(transcript_lines)
                                
                                duration = conflict.get("duration", 0.0)
                                speaker_labels = conflict.get("speaker_labels", {})
            except Exception as e:
                logger.warning(f"⚠️ Failed to fetch transcript from S3: {e}")
        
        if not transcript_text:
            raise HTTPException(
                status_code=404,
                detail=f"Transcript not found for conflict {conflict_id}"
            )
        
        # Get profiles via RAG
        boyfriend_profile = None
        girlfriend_profile = None
        try:
            query_embedding = embeddings_service.embed_query(transcript_text)
            
            boyfriend_results = pinecone_service.query(
                query_embedding=query_embedding, top_k=5, namespace="profiles",
                filter={"relationship_id": {"$eq": relationship_id}, "pdf_type": {"$eq": "boyfriend_profile"}}
            )
            boyfriend_chunks = [match.metadata.get("extracted_text", "") for match in boyfriend_results.matches if match.metadata.get("extracted_text")]
            if boyfriend_chunks:
                reranked_bf = reranker_service.rerank(query=transcript_text[:500], documents=boyfriend_chunks, top_k=3)
                boyfriend_profile = "\n\n".join([chunk for chunk, score in reranked_bf])
            
            girlfriend_results = pinecone_service.query(
                query_embedding=query_embedding, top_k=5, namespace="profiles",
                filter={"relationship_id": {"$eq": relationship_id}, "pdf_type": {"$eq": "girlfriend_profile"}}
            )
            girlfriend_chunks = [match.metadata.get("extracted_text", "") for match in girlfriend_results.matches if match.metadata.get("extracted_text")]
            if girlfriend_chunks:
                reranked_gf = reranker_service.rerank(query=transcript_text[:500], documents=girlfriend_chunks, top_k=3)
                girlfriend_profile = "\n\n".join([chunk for chunk, score in reranked_gf])
        except Exception as e:
            logger.warning(f"⚠️ RAG retrieval failed: {e}")
        
        # Generate both repair plans in parallel
        repair_plan_boyfriend, repair_plan_girlfriend = await asyncio.gather(
            generate_repair_plan(
                conflict_id=conflict_id,
                transcript_text=transcript_text,
                partner_requesting_id="partner_a",
                relationship_id=relationship_id,
                partner_a_id=partner_a_id,
                partner_b_id=partner_b_id,
                analysis=None,
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
                analysis=None,
                boyfriend_profile=boyfriend_profile,
                girlfriend_profile=girlfriend_profile
            )
        )
        
        # Store repair plans
        try:
            plan_path_bf = f"repair_plans/{relationship_id}/{conflict_id}_repair_partner_a.json"
            plan_json_bf = json.dumps(repair_plan_boyfriend.model_dump(), default=str, indent=2)
            s3_url_bf = s3_service.upload_file(
                file_path=plan_path_bf,
                file_content=plan_json_bf.encode('utf-8'),
                content_type="application/json"
            )
            if s3_url_bf and db_service:
                db_service.create_repair_plan(
                    conflict_id=conflict_id,
                    relationship_id=relationship_id,
                    partner_requesting="partner_a",
                    plan_path=s3_url_bf
                )
            
            plan_path_gf = f"repair_plans/{relationship_id}/{conflict_id}_repair_partner_b.json"
            plan_json_gf = json.dumps(repair_plan_girlfriend.model_dump(), default=str, indent=2)
            s3_url_gf = s3_service.upload_file(
                file_path=plan_path_gf,
                file_content=plan_json_gf.encode('utf-8'),
                content_type="application/json"
            )
            if s3_url_gf and db_service:
                db_service.create_repair_plan(
                    conflict_id=conflict_id,
                    relationship_id=relationship_id,
                    partner_requesting="partner_b",
                    plan_path=s3_url_gf
                )
            
            # Store in Pinecone
            repair_plan_text_bf = f"{repair_plan_boyfriend.apology_script} {' '.join(repair_plan_boyfriend.action_steps)}"
            repair_plan_embedding_bf = embeddings_service.embed_text(repair_plan_text_bf)
            pinecone_service.upsert_repair_plan(
                conflict_id=f"{conflict_id}_boyfriend",
                embedding=repair_plan_embedding_bf,
                repair_plan_data=repair_plan_boyfriend.model_dump(),
                namespace="repair_plans"
            )
            
            repair_plan_text_gf = f"{repair_plan_girlfriend.apology_script} {' '.join(repair_plan_girlfriend.action_steps)}"
            repair_plan_embedding_gf = embeddings_service.embed_text(repair_plan_text_gf)
            pinecone_service.upsert_repair_plan(
                conflict_id=f"{conflict_id}_girlfriend",
                embedding=repair_plan_embedding_gf,
                repair_plan_data=repair_plan_girlfriend.model_dump(),
                namespace="repair_plans"
            )
        except Exception as e:
            logger.error(f"❌ Error storing repair plans: {e}")
        
        return {
            "success": True,
            "repair_plan_boyfriend": repair_plan_boyfriend.model_dump(),
            "repair_plan_girlfriend": repair_plan_girlfriend.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating repair plans: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        
        # 1. Generate embedding and store in Pinecone (vector database)
        try:
            embedding = embeddings_service.embed_text(transcript_text)
            pinecone_service.upsert_transcript(
                conflict_id=conflict_id,
                embedding=embedding,
                transcript_data=conflict_transcript.model_dump(),
                namespace="transcripts"
            )
            logger.info(f"✅ Stored transcript for conflict {conflict_id} in Pinecone (vector embeddings)")
        except Exception as e:
            logger.error(f"❌ Error storing transcript in Pinecone: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Continue even if Pinecone fails - we still want Supabase storage
        
        # 1b. Chunk transcript and store chunks in Pinecone for RAG
        try:
            chunker = TranscriptChunker(chunk_size=1000, chunk_overlap=200)
            chunks = chunker.chunk_transcript(
                transcript_text=transcript_text,
                conflict_id=conflict_id,
                relationship_id=relationship_id,
                timestamp=conflict_transcript.timestamp.isoformat() if hasattr(conflict_transcript.timestamp, 'isoformat') else str(conflict_transcript.timestamp)
            )
            
            if chunks:
                # Generate embeddings for all chunks
                chunk_texts = [chunk["content"] for chunk in chunks]
                chunk_embeddings = embeddings_service.embed_batch(chunk_texts)
                
                # Store chunks in Pinecone
                pinecone_service.upsert_transcript_chunks(
                    chunks=chunks,
                    embeddings=chunk_embeddings,
                    namespace="transcript_chunks"
                )
                logger.info(f"✅ Stored {len(chunks)} transcript chunks for conflict {conflict_id} in Pinecone")
            else:
                logger.warning(f"⚠️ No chunks created for conflict {conflict_id}")
        except Exception as e:
            logger.error(f"❌ Error chunking and storing transcript chunks: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Continue even if chunking fails - full transcript is already stored
        
        # 2. Store raw transcript in AWS S3
        file_path = None
        s3_url = None
        try:
            file_path = f"transcripts/{relationship_id}/{conflict_id}.json"
            
            # Convert transcript_lines to JSON format matching ConflictManager
            transcript_json = json.dumps(transcript_lines, indent=2)
            
            # Upload to S3
            s3_url = s3_service.upload_file(
                file_path=file_path,
                file_content=transcript_json.encode('utf-8'),
                content_type="application/json"
            )
            if s3_url:
                logger.info(f"✅ Stored transcript for conflict {conflict_id} in S3: {file_path} (URL: {s3_url})")
                
                # Update conflict record with S3 path/URL using db_service (bypasses RLS)
                try:
                    if db_service:
                        # First, ensure conflict exists (create if it doesn't)
                        try:
                            db_service.create_conflict(
                                conflict_id=conflict_id,
                                relationship_id=relationship_id,
                                status="completed"
                            )
                        except Exception:
                            pass  # Conflict might already exist, that's fine
                        
                        # Update conflict with transcript path and metadata
                        db_service.update_conflict(
                            conflict_id=conflict_id,
                            status="completed",
                            transcript_path=s3_url or file_path,
                            metadata={"utterance_count": len(transcript_lines)}
                        )
                        logger.info(f"✅ Updated conflict record with transcript_path using db_service")
                    else:
                        # Fallback to Supabase
                        from supabase import create_client, Client
                        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                        supabase.table("conflicts").update({
                            "transcript_path": s3_url or file_path,
                            "metadata": {"utterance_count": len(transcript_lines)},
                            "status": "completed"
                        }).eq("id", conflict_id).execute()
                        logger.info(f"✅ Updated conflict record with transcript_path using Supabase")
                except Exception as db_error:
                    logger.warning(f"⚠️ Could not update conflict record: {db_error}")
                    import traceback
                    logger.error(traceback.format_exc())
            else:
                logger.error(f"❌ Failed to upload transcript to S3: {file_path}")
                
        except Exception as e:
            logger.error(f"❌ Error storing transcript in S3: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Continue even if S3 fails - Pinecone storage is primary
        
        # 3. Trigger background generation of analysis and repair plan
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

@router.post("/conflicts/{conflict_id}/generate-all")
async def generate_analysis_and_repair_plans(
    conflict_id: str,
    request: dict = Body(...)
):
    """
    Generate both analysis and repair plans in parallel for a conflict.
    Uses profiles to personalize suggestions for each partner.
    
    Returns:
    {
        "success": True,
        "analysis": {...},
        "repair_plan_boyfriend": {...},
        "repair_plan_girlfriend": {...}
    }
    """
    try:
        # Initialize Supabase client
        supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        # Get conflict and transcript
        conflict_response = supabase_client.table("conflicts").select("*").eq("id", conflict_id).execute()
        if not conflict_response.data:
            raise HTTPException(status_code=404, detail=f"Conflict {conflict_id} not found")
        
        conflict = conflict_response.data[0]
        relationship_id = conflict.get("relationship_id", "00000000-0000-0000-0000-000000000000")
        
        # Get transcript from Pinecone or S3
        transcript_text = ""
        transcript_result = pinecone_service.get_by_conflict_id(
            conflict_id=conflict_id,
            namespace="transcripts"
        )
        
        if transcript_result and transcript_result.metadata:
            transcript_text = transcript_result.metadata.get("transcript_text", "")
        
        if not transcript_text:
            # Fallback to S3
            transcript_path = conflict.get("transcript_path")
            if transcript_path:
                try:
                    # Extract S3 key
                    if transcript_path.startswith("s3://"):
                        s3_key = transcript_path.replace(f"s3://{settings.S3_BUCKET_NAME}/", "")
                    else:
                        s3_key = transcript_path
                    
                    from app.services.s3_service import s3_service
                    file_response = s3_service.download_file(s3_key)
                    if file_response:
                        import json
                        transcript_data = json.loads(file_response.decode('utf-8'))
                        if isinstance(transcript_data, list):
                            transcript_lines = []
                            for segment in transcript_data:
                                if isinstance(segment, dict):
                                    speaker = segment.get("speaker", "Speaker")
                                    text = segment.get("text", "")
                                    if text:
                                        transcript_lines.append(f"{speaker}: {text}")
                            transcript_text = "\n".join(transcript_lines)
                except Exception as e:
                    logger.error(f"Error fetching transcript from S3: {e}")
        
        if not transcript_text:
            raise HTTPException(status_code=400, detail="Transcript not found for this conflict")
        
        # Get profiles via RAG
        boyfriend_profile = None
        girlfriend_profile = None
        try:
            query_embedding = embeddings_service.embed_query(transcript_text)
            
            # Search boyfriend profile
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
            
            # Search girlfriend profile
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
            logger.warning(f"RAG retrieval failed: {e}")
        
        # Generate ALL LLM calls in parallel: analysis + both repair plans
        partner_a_id = "partner_a"
        partner_b_id = "partner_b"
        speaker_labels = {}
        duration = 0.0
        timestamp_now = datetime.now()
        
        # Generate analysis and both repair plans ALL in parallel
        # Repair plans can work without analysis (they'll use transcript + profiles)
        # Analysis will be available for repair plans to reference if needed
        analysis, repair_plan_boyfriend, repair_plan_girlfriend = await asyncio.gather(
            # Analysis generation
            analyze_conflict_transcript(
                conflict_id=conflict_id,
                transcript_text=transcript_text,
                relationship_id=relationship_id,
                partner_a_id=partner_a_id,
                partner_b_id=partner_b_id,
                speaker_labels=speaker_labels,
                duration=duration,
                timestamp=timestamp_now,
                partner_id=None,
                boyfriend_profile=boyfriend_profile,
                girlfriend_profile=girlfriend_profile
            ),
            # Boyfriend repair plan (will work without analysis, using transcript + profile)
            generate_repair_plan(
                conflict_id=conflict_id,
                transcript_text=transcript_text,
                partner_requesting_id="partner_a",
                relationship_id=relationship_id,
                partner_a_id=partner_a_id,
                partner_b_id=partner_b_id,
                analysis=None,  # Will be generated in parallel, repair plan can work without it
                boyfriend_profile=boyfriend_profile,
                girlfriend_profile=girlfriend_profile
            ),
            # Girlfriend repair plan (will work without analysis, using transcript + profile)
            generate_repair_plan(
                conflict_id=conflict_id,
                transcript_text=transcript_text,
                partner_requesting_id="partner_b",
                relationship_id=relationship_id,
                partner_a_id=partner_a_id,
                partner_b_id=partner_b_id,
                analysis=None,  # Will be generated in parallel, repair plan can work without it
                boyfriend_profile=boyfriend_profile,
                girlfriend_profile=girlfriend_profile
            )
        )
        
        logger.info(f"✅ All LLM calls completed in parallel: 2 analyses (boyfriend + girlfriend POV) + 2 repair plans")
        
        # Store both analyses in Pinecone and S3
        try:
            import json
            
            # Store boyfriend analysis in S3
            analysis_path_bf = f"analysis/{relationship_id}/{conflict_id}_analysis_boyfriend.json"
            analysis_json_bf = json.dumps(analysis_boyfriend.model_dump(), default=str, indent=2)
            s3_url_bf = s3_service.upload_file(
                file_path=analysis_path_bf,
                file_content=analysis_json_bf.encode('utf-8'),
                content_type="application/json"
            )
            if s3_url_bf:
                logger.info(f"✅ Stored boyfriend analysis in S3: {analysis_path_bf}")
                # Store in Pinecone
                analysis_embedding_bf = embeddings_service.embed_text(analysis_boyfriend.fight_summary)
                analysis_dict_bf = analysis_boyfriend.model_dump()
                analysis_dict_bf["analyzed_at"] = datetime.now()
                analysis_dict_bf["partner_pov"] = "boyfriend"
                pinecone_service.upsert_analysis(
                    conflict_id=f"{conflict_id}_boyfriend",
                    embedding=analysis_embedding_bf,
                    analysis_data=analysis_dict_bf,
                    namespace="analysis"
                )
            
            # Store girlfriend analysis in S3
            analysis_path_gf = f"analysis/{relationship_id}/{conflict_id}_analysis_girlfriend.json"
            analysis_json_gf = json.dumps(analysis_girlfriend.model_dump(), default=str, indent=2)
            s3_url_gf = s3_service.upload_file(
                file_path=analysis_path_gf,
                file_content=analysis_json_gf.encode('utf-8'),
                content_type="application/json"
            )
            if s3_url_gf:
                logger.info(f"✅ Stored girlfriend analysis in S3: {analysis_path_gf}")
                # Store in Pinecone
                analysis_embedding_gf = embeddings_service.embed_text(analysis_girlfriend.fight_summary)
                analysis_dict_gf = analysis_girlfriend.model_dump()
                analysis_dict_gf["analyzed_at"] = datetime.now()
                analysis_dict_gf["partner_pov"] = "girlfriend"
                pinecone_service.upsert_analysis(
                    conflict_id=f"{conflict_id}_girlfriend",
                    embedding=analysis_embedding_gf,
                    analysis_data=analysis_dict_gf,
                    namespace="analysis"
                )
            
            # Store metadata in database
            if db_service:
                if s3_url_bf:
                    db_service.create_conflict_analysis(
                        conflict_id=conflict_id,
                        relationship_id=relationship_id,
                        analysis_path=s3_url_bf
                    )
                if s3_url_gf:
                    db_service.create_conflict_analysis(
                        conflict_id=conflict_id,
                        relationship_id=relationship_id,
                        analysis_path=s3_url_gf
                    )
                logger.info(f"✅ Stored both analyses metadata in database")
        except Exception as e:
            logger.error(f"❌ Error storing analyses: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Store repair plans in Pinecone and S3 (existing code continues...)
        
        return {
            "success": True,
            "analysis_boyfriend": analysis_boyfriend.model_dump(),
            "analysis_girlfriend": analysis_girlfriend.model_dump(),
            "repair_plan_boyfriend": repair_plan_boyfriend.model_dump(),
            "repair_plan_girlfriend": repair_plan_girlfriend.model_dump()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating analysis and repair plans: {e}")
        import traceback
        logger.error(traceback.format_exc())
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

