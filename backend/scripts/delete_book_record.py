import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.db_service import db_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("🗑️ Removing book record from SQL database...")
    
    # 1. Find the book record
    try:
        profiles = db_service.get_profiles(
            relationship_id="00000000-0000-0000-0000-000000000000",
            pdf_type="reference_book"
        )
        
        book_to_delete = None
        for p in profiles:
            if "It Ends with Us" in p.get("filename", ""):
                book_to_delete = p
                break
        
        if not book_to_delete:
            logger.warning("⚠️ Book 'It Ends with Us' not found in database.")
            return

        pdf_id = book_to_delete["pdf_id"]
        logger.info(f"   Found book: {book_to_delete['filename']} (ID: {pdf_id})")
        
        # 2. Delete it
        success = db_service.delete_profile(pdf_id)
        
        if success:
            logger.info("✅ Successfully deleted book record from SQL database.")
        else:
            logger.error("❌ Failed to delete book record.")
            
    except Exception as e:
        logger.error(f"❌ Error during deletion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
