import os
import sys
from dotenv import load_dotenv
import logging

# Add parent directory to path to allow importing app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def verify_pinecone_content(conflict_id):
    """Fetch and print transcript content from Pinecone"""
    print(f"🌲 Verifying Pinecone content for conflict: {conflict_id}")
    
    try:
        from app.services.pinecone_service import pinecone_service
        
        result = pinecone_service.get_by_conflict_id(
            conflict_id=conflict_id,
            namespace="transcripts"
        )
        
        if result and result.metadata:
            print("\n✅ Found transcript metadata:")
            transcript_text = result.metadata.get("transcript_text", "")
            print("-" * 40)
            print(transcript_text)
            print("-" * 40)
            print(f"Length: {len(transcript_text)} chars")
        else:
            print("❌ No transcript found in Pinecone")
            
    except Exception as e:
        print(f"❌ Error fetching from Pinecone: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        conflict_id = sys.argv[1]
    else:
        conflict_id = "31defcb5-9fdd-4416-98d6-d965b3214675" # Default to most recent
    
    verify_pinecone_content(conflict_id)
