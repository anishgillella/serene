"""
PDF upload and OCR endpoints
"""
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
from app.services.ocr_service import ocr_service
from app.services.embeddings_service import embeddings_service
from app.services.pinecone_service import pinecone_service
from app.services.db_service import db_service
from app.services.s3_service import s3_service
from app.config import settings
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pdfs", tags=["pdfs"])

@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    relationship_id: str = Form(...),
    pdf_type: str = Form(...),  # "boyfriend_profile", "girlfriend_profile", "handbook"
    partner_id: Optional[str] = Form(None)
):
    """
    Upload PDF, extract text via OCR, and store in Pinecone
    
    Request:
    - file: PDF file
    - relationship_id: Relationship identifier
    - pdf_type: Type of PDF (boyfriend_profile, girlfriend_profile, handbook)
    - partner_id: Optional partner ID for profile PDFs
    """
    try:
        # Read PDF file
        pdf_bytes = await file.read()
        logger.info(f"📄 Received PDF: {file.filename}, size: {len(pdf_bytes)} bytes, type: {pdf_type}")
        
        # Extract text using Mistral OCR
        logger.info("🔍 Extracting text from PDF using Mistral OCR...")
        extracted_text = await ocr_service.extract_text_from_pdf(pdf_bytes, filename=file.filename)
        logger.info(f"✅ Extracted {len(extracted_text)} characters from PDF")
        
        # Generate embedding
        embedding = embeddings_service.embed_text(extracted_text)
        
        # Determine namespace based on PDF type
        namespace_map = {
            "boyfriend_profile": "profiles",
            "girlfriend_profile": "profiles",
            "handbook": "handbooks"
        }
        namespace = namespace_map.get(pdf_type)
        
        if not namespace:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid pdf_type: {pdf_type}. Must be one of: boyfriend_profile, girlfriend_profile, handbook"
            )
        
        # Create unique ID
        pdf_id = str(uuid.uuid4())
        
        # 1. Upload PDF to AWS S3
        file_path = None
        s3_url = None
        try:
            # Determine folder based on PDF type (single bucket with folders)
            folder = "profiles" if pdf_type in ["boyfriend_profile", "girlfriend_profile"] else "handbooks"
            file_path = f"{folder}/{relationship_id}/{pdf_id}.pdf"
            
            # Upload PDF file to S3
            s3_url = s3_service.upload_file(
                file_path=file_path,
                file_content=pdf_bytes,
                content_type="application/pdf"
            )
            if s3_url:
                logger.info(f"✅ Stored PDF in S3: {file_path} (URL: {s3_url})")
            else:
                logger.error(f"❌ Failed to upload PDF to S3: {file_path}")
        except Exception as e:
            logger.error(f"❌ Error storing PDF in S3: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Continue even if S3 fails - Pinecone storage is primary
        
        # 2. Store in Pinecone (vector embeddings for semantic search)
        # Note: Pinecone metadata has size limits, so we store full text in a separate field
        # For profile PDFs, we'll store the full text since it's needed for personalization
        metadata = {
            "pdf_id": pdf_id,
            "relationship_id": relationship_id,
            "pdf_type": pdf_type,
            "filename": file.filename,
            "text_length": len(extracted_text),
        }
        
        if partner_id:
            metadata["partner_id"] = partner_id
        
        # For profiles, store full text in metadata (they're usually small)
        # For larger documents, we might need chunking
        if pdf_type in ["boyfriend_profile", "girlfriend_profile"]:
            # Store full text for profiles (usually small enough)
            if len(extracted_text) <= 40000:  # Pinecone metadata limit is ~40KB
                metadata["extracted_text"] = extracted_text
            else:
                # Store first part and note that full text is available
                metadata["extracted_text"] = extracted_text[:35000]
                metadata["text_truncated"] = True
        
        pinecone_service.index.upsert(
            vectors=[{
                "id": f"{pdf_type}_{pdf_id}",
                "values": embedding,
                "metadata": metadata
            }],
            namespace=namespace
        )
        
        # Also store full text in a separate vector for better retrieval
        # Split into chunks if needed for large documents
        if len(extracted_text) > 40000:
            # For large documents, create multiple vectors with chunks
            chunk_size = 10000
            chunks = [extracted_text[i:i+chunk_size] for i in range(0, len(extracted_text), chunk_size)]
            chunk_vectors = []
            for i, chunk in enumerate(chunks):
                chunk_embedding = embeddings_service.embed_text(chunk)
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
                pinecone_service.index.upsert(
                    vectors=chunk_vectors,
                    namespace=namespace
                )
        
        logger.info(f"✅ Stored PDF in Pinecone: {pdf_id}, namespace: {namespace}")
        
        # 3. Store metadata in database (with S3 path)
        profile_id = None
        if db_service and file_path:
            try:
                profile_id = db_service.create_profile(
                    relationship_id=relationship_id,
                    pdf_type=pdf_type,
                    partner_id=partner_id,
                    filename=file.filename,
                    file_path=s3_url or file_path,  # Store S3 URL or path
                    pdf_id=pdf_id,
                    extracted_text_length=len(extracted_text)
                )
                logger.info(f"✅ Stored profile metadata in database: {profile_id}")
            except Exception as e:
                logger.error(f"❌ Error storing profile metadata in database: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Continue even if database fails
        
        return {
            "success": True,
            "pdf_id": pdf_id,
            "profile_id": profile_id,
            "extracted_text_length": len(extracted_text),
            "namespace": namespace,
            "file_path": s3_url or file_path,
            "s3_url": s3_url,
            "message": "PDF uploaded and processed successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Error uploading PDF: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profiles/{relationship_id}")
async def get_partner_profiles(relationship_id: str):
    """
    Retrieve partner profiles for a relationship
    Returns full extracted text from profile PDFs
    """
    try:
        # Query Pinecone for profiles using a dummy query vector
        # We use filter to find the right documents
        dummy_vector = [0.0] * 1024
        
        boyfriend_result = pinecone_service.index.query(
            vector=dummy_vector,
            top_k=1,
            namespace="profiles",
            include_metadata=True,
            filter={
                "relationship_id": {"$eq": relationship_id},
                "pdf_type": {"$eq": "boyfriend_profile"}
            }
        )
        
        girlfriend_result = pinecone_service.index.query(
            vector=dummy_vector,
            top_k=1,
            namespace="profiles",
            include_metadata=True,
            filter={
                "relationship_id": {"$eq": relationship_id},
                "pdf_type": {"$eq": "girlfriend_profile"}
            }
        )
        
        boyfriend_profile = None
        girlfriend_profile = None
        
        if boyfriend_result.matches:
            match = boyfriend_result.matches[0]
            boyfriend_profile = match.metadata.get("extracted_text", "")
            # If text was truncated, try to get chunks
            if match.metadata.get("text_truncated") and boyfriend_profile:
                pdf_id = match.metadata.get("pdf_id")
                if pdf_id:
                    # Query for chunks
                    chunk_results = pinecone_service.index.query(
                        vector=dummy_vector,
                        top_k=10,
                        namespace="profiles",
                        include_metadata=True,
                        filter={
                            "pdf_id": {"$eq": pdf_id},
                            "chunk_index": {"$exists": True}
                        }
                    )
                    if chunk_results.matches:
                        chunks = sorted(chunk_results.matches, key=lambda x: x.metadata.get("chunk_index", 0))
                        full_text = "".join([chunk.metadata.get("extracted_text", "") for chunk in chunks])
                        if full_text:
                            boyfriend_profile = full_text
        
        if girlfriend_result.matches:
            match = girlfriend_result.matches[0]
            girlfriend_profile = match.metadata.get("extracted_text", "")
            # If text was truncated, try to get chunks
            if match.metadata.get("text_truncated") and girlfriend_profile:
                pdf_id = match.metadata.get("pdf_id")
                if pdf_id:
                    # Query for chunks
                    chunk_results = pinecone_service.index.query(
                        vector=dummy_vector,
                        top_k=10,
                        namespace="profiles",
                        include_metadata=True,
                        filter={
                            "pdf_id": {"$eq": pdf_id},
                            "chunk_index": {"$exists": True}
                        }
                    )
                    if chunk_results.matches:
                        chunks = sorted(chunk_results.matches, key=lambda x: x.metadata.get("chunk_index", 0))
                        full_text = "".join([chunk.metadata.get("extracted_text", "") for chunk in chunks])
                        if full_text:
                            girlfriend_profile = full_text
        
        return {
            "success": True,
            "boyfriend_profile": boyfriend_profile,
            "girlfriend_profile": girlfriend_profile
        }
        
    except Exception as e:
        logger.error(f"❌ Error retrieving profiles: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

