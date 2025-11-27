import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import logging

# Add parent directory to path to allow importing app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def seed_pinecone():
    """Seed Pinecone with transcripts from seeded conflicts"""
    print("🌲 Seeding Pinecone with transcripts...")
    
    try:
        # Initialize services
        from app.services.pinecone_service import pinecone_service
        from app.services.embeddings_service import embeddings_service
        
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        RELATIONSHIP_ID = "00000000-0000-0000-0000-000000000000"
        
        # Get all conflicts
        cursor.execute("""
            SELECT id, started_at, status
            FROM conflicts
            WHERE relationship_id = %s;
        """, (RELATIONSHIP_ID,))
        
        conflicts = cursor.fetchall()
        print(f"   Found {len(conflicts)} conflicts to process")
        
        for conflict in conflicts:
            conflict_id = str(conflict['id'])
            
            # Get rant messages for this conflict
            cursor.execute("""
                SELECT partner_id, content, role
                FROM rant_messages
                WHERE conflict_id = %s
                ORDER BY created_at;
            """, (conflict_id,))
            
            rants = cursor.fetchall()
            
            if not rants:
                print(f"   ⚠️ Skipping conflict {conflict_id[:8]} (no rants)")
                continue
                
            # Construct transcript text
            transcript_lines = []
            for rant in rants:
                speaker = "Adrian Malhotra" if rant['partner_id'] == "partner_a" else "Elara Voss"
                transcript_lines.append(f"{speaker}: {rant['content']}")
            
            full_transcript = "\n\n".join(transcript_lines)
            
            # Generate embedding
            print(f"   🔄 Embedding transcript for {conflict_id[:8]}...")
            embedding = embeddings_service.embed_query(full_transcript)
            
            # Prepare data for Pinecone
            transcript_data = {
                "conflict_id": conflict_id,
                "relationship_id": RELATIONSHIP_ID,
                "timestamp": conflict['started_at'],
                "duration": 300, # Dummy duration
                "partner_a_id": "partner_a",
                "partner_b_id": "partner_b",
                "transcript_text": full_transcript,
                "speaker_labels": {"partner_a": "Adrian", "partner_b": "Elara"}
            }
            
            # Upsert to Pinecone (Full Transcript)
            pinecone_service.upsert_transcript(
                conflict_id=conflict_id,
                embedding=embedding,
                transcript_data=transcript_data
            )
            print(f"   ✅ Upserted full transcript for {conflict_id[:8]}")
            
            # Create and Upsert Chunks
            chunks = []
            chunk_embeddings = []
            
            for idx, rant in enumerate(rants):
                speaker = "Adrian Malhotra" if rant['partner_id'] == "partner_a" else "Elara Voss"
                content = f"{speaker}: {rant['content']}"
                
                # Embed chunk
                chunk_embedding = embeddings_service.embed_text(content)
                chunk_embeddings.append(chunk_embedding)
                
                chunks.append({
                    "conflict_id": conflict_id,
                    "relationship_id": RELATIONSHIP_ID,
                    "chunk_index": idx,
                    "speaker": speaker,
                    "content": content,
                    "timestamp": conflict['started_at'], # Ideally use message timestamp if available
                    "metadata": {
                        "role": rant['role']
                    }
                })
            
            if chunks:
                print(f"   🔄 Upserting {len(chunks)} chunks for {conflict_id[:8]}...")
                pinecone_service.upsert_transcript_chunks(
                    chunks=chunks,
                    embeddings=chunk_embeddings
                )
                print(f"   ✅ Upserted chunks for {conflict_id[:8]}")
            
        conn.close()
        print("\n✅ Pinecone seeding complete!")
        
    except Exception as e:
        print(f"❌ Error seeding Pinecone: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    seed_pinecone()
