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
    logger.info("🗑️ Removing empty 'Boyfriend Profile' record...")
    
    try:
        # Get all profiles
        profiles = db_service.get_profiles(
            relationship_id="00000000-0000-0000-0000-000000000000"
        )
        
        deleted_count = 0
        for p in profiles:
            # Check for empty boyfriend profile
            if p.get("pdf_type") == "boyfriend_profile" and p.get("extracted_text_length", 0) == 0:
                pdf_id = p["pdf_id"]
                logger.info(f"   Found empty profile: {p.get('filename')} (ID: {pdf_id})")
                
                if db_service.delete_profile(pdf_id):
                    logger.info("   ✅ Deleted record")
                    deleted_count += 1
                else:
                    logger.error("   ❌ Failed to delete record")
        
        if deleted_count == 0:
            logger.info("⚠️ No empty boyfriend profiles found.")
        else:
            logger.info(f"✅ Cleanup complete. Removed {deleted_count} empty records.")
            
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
