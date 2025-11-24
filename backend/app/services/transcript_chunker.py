"""Transcript chunking module for splitting conversation transcripts into chunks."""
import logging
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class TranscriptChunker:
    """Process conversation transcripts and split into chunks."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        """
        Initialize transcript chunker.
        
        Args:
            chunk_size: Maximum size of text chunks
            chunk_overlap: Overlap between chunks for context preservation
        """
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )
    
    def chunk_transcript(
        self,
        transcript_text: str,
        conflict_id: str,
        relationship_id: str,
        timestamp: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Split transcript text into chunks with metadata.
        
        Args:
            transcript_text: Full transcript text (format: "Speaker: text\nSpeaker: text")
            conflict_id: Conflict ID for this transcript
            relationship_id: Relationship ID
            timestamp: Timestamp of the transcript
            
        Returns:
            List of chunk dictionaries with content and metadata
        """
        if not transcript_text or not transcript_text.strip():
            logger.warning("Empty transcript text provided")
            return []
        
        # Split transcript into chunks
        chunks = self.text_splitter.split_text(transcript_text)
        
        chunk_list = []
        for idx, chunk in enumerate(chunks):
            # Extract speaker information from chunk if present
            speaker = None
            chunk_lines = chunk.split('\n')
            if chunk_lines:
                first_line = chunk_lines[0]
                if ':' in first_line:
                    speaker = first_line.split(':', 1)[0].strip()
            
            chunk_dict = {
                "content": chunk,
                "conflict_id": conflict_id,
                "relationship_id": relationship_id,
                "chunk_index": idx,
                "speaker": speaker or "Unknown",
                "metadata": {
                    "conflict_id": conflict_id,
                    "relationship_id": relationship_id,
                    "chunk_index": idx,
                    "speaker": speaker or "Unknown",
                    "text": chunk,
                }
            }
            
            if timestamp:
                chunk_dict["timestamp"] = timestamp
                chunk_dict["metadata"]["timestamp"] = timestamp
            
            chunk_list.append(chunk_dict)
        
        logger.info(f"Created {len(chunk_list)} chunks from transcript for conflict {conflict_id}")
        return chunk_list

