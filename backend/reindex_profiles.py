import asyncio
import os
import sys
from dotenv import load_dotenv

# Load env vars FIRST before importing app modules that rely on them
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.db_service import db_service
from app.services.embeddings_service import embeddings_service
from app.services.pinecone_service import pinecone_service
from app.routes.onboarding import process_onboarding_background
from app.schemas.onboarding import OnboardingSubmission, PartnerProfileInput, RelationshipProfileInput

# Mock submission object to reuse the logic
class MockSubmission:
    def __init__(self, rel_id, p_id, p_data, r_data):
        self.relationship_id = rel_id
        self.partner_id = p_id
        self.partner_profile = p_data
        self.relationship_profile = r_data

async def reindex_all_profiles():
    print("🔄 Starting profile re-indexing...")
    
    # 1. Fetch all partner profiles from Postgres
    # We need a method to list all, or we can just iterate if we had IDs.
    # Since db_service doesn't have "get_all", we might need to add it or just use raw query.
    # For now, let's add a raw query here to get all data.
    
    try:
        with db_service.get_db_context() as conn:
            with conn.cursor() as cur:
                # Fetch individual columns + metadata
                cur.execute("""
                    SELECT 
                        relationship_id, partner_id, name, role, age, 
                        communication_style, stress_triggers, soothing_mechanisms, 
                        background_story, metadata 
                    FROM partner_profiles
                """)
                partners = cur.fetchall()
                
                # Fetch relationship profiles (assuming similar structure or just metadata)
                cur.execute("SELECT relationship_id, recurring_arguments, shared_goals, relationship_dynamic, metadata FROM relationship_profiles")
                relationships = {}
                for row in cur.fetchall():
                    relationships[row[0]] = {
                        "recurring_arguments": row[1],
                        "shared_goals": row[2],
                        "relationship_dynamic": row[3],
                        "metadata": row[4]
                    }
            
        print(f"found {len(partners)} partner profiles to re-index.")
        
        for row in partners:
            rel_id = row[0]
            partner_id = row[1]
            print(f"Processing {rel_id} - {partner_id}...")
            
            # Construct partner data from columns + metadata
            metadata = row[9] or {}
            
            p_data = {
                "name": row[2],
                "role": row[3],
                "age": row[4],
                "communication_style": row[5],
                "stress_triggers": row[6] or [],
                "soothing_mechanisms": row[7] or [],
                "background_story": row[8],
                # Merge metadata fields which contain the detailed info
                **metadata
            }
            
            # Get matching relationship profile
            r_data_raw = relationships.get(rel_id, {})
            r_data = {
                "recurring_arguments": r_data_raw.get("recurring_arguments", []),
                "shared_goals": r_data_raw.get("shared_goals", []),
                "relationship_dynamic": r_data_raw.get("relationship_dynamic"),
                # Merge metadata
                **(r_data_raw.get("metadata", {}) or {})
            }
            
            # Parse into Pydantic models
            try:
                p_profile = PartnerProfileInput(**p_data)
                r_profile = RelationshipProfileInput(**r_data)
                
                # Create submission object
                submission = MockSubmission(rel_id, partner_id, p_profile, r_profile)
                
                # Run the chunking logic
                await process_onboarding_background(submission)
                print(f"  ✅ Re-indexed successfully.")
                
            except Exception as e:
                print(f"  ❌ Failed to parse/index: {e}")
                
        print("\n✨ Re-indexing complete!")
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(reindex_all_profiles())
