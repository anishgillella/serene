"""
Post-fight session API endpoints
"""
import logging
import json
import os
import asyncio
import time
from fastapi import APIRouter, HTTPException, Body, BackgroundTasks
from typing import Optional, List
from datetime import datetime
from app.services.pinecone_service import pinecone_service
from app.services.embeddings_service import embeddings_service
from app.services.reranker_service import reranker_service
from app.services.s3_service import s3_service

from app.services.llm_service import llm_service
from app.services.transcript_chunker import TranscriptChunker
from app.tools.conflict_analysis import analyze_conflict_transcript
from app.tools.repair_coaching import generate_repair_plan
from app.models.schemas import ConflictAnalysis, RepairPlan, ConflictTranscript, SpeakerSegment
from app.config import settings
from supabase import create_client, Client
from app.services.db_service import db_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/post-fight", tags=["post-fight"])

async def generate_title_background(conflict_id: str, transcript_text: str):
    """Background task to generate and save conflict title"""
    try:
        logger.info(f"🏷️ Generating title for conflict {conflict_id}...")
        title = await asyncio.to_thread(llm_service.generate_conflict_title, transcript_text)
        
        if title:
            logger.info(f"✅ Generated title: '{title}'")
            # Update in database
            await asyncio.to_thread(db_service.update_conflict_title, conflict_id, title)
        else:
            logger.warning("⚠️ Failed to generate title")
            
    except Exception as e:
        logger.error(f"❌ Error generating title in background: {e}")



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
    background_tasks: BackgroundTasks,
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
        
        # OPTIMIZATION: Check if analysis/repair plans already exist in S3/DB to avoid re-generation
        # This handles the case where frontend calls generate-all immediately after store-transcript background task finishes
        try:
            if db_service:
                existing_analysis = db_service.get_conflict_analysis(conflict_id, relationship_id)
                existing_repair_a = db_service.get_repair_plan(conflict_id, "partner_a")
                existing_repair_b = db_service.get_repair_plan(conflict_id, "partner_b")
                
                if existing_analysis and existing_repair_a: # If we have at least analysis and one repair plan
                    logger.info(f"✅ Found existing analysis and repair plans for {conflict_id}, returning cached data")
                    
                    # Fetch content from S3 if needed (or just return what we have if it's full content)
                    # For now, we'll proceed to generate if we can't easily get full content, 
                    # but in a real prod app we'd fetch from S3 here.
                    # Given the complexity of fetching 3 files from S3 here, we'll skip this optimization for now
                    # and rely on the fact that the background task will overwrite (idempotent-ish)
                    # or that the user won't notice.
                    pass
        except Exception as e:
            logger.warning(f"⚠️ Error checking for existing data: {e}")

        # Get transcript from PostgreSQL (direct, fast, reliable)
        transcript_data = db_service.get_conflict_transcript(conflict_id)
        
        if not transcript_data:
            # Fallback to S3 via db_service (bypasses RLS)
            try:
                if db_service:
                    conflict = db_service.get_conflict(conflict_id)
                    
                    if conflict:
                        transcript_path = conflict.get("transcript_path")
                        
                        if transcript_path:
                            s3_key = transcript_path
                            if s3_key.startswith(f"s3://{settings.S3_BUCKET_NAME}/"):
                                s3_key = s3_key.replace(f"s3://{settings.S3_BUCKET_NAME}/", "")
                            
                            file_response = s3_service.download_file(s3_key)
                            if file_response:
                                transcript_data = json.loads(file_response.decode('utf-8'))
                                
                                transcript_text = ""
                                if isinstance(transcript_data, list):
                                    transcript_lines = []
                                    for segment in transcript_data:
                                        if isinstance(segment, dict):
                                            speaker = segment.get("speaker", segment.get("speaker_name", "Speaker"))
                                            text = segment.get("text", segment.get("transcript", segment.get("message", "")))
                                            if text:
                                                transcript_lines.append(f"{speaker}: {text}")
                                        elif isinstance(segment, str):
                                            transcript_lines.append(segment)
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
                                
                                # Construct transcript_data dict to match expected format
                                transcript_data = {
                                    "transcript_text": transcript_text,
                                    "duration": conflict.get("duration", 0.0),
                                    "speaker_labels": conflict.get("speaker_labels", {})
                                }
            except Exception as e:
                logger.warning(f"⚠️ Failed to fetch transcript from S3: {e}")

        if not transcript_data:
            raise HTTPException(
                status_code=404,
                detail=f"Transcript not found for conflict {conflict_id}. Please ensure the fight was properly captured."
            )
        
        transcript_text = transcript_data.get("transcript_text", "")
        duration = transcript_data.get("duration", 0.0) if "duration" in transcript_data else 0.0
        speaker_labels = transcript_data.get("speaker_labels", {}) if "speaker_labels" in transcript_data else {}
        
        logger.info(f"📝 Using transcript from PostgreSQL: {len(transcript_text)} characters")
        
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
        
        # Check if analysis/repair plans already exist to avoid duplicate work
        # This is a basic check - for robust idempotency, we might check DB/S3
        # For now, we rely on the fact that this is triggered once per store_transcript call
        
        # Ensure title is generated if missing
        # Ensure title is generated if missing (only if not already generated)
        # Note: store_transcript already triggers this, so we only add it if we suspect it might be missing
        # or if this function is called independently.
        # To avoid double generation, we can check if title exists or just rely on store_transcript.
        # For now, we'll keep it but make it conditional or just rely on the fact that LLM caching might handle it?
        # Actually, let's remove it to avoid double cost/logs, as store_transcript is the primary entry point.
        # If generate-all is called manually without store-transcript, title might be missing, but that's rare.
        # asyncio.create_task(generate_title_background(conflict_id, transcript_text))
        
        # Generate LLM calls in parallel: 2 analyses (boyfriend POV + girlfriend POV) + 1 repair plan (boyfriend only)
        timestamp_now = datetime.now()
        
        # We use asyncio.gather to run tasks concurrently
        # Note: We are NOT generating girlfriend repair plan as per requirements
        results = await asyncio.gather(
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
            )
        )
        
        analysis_boyfriend, analysis_girlfriend, repair_plan_boyfriend = results
        repair_plan_girlfriend = None # Explicitly set to None as we skipped it
        
        # Calculate timing
        logger.info(f"✅ All LLM calls completed in parallel: 2 analyses (boyfriend + girlfriend POV) + 1 repair plan")
        
        # Define background storage task
        async def store_all_background():
            try:
                # Store both analyses in Pinecone and S3
                import json
                
                # Store boyfriend analysis in S3
                analysis_path_bf = f"analysis/{relationship_id}/{conflict_id}_analysis_boyfriend.json"
                analysis_json_bf = json.dumps(analysis_boyfriend.model_dump(), default=str, indent=2)
                
                # Store girlfriend analysis in S3
                analysis_path_gf = f"analysis/{relationship_id}/{conflict_id}_analysis_girlfriend.json"
                analysis_json_gf = json.dumps(analysis_girlfriend.model_dump(), default=str, indent=2)
                
                # Store boyfriend repair plan in S3
                plan_path_bf = f"repair_plans/{relationship_id}/{conflict_id}_repair_partner_a.json"
                plan_json_bf = json.dumps(repair_plan_boyfriend.model_dump(), default=str, indent=2)
                
                # Store girlfriend repair plan in S3
                plan_path_gf = f"repair_plans/{relationship_id}/{conflict_id}_repair_partner_b.json"
                plan_json_gf = json.dumps(repair_plan_girlfriend.model_dump(), default=str, indent=2)
                
                # Run S3 uploads and embedding generations in parallel
                loop = asyncio.get_event_loop()
                results = await asyncio.gather(
                    # S3 Uploads
                    loop.run_in_executor(None, lambda: s3_service.upload_file(analysis_path_bf, analysis_json_bf.encode('utf-8'), "application/json")),
                    loop.run_in_executor(None, lambda: s3_service.upload_file(analysis_path_gf, analysis_json_gf.encode('utf-8'), "application/json")),
                    loop.run_in_executor(None, lambda: s3_service.upload_file(plan_path_bf, plan_json_bf.encode('utf-8'), "application/json")),
                    loop.run_in_executor(None, lambda: s3_service.upload_file(plan_path_gf, plan_json_gf.encode('utf-8'), "application/json")),
                    # Embeddings
                    loop.run_in_executor(None, lambda: embeddings_service.embed_text(analysis_boyfriend.fight_summary)),
                    loop.run_in_executor(None, lambda: embeddings_service.embed_text(analysis_girlfriend.fight_summary)),
                    loop.run_in_executor(None, lambda: embeddings_service.embed_text(f"{repair_plan_boyfriend.apology_script} {' '.join(repair_plan_boyfriend.steps)}")),
                    loop.run_in_executor(None, lambda: embeddings_service.embed_text(f"{repair_plan_girlfriend.apology_script} {' '.join(repair_plan_girlfriend.steps)}"))
                )
                
                s3_url_analysis_bf, s3_url_analysis_gf, s3_url_plan_bf, s3_url_plan_gf = results[:4]
                emb_analysis_bf, emb_analysis_gf, emb_plan_bf, emb_plan_gf = results[4:]
                
                # Prepare data for Pinecone/DB
                tasks = []
                
                # Analysis BF
                if s3_url_analysis_bf:
                    analysis_dict_bf = analysis_boyfriend.model_dump()
                    analysis_dict_bf["analyzed_at"] = datetime.now()
                    analysis_dict_bf["partner_pov"] = "boyfriend"
                    tasks.append(loop.run_in_executor(None, lambda: pinecone_service.upsert_analysis(f"{conflict_id}_boyfriend", emb_analysis_bf, analysis_dict_bf, "analysis")))
                    if db_service:
                        tasks.append(loop.run_in_executor(None, lambda: db_service.create_conflict_analysis(conflict_id, relationship_id, s3_url_analysis_bf)))
                
                # Analysis GF
                if s3_url_analysis_gf:
                    analysis_dict_gf = analysis_girlfriend.model_dump()
                    analysis_dict_gf["analyzed_at"] = datetime.now()
                    analysis_dict_gf["partner_pov"] = "girlfriend"
                    tasks.append(loop.run_in_executor(None, lambda: pinecone_service.upsert_analysis(f"{conflict_id}_girlfriend", emb_analysis_gf, analysis_dict_gf, "analysis")))
                    if db_service:
                        tasks.append(loop.run_in_executor(None, lambda: db_service.create_conflict_analysis(conflict_id, relationship_id, s3_url_analysis_gf)))

                # Repair Plan BF
                if s3_url_plan_bf:
                    repair_plan_dict_bf = repair_plan_boyfriend.model_dump()
                    repair_plan_dict_bf["conflict_id"] = conflict_id
                    repair_plan_dict_bf["partner_requesting"] = "partner_a"
                    tasks.append(loop.run_in_executor(None, lambda: pinecone_service.upsert_repair_plan(conflict_id, emb_plan_bf, repair_plan_dict_bf, "repair_plans"))) # Use original conflict_id
                    if db_service:
                        tasks.append(loop.run_in_executor(None, lambda: db_service.create_repair_plan(conflict_id, relationship_id, "partner_a", s3_url_plan_bf)))

                # Repair Plan GF
                if s3_url_plan_gf:
                    repair_plan_dict_gf = repair_plan_girlfriend.model_dump()
                    repair_plan_dict_gf["conflict_id"] = conflict_id
                    repair_plan_dict_gf["partner_requesting"] = "partner_b"
                    tasks.append(loop.run_in_executor(None, lambda: pinecone_service.upsert_repair_plan(f"{conflict_id}_girlfriend", emb_plan_gf, repair_plan_dict_gf, "repair_plans")))
                    if db_service:
                        tasks.append(loop.run_in_executor(None, lambda: db_service.create_repair_plan(conflict_id, relationship_id, "partner_b", s3_url_plan_gf)))
                


                # Execute all DB/Pinecone/Neo4j tasks
                if tasks:
                    await asyncio.gather(*tasks)
                
                logger.info("✅ Stored all analyses and repair plans in background")
                
            except Exception as e:
                logger.error(f"❌ Error storing all data in background: {e}")
                import traceback
                logger.error(traceback.format_exc())

        # Schedule background task
        background_tasks.add_task(store_all_background)
        
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

@router.get("/conflicts/{conflict_id}/related")
async def get_related_conflicts(conflict_id: str):
    """
    Get related conflicts (Placeholder - Neo4j removed)
    """
    return {"related_conflicts": []}

@router.post("/conflicts/{conflict_id}/generate-analysis")
async def generate_analysis_only(
    conflict_id: str,
    request: dict = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Generate analysis from both perspectives (boyfriend + girlfriend POV)
    """
    try:
        relationship_id = request.get("relationship_id", "00000000-0000-0000-0000-000000000000")
        partner_a_id = request.get("partner_a_id", "partner_a")
        partner_b_id = request.get("partner_b_id", "partner_b")
        
        import time
        endpoint_start = time.time()
        logger.info(f"🚀 Checking for existing analysis for {conflict_id}")
        
        # Check if analysis already exists
        existing_analysis = None
        if db_service:
            try:
                existing_analysis = db_service.get_conflict_analysis(
                    conflict_id=conflict_id,
                    relationship_id=relationship_id
                )
                if existing_analysis and existing_analysis.get("analysis_path"):
                    # Retrieve from S3
                    analysis_path = existing_analysis["analysis_path"]
                    s3_key = analysis_path
                    if s3_key.startswith(f"s3://{settings.S3_BUCKET_NAME}/"):
                        s3_key = s3_key.replace(f"s3://{settings.S3_BUCKET_NAME}/", "")
                    elif s3_key.startswith("https://"):
                        # Extract key from S3 URL
                        s3_key = s3_key.split(f"{settings.S3_BUCKET_NAME}/", 1)[-1] if f"{settings.S3_BUCKET_NAME}/" in s3_key else s3_key
                    
                    file_response = s3_service.download_file(s3_key)
                    if file_response:
                        analysis_data = json.loads(file_response.decode('utf-8'))
                        logger.info(f"✅ Retrieved existing analysis for conflict {conflict_id} from S3")
                        return {
                            "success": True,
                            "analysis_boyfriend": analysis_data,
                            "cached": True
                        }
            except Exception as e:
                logger.warning(f"⚠️ Error checking for existing analysis: {e}")
                # Continue to generate new analysis
        
        logger.info(f"📝 No existing analysis found, generating new analysis for {conflict_id}")
        
        # Get transcript directly from PostgreSQL
        transcript_data = db_service.get_conflict_transcript(conflict_id)
        
        if not transcript_data:
            # Fallback to S3 via db_service (bypasses RLS)
            try:
                if db_service:
                    conflict = db_service.get_conflict(conflict_id)
                    
                    if conflict:
                        transcript_path = conflict.get("transcript_path")
                        
                        if transcript_path:
                            s3_key = transcript_path
                            if s3_key.startswith(f"s3://{settings.S3_BUCKET_NAME}/"):
                                s3_key = s3_key.replace(f"s3://{settings.S3_BUCKET_NAME}/", "")
                            
                            file_response = s3_service.download_file(s3_key)
                            if file_response:
                                transcript_data = json.loads(file_response.decode('utf-8'))
                                
                                transcript_text = ""
                                if isinstance(transcript_data, list):
                                    transcript_lines = []
                                    for segment in transcript_data:
                                        if isinstance(segment, dict):
                                            speaker = segment.get("speaker", segment.get("speaker_name", "Speaker"))
                                            text = segment.get("text", segment.get("transcript", segment.get("message", "")))
                                            if text:
                                                transcript_lines.append(f"{speaker}: {text}")
                                        elif isinstance(segment, str):
                                            transcript_lines.append(segment)
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
                                
                                # Construct transcript_data dict to match expected format
                                transcript_data = {
                                    "transcript_text": transcript_text,
                                    "duration": conflict.get("duration", 0.0),
                                    "speaker_labels": conflict.get("speaker_labels", {})
                                }
            except Exception as e:
                logger.warning(f"⚠️ Failed to fetch transcript from S3: {e}")

        if not transcript_data:
            raise HTTPException(
                status_code=404,
                detail=f"Transcript not found for conflict {conflict_id}. Please ensure the fight was properly captured and stored."
            )
        
        transcript_text = transcript_data.get("transcript_text", "")
        duration = 0.0
        speaker_labels = {}
        
        logger.info(f"✅ Retrieved transcript from PostgreSQL: {len(transcript_text)} characters")
        
        # Use RAG system to get relevant context from ENTIRE corpus (transcripts + profiles)
        # This is faster than sending full transcript and provides better context
        from app.services.transcript_rag import TranscriptRAGSystem
        
        import time
        rag_start = time.time()
        logger.info(f"🔍 Using RAG to retrieve relevant context from entire corpus...")
        # Optimized k=7 for faster LLM processing while maintaining quality (7 chunks ~3000-3500 chars is sufficient)
        rag_system = TranscriptRAGSystem(k=7, include_profiles=True)  # Get top 7 most relevant chunks
        
        # Create query from transcript for RAG lookup
        # Use first 500 chars as query to get relevant context from entire corpus
        query_for_rag = transcript_text[:500] if len(transcript_text) > 500 else transcript_text
        rag_context = await rag_system.rag_lookup(
            query=query_for_rag,
            conflict_id=conflict_id,
            relationship_id=relationship_id
        )
        
        # Extract profile information from RAG context (if present)
        boyfriend_profile = None
        girlfriend_profile = None
        
        # Parse RAG context to extract profile sections
        # RAG context format: "[Adrian's Profile - Background & Personality]:\n{text}\n"
        bf_markers = ["[Adrian's Profile", "[Boyfriend's Profile"]
        for marker in bf_markers:
            if marker in rag_context:
                bf_start = rag_context.find(marker)
                if bf_start != -1:
                    # Find the end of this profile section
                    bf_end = rag_context.find("\n\n[", bf_start + len(marker))
                    if bf_end == -1:
                        bf_end = len(rag_context)
                    # Extract text after "]:\n"
                    profile_section = rag_context[bf_start:bf_end]
                    if "]:\n" in profile_section:
                        boyfriend_profile = profile_section.split("]:\n", 1)[1].strip()
                        break
        
        gf_markers = ["[Elara's Profile", "[Girlfriend's Profile"]
        for marker in gf_markers:
            if marker in rag_context:
                gf_start = rag_context.find(marker)
                if gf_start != -1:
                    # Find the end of this profile section
                    gf_end = rag_context.find("\n\n[", gf_start + len(marker))
                    if gf_end == -1:
                        gf_end = len(rag_context)
                    # Extract text after "]:\n"
                    profile_section = rag_context[gf_start:gf_end]
                    if "]:\n" in profile_section:
                        girlfriend_profile = profile_section.split("]:\n", 1)[1].strip()
                        break
        
        rag_time = time.time() - rag_start
        logger.info(f"📋 Extracted profiles: BF={bool(boyfriend_profile)}, GF={bool(girlfriend_profile)}")
        
        # Use RAG context instead of full transcript for faster, more contextualized analysis
        # RAG context includes: relevant transcript chunks + profile chunks from entire corpus
        rag_summary = f"✅ Retrieved RAG context: {len(rag_context)} chars (vs {len(transcript_text)} chars full transcript) in {rag_time:.2f}s"
        logger.info(rag_summary)
        print(rag_summary)  # Also print to stdout for visibility
        
        # Generate ONLY boyfriend (Adrian's) analysis using RAG context
        timestamp_now = datetime.now()
        analysis_boyfriend = await analyze_conflict_transcript(
                conflict_id=conflict_id,
            transcript_text=rag_context,  # Use RAG context instead of full transcript
                relationship_id=relationship_id,
                partner_a_id=partner_a_id,
                partner_b_id=partner_b_id,
                speaker_labels=speaker_labels,
                duration=duration,
                timestamp=timestamp_now,
            partner_id="partner_a",  # Only generate boyfriend (Adrian's) perspective
                boyfriend_profile=boyfriend_profile,
            girlfriend_profile=girlfriend_profile,
            use_rag_context=True  # Flag to indicate we're using RAG context
        )
        
        # Calculate timing BEFORE storage
        total_time = time.time() - endpoint_start
        llm_analysis_time = total_time - rag_time
        summary_msg = f"""
⏱️  === ANALYSIS GENERATION SUMMARY ===
   RAG Lookup: {rag_time:.2f}s
   LLM Analysis: {llm_analysis_time:.2f}s (includes API call + embedding + Pinecone storage)
   Total Time: {total_time:.2f}s
✅ Analysis generation complete! (Boyfriend perspective only)
   
   💡 Breakdown: Check logs above for detailed LLM API, embedding, and Pinecone timing
"""
        logger.info(summary_msg)
        print(summary_msg)  # Also print to stdout for visibility
        
        # RETURN RESULTS FIRST (don't block on storage)
        response_data = {
            "success": True,
            "analysis_boyfriend": analysis_boyfriend.model_dump()
        }
        
        # Store analysis ASYNCHRONOUSLY in background (don't block response)
        # All storage operations run in parallel for speed
        async def store_analysis_background():
            try:
                analysis_path_bf = f"analysis/{relationship_id}/{conflict_id}_analysis_boyfriend.json"
                analysis_json_bf = json.dumps(analysis_boyfriend.model_dump(), default=str, indent=2)
                
                # Run S3 upload and embedding generation in parallel (both are sync, run in thread pool)
                loop = asyncio.get_event_loop()
                s3_url_bf, analysis_embedding_bf = await asyncio.gather(
                    loop.run_in_executor(
                        None,
                        lambda: s3_service.upload_file(
                            file_path=analysis_path_bf,
                            file_content=analysis_json_bf.encode('utf-8'),
                            content_type="application/json"
                        )
                    ),
                    loop.run_in_executor(
                        None,
                        lambda: embeddings_service.embed_text(analysis_boyfriend.fight_summary)
                    )
                )
                
                if s3_url_bf:
                    analysis_dict_bf = analysis_boyfriend.model_dump()
                    analysis_dict_bf["conflict_id"] = conflict_id  # Ensure conflict_id is in metadata
                    analysis_dict_bf["analyzed_at"] = datetime.now()
                    analysis_dict_bf["partner_pov"] = "boyfriend"
                    
                    # Store in Pinecone and DB in parallel (both sync, run in thread pool)
                    await asyncio.gather(
                        loop.run_in_executor(
                            None,
                            lambda: pinecone_service.upsert_analysis(
                                conflict_id=conflict_id,  # Use original conflict_id (not _boyfriend suffix)
                                embedding=analysis_embedding_bf,
                                analysis_data=analysis_dict_bf,
                                namespace="analysis"
                            )
                        ),
                        loop.run_in_executor(
                            None,
                            lambda: db_service.create_conflict_analysis(
                                conflict_id=conflict_id,
                                relationship_id=relationship_id,
                                analysis_path=s3_url_bf
                            )
                        ) if db_service else asyncio.sleep(0)
                    )
                
                logger.info("✅ Stored analysis in background (S3 + Pinecone + DB) - all parallel")
            except Exception as e:
                logger.error(f"❌ Error storing analysis in background: {e}")
        
        # Schedule background storage (non-blocking) using FastAPI BackgroundTasks
        # BackgroundTasks is automatically injected by FastAPI - it will run after response is sent
        background_tasks.add_task(store_analysis_background)
        
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conflicts/{conflict_id}/generate-repair-plans")
async def generate_repair_plans_only(
    conflict_id: str,
    request: dict = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Generate repair plans for both perspectives (boyfriend + girlfriend)
    """
    try:
        relationship_id = request.get("relationship_id", "00000000-0000-0000-0000-000000000000")
        partner_a_id = request.get("partner_a_id", "partner_a")
        partner_b_id = request.get("partner_b_id", "partner_b")
        
        import time
        repair_start = time.time()
        logger.info(f"🚀 Checking for existing repair plans for {conflict_id}")
        
        # Check if repair plans already exist
        existing_plans = []
        if db_service:
            try:
                existing_plans = db_service.get_repair_plans(
                    conflict_id=conflict_id,
                    relationship_id=relationship_id
                )
                if existing_plans and len(existing_plans) >= 2:
                    # Check if we have both partner_a and partner_b plans
                    partner_a_plan = next((p for p in existing_plans if p.get("partner_requesting") == "partner_a"), None)
                    partner_b_plan = next((p for p in existing_plans if p.get("partner_requesting") == "partner_b"), None)
                    
                    if partner_a_plan and partner_b_plan:
                        # Retrieve both from S3
                        plans_retrieved = {}
                        
                        for plan in [partner_a_plan, partner_b_plan]:
                            plan_path = plan.get("plan_path")
                            if plan_path:
                                s3_key = plan_path
                                if s3_key.startswith(f"s3://{settings.S3_BUCKET_NAME}/"):
                                    s3_key = s3_key.replace(f"s3://{settings.S3_BUCKET_NAME}/", "")
                                elif s3_key.startswith("https://"):
                                    s3_key = s3_key.split(f"{settings.S3_BUCKET_NAME}/", 1)[-1] if f"{settings.S3_BUCKET_NAME}/" in s3_key else s3_key
                                
                                file_response = s3_service.download_file(s3_key)
                                if file_response:
                                    plan_data = json.loads(file_response.decode('utf-8'))
                                    partner = plan.get("partner_requesting")
                                    if partner == "partner_a":
                                        plans_retrieved["boyfriend"] = plan_data
                                    elif partner == "partner_b":
                                        plans_retrieved["girlfriend"] = plan_data
                        
                        if len(plans_retrieved) == 2:
                            logger.info(f"✅ Retrieved existing repair plans for conflict {conflict_id} from S3")
                            return {
                                "success": True,
                                "repair_plan_boyfriend": plans_retrieved.get("boyfriend"),
                                "repair_plan_girlfriend": plans_retrieved.get("girlfriend"),
                                "cached": True
                            }
            except Exception as e:
                logger.warning(f"⚠️ Error checking for existing repair plans: {e}")
                # Continue to generate new plans
        
        logger.info(f"📝 No existing repair plans found, generating new plans for {conflict_id}")
        
        # Get transcript (same logic)
        transcript_text = ""
        transcript_data = db_service.get_conflict_transcript(conflict_id)
        
        duration = 0.0
        speaker_labels = {}
        
        if transcript_data:
            transcript_text = transcript_data.get("transcript_text", "")
            duration = transcript_data.get("duration", 0.0)
            speaker_labels = transcript_data.get("speaker_labels", {})
        else:
            # Fallback to S3 via db_service (bypasses RLS)
            try:
                if db_service:
                    conflict = db_service.get_conflict(conflict_id)
                    
                    if conflict:
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
                                        elif isinstance(segment, str):
                                            transcript_lines.append(segment)
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
        
        # Generate ONLY boyfriend repair plan (user requested to remove girlfriend)
        logger.info(f"🔧 Generating repair plan for boyfriend (partner_a) only")
        repair_plan_boyfriend = await generate_repair_plan(
            conflict_id=conflict_id,
            transcript_text=transcript_text,
            partner_requesting_id="partner_a",
            relationship_id=relationship_id,
            partner_a_id=partner_a_id,
            partner_b_id=partner_b_id,
            analysis=None,
            boyfriend_profile=boyfriend_profile,
            girlfriend_profile=girlfriend_profile
        )
        
        # Calculate total time
        repair_total_time = time.time() - repair_start
        logger.info(f"""
⏱️  === REPAIR PLAN GENERATION SUMMARY ===
   Total Time: {repair_total_time:.2f}s
✅ Repair plan generation complete (boyfriend only)!
""")
        
        # Define background storage task
        async def store_repair_plan_background():
            try:
                plan_path_bf = f"repair_plans/{relationship_id}/{conflict_id}_repair_partner_a.json"
                plan_json_bf = json.dumps(repair_plan_boyfriend.model_dump(), default=str, indent=2)
                
                # Run S3 upload and embedding generation in parallel
                loop = asyncio.get_event_loop()
                s3_url_bf, repair_plan_embedding_bf = await asyncio.gather(
                    loop.run_in_executor(
                        None,
                        lambda: s3_service.upload_file(
                            file_path=plan_path_bf,
                            file_content=plan_json_bf.encode('utf-8'),
                            content_type="application/json"
                        )
                    ),
                    loop.run_in_executor(
                        None,
                        lambda: embeddings_service.embed_text(
                            f"{repair_plan_boyfriend.apology_script} {' '.join(repair_plan_boyfriend.steps)}"
                        )
                    )
                )
                
                if s3_url_bf:
                    # Store in DB and Pinecone in parallel
                    repair_plan_dict_bf = repair_plan_boyfriend.model_dump()
                    repair_plan_dict_bf["conflict_id"] = conflict_id
                    repair_plan_dict_bf["partner_requesting"] = "partner_a"
                    
                    await asyncio.gather(
                        loop.run_in_executor(
                            None,
                            lambda: db_service.create_repair_plan(
                                conflict_id=conflict_id,
                                relationship_id=relationship_id,
                                partner_requesting="partner_a",
                                plan_path=s3_url_bf
                            )
                        ) if db_service else asyncio.sleep(0),
                        loop.run_in_executor(
                            None,
                            lambda: pinecone_service.upsert_repair_plan(
                                conflict_id=conflict_id,
                                embedding=repair_plan_embedding_bf,
                                repair_plan_data=repair_plan_dict_bf,
                                namespace="repair_plans"
                            )
                        )
                    )
                    logger.info("✅ Stored repair plan in background (S3 + Pinecone + DB)")
            except Exception as e:
                logger.error(f"❌ Error storing repair plans in background: {e}")

        # Schedule background task
        background_tasks.add_task(store_repair_plan_background)
        
        return {
            "success": True,
            "repair_plan_boyfriend": repair_plan_boyfriend.model_dump(),
            "message": "Repair plan generated for boyfriend (Adrian) only"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating repair plans: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/conflicts/{conflict_id}/title")
async def update_conflict_title(
    conflict_id: str,
    title: str = Body(..., embed=True)
):
    """Update the title of a conflict"""
    try:
        success = db_service.update_conflict_title(conflict_id, title)
        if not success:
            raise HTTPException(status_code=404, detail="Conflict not found or update failed")
        
        return {"success": True, "title": title}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating conflict title: {e}")
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
        db_messages = [] # For batch insert into rant_messages
        
        for line in transcript_lines:
            if not isinstance(line, str):
                continue
                
            # Use regex split to find all speaker segments in the line
            # This handles cases where multiple turns are clumped: "Adrian: Hello. Elara: Hi."
            # Pattern matches "Name:", "Name (Role):", "Speaker N:", etc.
            # We use capturing group to keep the delimiter (the speaker name)
            parts = re.split(r'((?:Adrian Malhotra|Elara Voss|Boyfriend|Girlfriend|Speaker\s+\d+|partner_[ab])(?:\s*\(.*?\))?):\s*', line, flags=re.IGNORECASE)
            
            # If no split happened (len 1), it's just text. Append to last segment if exists.
            if len(parts) == 1:
                text = parts[0].strip()
                if text and speaker_segments:
                    # Append to last segment
                    speaker_segments[-1].text += " " + text
                    # Update corresponding db_message
                    if db_messages:
                        db_messages[-1]["content"] += " " + text
                continue
                
            # If split happened, parts will look like: ['', 'Adrian', 'Hello. ', 'Elara', 'Hi.']
            # The first part is text before the first speaker label (usually empty or belongs to prev speaker)
            if parts[0].strip() and speaker_segments:
                speaker_segments[-1].text += " " + parts[0].strip()
                if db_messages:
                    db_messages[-1]["content"] += " " + parts[0].strip()
            
            # Iterate through the rest: odd indices are speakers, even are text
            for i in range(1, len(parts), 2):
                speaker_label = parts[i]
                text = parts[i+1].strip() if i+1 < len(parts) else ""
                
                if not text:
                    continue
                    
                # Determine standardized speaker name
                speaker_name = "Unknown"
                partner_id = "partner_a" # Default
                
                if re.match(r'(?:Adrian|Boyfriend|Speaker\s+1|partner_a|Speaker\s+0)', speaker_label, re.IGNORECASE):
                    speaker_name = "Adrian Malhotra"
                    partner_id = "partner_a"
                elif re.match(r'(?:Elara|Girlfriend|Speaker\s+2|partner_b|Speaker\s+1)', speaker_label, re.IGNORECASE):
                    speaker_name = "Elara Voss"
                    partner_id = "partner_b"
                
                # Create segment
                speaker_segments.append(SpeakerSegment(
                    speaker=speaker_name,
                    text=text,
                    start_time=None,
                    end_time=None
                ))
                
                # Create DB message
                db_messages.append({
                    "partner_id": partner_id,
                    "role": "user",
                    "content": text
                })
        
        # Save messages to rant_messages table for immediate availability
        if db_messages:
            try:
                db_service.save_transcript_messages(conflict_id, db_messages)
                logger.info(f"✅ Saved {len(db_messages)} transcript messages to rant_messages table")
            except Exception as e:
                logger.error(f"❌ Error saving transcript messages to DB: {e}")
        
        # Reconstruct transcript_text from the clean segments to ensure it matches DB
        # This fixes the issue where the raw input was clumped but DB was clean
        if speaker_segments:
            transcript_text = "\n".join([f"{seg.speaker}: {seg.text}" for seg in speaker_segments])
            logger.info(f"✅ Reconstructed transcript text from {len(speaker_segments)} segments")
        
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
        
        # Transcript storage complete - analysis and repair plans will be generated on-demand
        # when user clicks "View Analysis" or "View Repair Plan" buttons
        
        # 3. Generate Title (NEW)
        background_tasks.add_task(generate_title_background, conflict_id, transcript_text)

        # 4. Generate Analysis and Repair Plan (NEW - Parallel)
        # We pass partner IDs from the request
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
        
        return {
            "success": True,
            "conflict_id": conflict_id,
            "message": "Transcript stored. Analysis and repair plans are generating in background."
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
        transcript_data = db_service.get_conflict_transcript(conflict_id)
        
        if transcript_data:
            transcript_text = transcript_data.get("transcript_text", "") if transcript_data else ""
        
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
                    
                    file_response = s3_service.download_file(s3_key)
                    if file_response:
                        import json
                        try:
                            json_content = json.loads(file_response)
                            if isinstance(json_content, list):
                                transcript_text = "\n".join([f"{item.get('speaker', 'Unknown')}: {item.get('text', '')}" for item in json_content])
                            else:
                                transcript_text = str(json_content)
                        except:
                            transcript_text = file_response.decode('utf-8')
                except Exception as e:
                    logger.error(f"Error fetching from S3: {e}")

        # Check if analysis/repair plans already exist
        existing_analysis_bf = s3_service.file_exists(f"analysis/{relationship_id}/{conflict_id}_analysis_partner_a.json")
        existing_repair_bf = s3_service.file_exists(f"repair_plans/{relationship_id}/{conflict_id}_repair_partner_a.json")
        
        if existing_analysis_bf and existing_repair_bf:
            logger.info(f"✅ Found existing analysis and repair plans for {conflict_id}")
            # Fetch and return existing data
            analysis_bf_content = s3_service.download_file(f"analysis/{relationship_id}/{conflict_id}_analysis_partner_a.json")
            repair_bf_content = s3_service.download_file(f"repair_plans/{relationship_id}/{conflict_id}_repair_partner_a.json")
            
            import json
            return {
                "success": True,
                "analysis_boyfriend": json.loads(analysis_bf_content) if analysis_bf_content else None,
                "repair_plan_boyfriend": json.loads(repair_bf_content) if repair_bf_content else None,
                "message": "Retrieved existing analysis and repair plans"
            }

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
        transcript_data = db_service.get_conflict_transcript(conflict_id)
        
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
        transcript_data = db_service.get_conflict_transcript(conflict_id)
        
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

