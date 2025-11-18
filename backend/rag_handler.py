"""RAG (Retrieval-Augmented Generation) for Amara's knowledge base."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
import pypdf

# Try importing chroma with fallback
try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    logging.warning("chromadb not installed. RAG features will be limited.")

logger = logging.getLogger(__name__)

# Load environment
load_dotenv(Path(__file__).parent.parent / ".env")

VECTOR_STORE_PATH = os.environ.get("VECTOR_STORE_PATH", "backend/vector_store")
PDF_PATH = os.environ.get("PLACEHOLDER_PDF", "Voice Agent.pdf")


class AmareKnowledgeBase:
    """Retrieval-Augmented Generation for Amara's profile."""
    
    def __init__(self):
        self.client = None
        self.collection = None
        self.documents = []
        self.initialized = False
        
        if CHROMA_AVAILABLE:
            self._initialize_chroma()
        else:
            logger.warning("RAG disabled - chromadb not available")
    
    def _initialize_chroma(self) -> None:
        """Initialize Chroma vector database."""
        try:
            # Create persistent client
            os.makedirs(VECTOR_STORE_PATH, exist_ok=True)
            self.client = chromadb.PersistentClient(path=VECTOR_STORE_PATH)
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="amara_profile",
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info("✅ Chroma initialized")
            self.initialized = True
            
            # Load documents if collection is empty
            if self.collection.count() == 0:
                self._load_pdf()
                
        except Exception as e:
            logger.error(f"Error initializing Chroma: {e}")
            self.initialized = False
    
    def _load_pdf(self) -> None:
        """Load Amara's PDF into vector database."""
        try:
            pdf_file = Path(__file__).parent.parent / PDF_PATH
            
            if not pdf_file.exists():
                logger.warning(f"PDF not found: {pdf_file}")
                return
            
            logger.info(f"Loading PDF: {pdf_file}")
            
            # Extract text from PDF
            reader = pypdf.PdfReader(str(pdf_file))
            full_text = ""
            
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                full_text += f"\n--- Page {page_num + 1} ---\n{text}"
            
            # Split into chunks (rough chunking)
            chunks = self._chunk_text(full_text, chunk_size=1000, overlap=200)
            
            # Add to Chroma
            ids = [f"chunk_{i}" for i in range(len(chunks))]
            self.collection.add(
                ids=ids,
                documents=chunks,
                metadatas=[{"source": "amara_profile.pdf", "chunk": i} for i in range(len(chunks))],
            )
            
            logger.info(f"✅ Loaded {len(chunks)} chunks from PDF")
            self.documents = chunks
            
        except Exception as e:
            logger.error(f"Error loading PDF: {e}")
    
    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk.strip())
            start = end - overlap
        
        return chunks
    
    async def retrieve(self, query: str, top_k: int = 3) -> list[str]:
        """Retrieve relevant documents for a query.
        
        Args:
            query: The user's question or statement
            top_k: Number of results to return
            
        Returns:
            List of relevant text chunks about Amara
        """
        if not self.initialized or not self.collection:
            logger.warning("RAG not initialized, returning empty context")
            return []
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
            )
            
            if results and results["documents"]:
                documents = results["documents"][0]
                logger.info(f"Retrieved {len(documents)} documents for: {query[:50]}...")
                return documents
            
            return []
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []
    
    async def get_context(self, user_message: str) -> str:
        """Get context about Amara for the LLM.
        
        Args:
            user_message: What the user said
            
        Returns:
            Formatted context string about Amara
        """
        relevant_docs = await self.retrieve(user_message, top_k=2)
        
        if not relevant_docs:
            return ""
        
        context = "## Context about Amara:\n"
        for i, doc in enumerate(relevant_docs, 1):
            context += f"\n{i}. {doc[:500]}...\n"
        
        return context


# Global instance
amara_kb = AmareKnowledgeBase()


async def get_amara_context(user_message: str) -> str:
    """Get relevant context about Amara for a user message."""
    return await amara_kb.get_context(user_message)
