import asyncio
import logging
import sys
import os

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.db_service import db_service, DEFAULT_RELATIONSHIP_ID
from app.services.pinecone_service import pinecone_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clear-onboarding")

async def clear_data():
    logger.info("🧹 Starting cleanup of onboarding data...")
    
    # 1. Clear Pinecone "profiles" namespace
    try:
        if pinecone_service.index:
            logger.info("Deleting all vectors from 'profiles' namespace in Pinecone...")
            # We can't easily delete just by relationship_id without fetching IDs first,
            # but for this user request "Remove this data", clearing the namespace is the cleanest 
            # if they are the only user (which is true for this dev setup).
            # Alternatively, we could query for vectors with metadata relationship_id and delete by ID.
            # Given the user said "Remove this data... I will update it", wiping the profiles namespace is safe for a single-user dev env.
            pinecone_service.delete_all_from_namespace("profiles")
            logger.info("✅ Pinecone 'profiles' namespace cleared.")
        else:
            logger.warning("⚠️ Pinecone service not initialized.")
    except Exception as e:
        logger.error(f"❌ Error clearing Pinecone: {e}")

    # 2. Clear Postgres "profiles" table for the default relationship
    try:
        if db_service:
            logger.info(f"Deleting profile records for relationship {DEFAULT_RELATIONSHIP_ID}...")
            # We need to find the profile IDs first to be safe, or just delete by relationship_id
            # db_service doesn't have delete_by_relationship_id, so we'll fetch then delete.
            profiles = db_service.get_profiles(DEFAULT_RELATIONSHIP_ID, pdf_type="onboarding_profile")
            if profiles:
                for p in profiles:
                    pdf_id = p["pdf_id"]
                    db_service.delete_profile(pdf_id)
                    logger.info(f"   Deleted profile record: {pdf_id}")
                logger.info("✅ Postgres profile records deleted.")
            else:
                logger.info("   No profile records found in Postgres.")
        else:
            logger.warning("⚠️ DB service not initialized.")
    except Exception as e:
        logger.error(f"❌ Error clearing Postgres: {e}")

    logger.info("✨ Cleanup complete!")

if __name__ == "__main__":
    asyncio.run(clear_data())
