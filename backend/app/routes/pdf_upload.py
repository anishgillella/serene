"""
PDF upload and OCR endpoints
"""
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from typing import Optional, List, Dict
from app.services.ocr_service import ocr_service
from app.services.embeddings_service import embeddings_service
from app.services.pinecone_service import pinecone_service
from app.services.db_service import db_service
from app.services.s3_service import s3_service
from app.config import settings
import uuid
import asyncio
from datetime import datetime
import traceback
import re

logger = logging.getLogger(__name__)

# Store logs for active uploads: {pdf_id: [log_messages]}
upload_logs: Dict[str, List[str]] = {}

router = APIRouter(prefix="/api/pdfs", tags=["pdfs"])

async def process_pdf_task(
    pdf_bytes: bytes,
    filename: str,
    relationship_id: str,
    pdf_type: str,
    partner_id: Optional[str],
    pdf_id: str,
    profile_id: Optional[str]
):
    def log(msg):
        logger.info(msg)
        if pdf_id not in upload_logs:
            upload_logs[pdf_id] = []
        upload_logs[pdf_id].append(f"{datetime.now().strftime('%H:%M:%S')} - {msg}")
    
    try:
        log(f"🚀 Starting background processing for {filename}...")
        
        # Extract text using generic extraction (PDF, DOCX, TXT)
        log(f"🔍 Extracting text from file using OCR/Text Extraction...")
        extracted_text = await ocr_service.extract_text(pdf_bytes, filename=filename)
        log(f"✅ Extracted {len(extracted_text)} characters from file")
        
        # Generate embedding
        log("🧠 Generating embeddings...")
        embedding = embeddings_service.embed_text(extracted_text)
        
        # Determine namespace based on PDF type
        namespace_map = {
            "handbook": "handbooks",
            "reference_book": "books",
            "document": "documents"
        }
        namespace = namespace_map.get(pdf_type)
        
        if not namespace:
            log(f"❌ Invalid pdf_type: {pdf_type}")
            return

        # 1. Upload PDF to AWS S3
        file_path = None
        s3_url = None
        try:
            if pdf_type == "reference_book":
                folder = "books"
            else:
                folder = "handbooks"
            # Determine extension and content type
            import os
            _, ext = os.path.splitext(filename)
            ext = ext.lower()
            content_type = "application/pdf"
            if ext == ".docx":
                content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            elif ext == ".txt":
                content_type = "text/plain"
            
            file_path = f"{folder}/{relationship_id}/{pdf_id}{ext}"
            
            log(f"☁️ Uploading to S3: {file_path}")
            s3_url = s3_service.upload_file(
                file_path=file_path,
                file_content=pdf_bytes,
                content_type=content_type
            )
            if s3_url:
                log(f"✅ Stored PDF in S3: {s3_url}")
            else:
                log(f"❌ Failed to upload PDF to S3")
        except Exception as e:
            log(f"❌ Error storing PDF in S3: {e}")
            logger.error(traceback.format_exc())
        
        # 2. Store in Pinecone
        metadata = {
            "pdf_id": pdf_id,
            "relationship_id": relationship_id,
            "pdf_type": pdf_type,
            "filename": filename,
            "text_length": len(extracted_text),
        }
        
        if partner_id:
            metadata["partner_id"] = partner_id
        
        # Handle chunking based on PDF type
        chunk_vectors = []
        
        if pdf_type == "reference_book":
            # SMART CHUNKING for reference books (with chapter detection)
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            
            log("📖 Using chapter-aware chunking for reference book...")
            
            # Detect chapters using regex patterns
            chapter_patterns = [
                r'^Chapter\s+(\d+|[IVXLCDM]+)[\s:.-]+(.+?)$',
                r'^CHAPTER\s+(\d+|[IVXLCDM]+)[\s:.-]+(.+?)$',
                r'^(\d+)\.\s+(.+?)$',
            ]
            
            chapters = []
            lines = extracted_text.split('\n')
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                for pattern in chapter_patterns:
                    match = re.match(pattern, line_stripped)
                    if match:
                        chapter_num = match.group(1)
                        chapter_title = match.group(2).strip()
                        try:
                            chapter_num_int = int(chapter_num)
                        except ValueError:
                            chapter_num_int = 0  # Unknown chapter
                        text_pos = extracted_text.find('\n'.join(lines[:i]))
                        chapters.append({
                            'number': chapter_num_int,
                            'title': chapter_title,
                            'start_pos': text_pos,
                        })
                        break
            
            # Set end positions for chapters
            for i in range(len(chapters)):
                if i < len(chapters) - 1:
                    chapters[i]['end_pos'] = chapters[i + 1]['start_pos']
                else:
                    chapters[i]['end_pos'] = len(extracted_text)
            
            log(f"   📚 Detected {len(chapters)} chapters")
            
            # Create text splitter (smart chunking)
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            
            # Helper to filter junk chunks
            junk_keywords = [
                "copyright", "all rights reserved", "isbn", "library of congress",
                "printed in", "publication data", "cover design", "simon & schuster",
                "acknowledgments", "dedication", "table of contents", "index",
                "thisiscrave.com", "atria books"
            ]
            def is_junk(text):
                text_lower = text.lower()
                junk_score = sum(1 for kw in junk_keywords if kw in text_lower)
                if junk_score >= 2 or (len(text) < 500 and junk_score >= 1):
                    return True
                if "thank you" in text_lower and len(text_lower.split('\n')) > 10:
                    return True
                return False

            # Collect all chunk texts + metadata first, then batch-embed
            pending_chunks = []  # list of (chunk_text, metadata_dict, vector_id)
            chunk_global_index = 0

            if chapters:
                for chapter in chapters:
                    chapter_text = extracted_text[chapter['start_pos']:chapter['end_pos']]
                    chapter_chunks = splitter.split_text(chapter_text)

                    for local_idx, chunk_text in enumerate(chapter_chunks):
                        if is_junk(chunk_text):
                            log(f"   🗑️ Skipping junk chunk: {chunk_text[:50]}...")
                            continue
                        pending_chunks.append((chunk_text, {
                            'pdf_id': pdf_id,
                            'relationship_id': relationship_id,
                            'pdf_type': pdf_type,
                            'filename': filename,
                            'book_title': filename.replace('.pdf', ''),
                            'chapter_number': chapter['number'],
                            'chapter_title': chapter['title'],
                            'chunk_index': chunk_global_index,
                            'chapter_chunk_index': local_idx,
                            'total_chapter_chunks': len(chapter_chunks),
                            'text': chunk_text,
                            'text_length': len(chunk_text),
                        }, f"book_{pdf_id}_chunk_{chunk_global_index}"))
                        chunk_global_index += 1
                log(f"   📖 Collected {len(pending_chunks)} chapter-aware chunks for batch embedding")
            else:
                log("   ⚠️ No chapters detected, using standard chunking")
                all_chunks = splitter.split_text(extracted_text)
                for idx, chunk_text in enumerate(all_chunks):
                    if is_junk(chunk_text):
                        log(f"   🗑️ Skipping junk chunk: {chunk_text[:50]}...")
                        continue
                    pending_chunks.append((chunk_text, {
                        'pdf_id': pdf_id,
                        'relationship_id': relationship_id,
                        'pdf_type': pdf_type,
                        'filename': filename,
                        'book_title': filename.replace('.pdf', ''),
                        'chapter_number': 0,
                        'chapter_title': 'Unknown Section',
                        'chunk_index': idx,
                        'text': chunk_text,
                        'text_length': len(chunk_text),
                    }, f"book_{pdf_id}_chunk_{idx}"))
                log(f"   📖 Collected {len(pending_chunks)} standard chunks for batch embedding")

            # Batch-embed all chunks (Voyage supports batches natively)
            if pending_chunks:
                EMBED_BATCH_SIZE = 128  # Voyage batch limit
                all_texts = [c[0] for c in pending_chunks]
                all_embeddings = []
                for i in range(0, len(all_texts), EMBED_BATCH_SIZE):
                    batch_texts = all_texts[i:i + EMBED_BATCH_SIZE]
                    log(f"   🧠 Embedding batch {i // EMBED_BATCH_SIZE + 1}/{(len(all_texts) + EMBED_BATCH_SIZE - 1) // EMBED_BATCH_SIZE} ({len(batch_texts)} chunks)...")
                    batch_embeddings = embeddings_service.embed_batch(batch_texts)
                    all_embeddings.extend(batch_embeddings)

                for idx, (chunk_text, metadata, vector_id) in enumerate(pending_chunks):
                    chunk_vectors.append({
                        'id': vector_id,
                        'values': all_embeddings[idx],
                        'metadata': metadata
                    })
                log(f"   ✅ Created {len(chunk_vectors)} chunks with batch embeddings")
            
            # Upload chunks in batches
            batch_size = 100
            total_batches = (len(chunk_vectors) + batch_size - 1) // batch_size
            for i in range(0, len(chunk_vectors), batch_size):
                batch = chunk_vectors[i:i + batch_size]
                pinecone_service.index.upsert(vectors=batch, namespace=namespace)
                log(f"   📤 Uploaded batch {i//batch_size + 1}/{total_batches} to Pinecone")
            

        
        else:
            # Other types (handbook): simple upload with basic chunking if large
            pinecone_service.index.upsert(
                vectors=[{
                    "id": f"{pdf_type}_{pdf_id}",
                    "values": embedding,
                    "metadata": metadata
                }],
                namespace=namespace
            )
            
            if len(extracted_text) > 40000:
                chunk_size = 10000
                chunks = [extracted_text[i:i+chunk_size] for i in range(0, len(extracted_text), chunk_size)]
                chunk_embeddings = embeddings_service.embed_batch(chunks)
                for i, (chunk, chunk_embedding) in enumerate(zip(chunks, chunk_embeddings)):
                    chunk_metadata = metadata.copy()
                    chunk_metadata["chunk_index"] = i
                    chunk_metadata["total_chunks"] = len(chunks)
                    chunk_metadata["extracted_text"] = chunk
                    chunk_vectors.append({
                        "id": f"{pdf_type}_{pdf_id}_chunk_{i}",
                        "values": chunk_embedding,
                        "metadata": chunk_metadata
                    })
                if chunk_vectors:
                    pinecone_service.index.upsert(vectors=chunk_vectors, namespace=namespace)
                    log(f"   ✅ Created and uploaded {len(chunk_vectors)} chunks (batch embedded)")
        
        log(f"✅ Stored PDF in Pinecone: {pdf_id}, namespace: {namespace}")
        
        # 3. Update DB record with success status
        if db_service:
            try:
                updates = {
                    "extracted_text_length": len(extracted_text)
                }
                if s3_url:
                    updates["file_path"] = s3_url
                    
                await asyncio.to_thread(
                    db_service.update_profile,
                    pdf_id=pdf_id,
                    updates=updates
                )
                log("✅ Updated database record")
            except Exception as e:
                log(f"❌ Error updating database: {e}")
        
    except Exception as e:
        log(f"❌ Error in background processing: {e}")
        logger.error(traceback.format_exc())

@router.post("/upload")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    relationship_id: str = Form(...),
    pdf_type: str = Form(...),  # "handbook", "reference_book", "document"
    partner_id: Optional[str] = Form(None)
):
    """
    Upload PDF, extract text via OCR, and store in Pinecone (Background Task)
    """
    try:
        # Read file
        pdf_bytes = await file.read()
        filename = file.filename
        logger.info(f"📄 Received file: {filename}, size: {len(pdf_bytes)} bytes, type: {pdf_type}")
        
        # Create unique ID
        pdf_id = str(uuid.uuid4())
        
        # Create DB record immediately (status=processing via length=0)
        profile_id = None
        if db_service:
            try:
                profile_id = db_service.create_profile(
                    relationship_id=relationship_id,
                    pdf_type=pdf_type,
                    partner_id=partner_id,
                    filename=filename,
                    file_path="", # Will update later
                    pdf_id=pdf_id,
                    extracted_text_length=0 # Indicates processing
                )
                logger.info(f"✅ Created initial profile record: {profile_id}")
            except Exception as e:
                logger.error(f"❌ Error creating profile record: {e}")
                # Continue even if DB fails, but we won't be able to update it later
        
        # Start background task
        background_tasks.add_task(
            process_pdf_task,
            pdf_bytes,
            filename,
            relationship_id,
            pdf_type,
            partner_id,
            pdf_id,
            profile_id
        )
        
        return {
            "success": True,
            "pdf_id": pdf_id,
            "profile_id": profile_id,
            "message": "Upload started in background",
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"❌ Error starting upload: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))




@router.get("/list/{relationship_id}")
async def list_pdfs(relationship_id: str):
    """
    List all uploaded PDFs for a relationship
    """
    try:
        if not db_service:
            # Fallback if DB service not available (e.g. using mock)
            return {"success": True, "files": []}
            
        profiles = db_service.get_profiles(relationship_id)
        return {
            "success": True, 
            "files": profiles
        }
    except Exception as e:
        logger.error(f"❌ Error listing PDFs: {e}")
        return {"success": False, "error": str(e), "files": []}


@router.get("/logs/{pdf_id}")
async def get_upload_logs(pdf_id: str):
    """
    Get real-time logs for a PDF upload
    """
    logs = upload_logs.get(pdf_id, [])
    return {"logs": logs}
