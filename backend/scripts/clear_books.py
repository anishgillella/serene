import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.pinecone_service import pinecone_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("🗑️ Clearing 'books' namespace in Pinecone...")
    try:
        pinecone_service.delete_all_from_namespace("books")
        logger.info("✅ Successfully cleared 'books' namespace")
    except Exception as e:
        logger.error(f"❌ Failed to clear namespace: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
