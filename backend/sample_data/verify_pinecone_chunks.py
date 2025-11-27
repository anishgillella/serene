
import os
import sys
from dotenv import load_dotenv
import logging

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def verify_chunks(conflict_id):
    print(f"🌲 Verifying Pinecone CHUNKS for conflict: {conflict_id}")
    
    try:
        from app.services.pinecone_service import pinecone_service
        
        # Query chunks with filter
        # We need a dummy vector matching Voyage AI dimension (1024)
        dummy_vector = [0.0] * 1024 
        
        results = pinecone_service.index.query(
            vector=dummy_vector,
            top_k=50,
            namespace="transcript_chunks",
            filter={"conflict_id": {"$eq": conflict_id}},
            include_metadata=True
        )
        
        if results and results.matches:
            print(f"\n✅ Found {len(results.matches)} chunks:")
            # Sort by index
            chunks = sorted(results.matches, key=lambda x: x.metadata.get('chunk_index', 0))
            
            for chunk in chunks[:5]: # Show first 5
                meta = chunk.metadata
                print(f"  [{meta.get('chunk_index')}] {meta.get('speaker')}: {meta.get('text')[:50]}...")
            
            if len(chunks) > 5:
                print(f"  ... and {len(chunks)-5} more")
        else:
            print("❌ No chunks found in Pinecone for this conflict")
            
    except Exception as e:
        print(f"❌ Error fetching from Pinecone: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        conflict_id = sys.argv[1]
    else:
        conflict_id = "31defcb5-9fdd-4416-98d6-d965b3214675"
    
    verify_chunks(conflict_id)
