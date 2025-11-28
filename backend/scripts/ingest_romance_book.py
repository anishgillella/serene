#!/usr/bin/env python3
"""
Script to ingest a romance/relationship book PDF into Pinecone with chapter-aware chunking.

This creates a dedicated "books" namespace with chapter metadata for rich RAG queries.

Usage:
    python scripts/ingest_romance_book.py path/to/book.pdf "Book Title"
    
Example:
    python scripts/ingest_romance_book.py docs/romance_guide.pdf "The Art of Love"
"""

import sys
import os
import re
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ocr_service import ocr_service
from app.services.embeddings_service import embeddings_service
from app.services.pinecone_service import pinecone_service
from langchain.text_splitter import RecursiveCharacterTextSplitter
import asyncio
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChapterAwareBookIngester:
    """Ingests a book PDF with chapter detection and metadata"""
    
    def __init__(self):
        self.chapter_patterns = [
            r'^Chapter\s+(\d+|[IVXLCDM]+)[\s:.-]+(.+?)$',  # "Chapter 5: Title" or "Chapter V - Title"
            r'^CHAPTER\s+(\d+|[IVXLCDM]+)[\s:.-]+(.+?)$',  # Uppercase variant
            r'^(\d+)\.\s+(.+?)$',  # "1. Title"
        ]
        
    def detect_chapters(self, text: str) -> list:
        """
        Detect chapter boundaries in the extracted text.
        
        Returns list of dicts: [{'number': 1, 'title': 'Intro', 'start_pos': 0, 'end_pos': 1500}]
        """
        chapters = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
                
            for pattern in self.chapter_patterns:
                match = re.match(pattern, line_stripped)
                if match:
                    chapter_num = match.group(1)
                    chapter_title = match.group(2).strip()
                    
                    # Convert roman numerals to int if needed
                    try:
                        chapter_num_int = int(chapter_num)
                    except ValueError:
                        # Try to convert roman numeral
                        chapter_num_int = self._roman_to_int(chapter_num)
                    
                    # Calculate position in original text
                    text_pos = text.find('\n'.join(lines[:i]))
                    
                    chapters.append({
                        'number': chapter_num_int,
                        'title': chapter_title,
                        'start_pos': text_pos,
                        'raw_number': chapter_num
                    })
                    break
        
        # Set end positions
        for i in range(len(chapters)):
            if i < len(chapters) - 1:
                chapters[i]['end_pos'] = chapters[i + 1]['start_pos']
            else:
                chapters[i]['end_pos'] = len(text)
        
        logger.info(f"📖 Detected {len(chapters)} chapters")
        for ch in chapters[:5]:  # Log first 5
            logger.info(f"   Chapter {ch['number']}: {ch['title']}")
        
        return chapters
    
    def _roman_to_int(self, s: str) -> int:
        """Convert roman numeral to integer"""
        roman_map = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
        s = s.upper()
        result = 0
        prev = 0
        for char in reversed(s):
            val = roman_map.get(char, 0)
            if val < prev:
                result -= val
            else:
                result += val
            prev = val
        return result
    
    def chunk_with_chapter_metadata(self, text: str, book_title: str, chapters: list) -> list:
        """
        Chunk text while preserving chapter metadata.
        
        Returns list of chunks with metadata.
        """
        # Create text splitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        chunks_with_metadata = []
        chunk_global_index = 0
        
        # If chapters detected, chunk per chapter
        if chapters:
            for chapter in chapters:
                chapter_text = text[chapter['start_pos']:chapter['end_pos']]
                chapter_chunks = splitter.split_text(chapter_text)
                
                for local_idx, chunk_text in enumerate(chapter_chunks):
                    chunks_with_metadata.append({
                        'text': chunk_text,
                        'chapter_number': chapter['number'],
                        'chapter_title': chapter['title'],
                        'chunk_index': chunk_global_index,
                        'chapter_chunk_index': local_idx,
                        'total_chapter_chunks': len(chapter_chunks),
                        'book_title': book_title,
                    })
                    chunk_global_index += 1
        else:
            # No chapters detected - chunk entire book with generic metadata
            logger.warning("⚠️ No chapters detected, chunking entire book as one section")
            all_chunks = splitter.split_text(text)
            for idx, chunk_text in enumerate(all_chunks):
                chunks_with_metadata.append({
                    'text': chunk_text,
                    'chapter_number': 0,  # Unknown
                    'chapter_title': 'Unknown Section',
                    'chunk_index': idx,
                    'book_title': book_title,
                })
        
        logger.info(f"📦 Created {len(chunks_with_metadata)} chunks from book")
        return chunks_with_metadata
    
    async def ingest_book(self, pdf_path: str, book_title: str, relationship_id: str = "00000000-0000-0000-0000-000000000000"):
        """
        Main ingestion function.
        
        Args:
            pdf_path: Path to the PDF file
            book_title: Title of the book (used in metadata)
            relationship_id: Relationship ID (default is global)
        """
        logger.info(f"📚 Starting book ingestion: {book_title}")
        logger.info(f"   PDF: {pdf_path}")
        
        # 1. Read PDF
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        logger.info(f"✅ Read PDF: {len(pdf_bytes)} bytes")
        
        # 2. Extract text using OCR
        logger.info("🔍 Extracting text from PDF (this may take a while)...")
        extracted_text = await ocr_service.extract_text_from_pdf(pdf_bytes, filename=os.path.basename(pdf_path))
        logger.info(f"✅ Extracted {len(extracted_text)} characters")
        
        # 3. Detect chapters
        chapters = self.detect_chapters(extracted_text)
        
        # 4. Chunk with chapter metadata
        chunks = self.chunk_with_chapter_metadata(extracted_text, book_title, chapters)
        
        # 5. Generate embeddings and upsert to Pinecone
        logger.info("🧠 Generating embeddings and uploading to Pinecone...")
        
        book_id = str(uuid.uuid4())
        vectors = []
        
        for chunk_data in chunks:
            # Generate embedding for chunk
            embedding = embeddings_service.embed_text(chunk_data['text'])
            
            # Create metadata
            metadata = {
                'book_id': book_id,
                'book_title': book_title,
                'relationship_id': relationship_id,
                'chunk_index': chunk_data['chunk_index'],
                'chapter_number': chunk_data['chapter_number'],
                'chapter_title': chunk_data['chapter_title'],
                'text': chunk_data['text'],  # Store text in metadata for retrieval
                'text_length': len(chunk_data['text']),
                'pdf_type': 'reference_book',  # New type for books
            }
            
            # Add chapter-specific metadata if available
            if 'chapter_chunk_index' in chunk_data:
                metadata['chapter_chunk_index'] = chunk_data['chapter_chunk_index']
                metadata['total_chapter_chunks'] = chunk_data['total_chapter_chunks']
            
            vectors.append({
                'id': f"book_{book_id}_chunk_{chunk_data['chunk_index']}",
                'values': embedding,
                'metadata': metadata
            })
        
        # Upsert in batches (Pinecone has batch size limits)
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            pinecone_service.index.upsert(
                vectors=batch,
                namespace='books'  # Dedicated namespace for reference books
            )
            logger.info(f"   Uploaded batch {i // batch_size + 1}/{(len(vectors) + batch_size - 1) // batch_size}")
        
        logger.info(f"✅ Successfully ingested book: {book_title}")
        logger.info(f"   Book ID: {book_id}")
        logger.info(f"   Total chunks: {len(vectors)}")
        logger.info(f"   Chapters detected: {len(chapters)}")
        logger.info(f"   Namespace: books")
        
        return {
            'book_id': book_id,
            'book_title': book_title,
            'total_chunks': len(vectors),
            'chapters_count': len(chapters),
            'chapters': chapters[:10]  # Return first 10 chapters as preview
        }


async def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/ingest_romance_book.py <pdf_path> <book_title>")
        print('Example: python scripts/ingest_romance_book.py docs/romance_guide.pdf "The Art of Love"')
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    book_title = sys.argv[2]
    
    if not os.path.exists(pdf_path):
        logger.error(f"❌ PDF file not found: {pdf_path}")
        sys.exit(1)
    
    ingester = ChapterAwareBookIngester()
    result = await ingester.ingest_book(pdf_path, book_title)
    
    print("\n" + "=" * 60)
    print("📚 INGESTION COMPLETE")
    print("=" * 60)
    print(f"Book ID: {result['book_id']}")
    print(f"Total Chunks: {result['total_chunks']}")
    print(f"Chapters Found: {result['chapters_count']}")
    print("\nFirst few chapters:")
    for ch in result['chapters']:
        print(f"  Chapter {ch['number']}: {ch['title']}")
    print("\nYou can now query this book in Luna's voice agent!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
