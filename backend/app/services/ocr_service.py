"""
Mistral OCR service for extracting text from PDFs
"""
import logging
import asyncio
import tempfile
import os
from typing import Optional
from mistralai import Mistral
from mistralai import DocumentURLChunk
from app.config import settings

logger = logging.getLogger(__name__)

class OCRService:
    """Service for OCR using Mistral OCR API"""
    
    def __init__(self):
        self.client = Mistral(api_key=settings.MISTRAL_API_KEY)
        self.model = "mistral-ocr-latest"
        logger.info("✅ Initialized Mistral OCR service")
    
    async def extract_text_from_pdf(self, pdf_bytes: bytes, filename: Optional[str] = None) -> str:
        """
        Extract text from PDF using Mistral OCR API
        
        Args:
            pdf_bytes: PDF file as bytes
            filename: Optional filename for the PDF
            
        Returns:
            Extracted text content
        """
        try:
            filename = filename or "document.pdf"
            loop = asyncio.get_event_loop()
            
            logger.info(f"📄 Uploading PDF to Mistral OCR: {filename} ({len(pdf_bytes)} bytes)")
            
            # Upload file to Mistral's OCR service
            upload_response = await loop.run_in_executor(
                None,
                lambda: self.client.files.upload(
                    file={
                        "file_name": filename,
                        "content": pdf_bytes,
                    },
                    purpose="ocr"
                )
            )
            
            logger.info(f"✅ File uploaded, ID: {upload_response.id}")
            
            # Get signed URL for the uploaded file
            signed_url_response = await loop.run_in_executor(
                None,
                lambda: self.client.files.get_signed_url(
                    file_id=upload_response.id, 
                    expiry=1  # 1 hour expiry
                )
            )
            
            logger.info(f"✅ Got signed URL, processing OCR...")
            
            # Process PDF with OCR
            ocr_response = await loop.run_in_executor(
                None,
                lambda: self.client.ocr.process(
                    document=DocumentURLChunk(document_url=signed_url_response.url),
                    model=self.model,
                    include_image_base64=False  # We only need text
                )
            )
            
            # Extract text from all pages
            all_text = []
            
            if not ocr_response.pages:
                logger.warning("No pages found in OCR response")
                return ""
            
            for idx, page in enumerate(ocr_response.pages):
                # Try to get page number with fallbacks
                try:
                    page_num = page.page_number
                except AttributeError:
                    if hasattr(page, 'page_index'):
                        page_num = page.page_index + 1
                    elif hasattr(page, 'index'):
                        page_num = page.index + 1
                    else:
                        page_num = idx + 1
                
                # Extract text content from markdown
                try:
                    text_content = page.markdown
                except AttributeError:
                    # Fallback if markdown attribute is missing
                    if hasattr(page, 'text'):
                        text_content = page.text
                    elif hasattr(page, 'content'):
                        text_content = page.content
                    else:
                        text_content = ""
                        logger.warning(f"Could not find text content for page {page_num}")
                
                if text_content:
                    all_text.append(f"--- Page {page_num} ---\n{text_content}")
            
            full_text = "\n\n".join(all_text)
            logger.info(f"✅ Extracted {len(full_text)} characters from PDF ({len(ocr_response.pages)} pages)")
            
            return full_text
            
        except Exception as e:
            logger.error(f"❌ Error extracting text from PDF: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

# Singleton instance
ocr_service = OCRService()

