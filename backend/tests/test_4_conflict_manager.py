"""
Test 4: ConflictManager Service
================================

Purpose:
    Tests the ConflictManager service that handles conflict recording lifecycle.
    This is the core business logic for saving and managing conflict sessions.

What This Tests:
    - Starting a new conflict recording
    - Adding transcript segments
    - Ending a conflict (saves to DB + Storage)
    - Data integrity (DB record + JSON file match)

Expected Result:
    ✅ Conflict starts successfully
    ✅ Transcripts are buffered correctly
    ✅ Conflict ends and saves data to both:
        - PostgreSQL (conflicts table)
        - Storage (JSON file)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.services.conflict_manager import ConflictManager
from supabase import create_client
import asyncio
import json

async def test_conflict_manager():
    print("=" * 50)
    print("TEST 4: ConflictManager Service")
    print("=" * 50)
    
    # Initialize
    print("\n1. Initializing ConflictManager...")
    try:
        manager = ConflictManager()
        print("   ✅ ConflictManager initialized")
    except Exception as e:
        print(f"   ❌ Initialization failed: {e}")
        return False
    
    # Start conflict
    print("\n2. Starting conflict recording...")
    try:
        await manager.start_conflict()
        conflict_id = manager.current_conflict_id
        print(f"   ✅ Conflict started, ID: {conflict_id}")
    except Exception as e:
        print(f"   ❌ Start failed: {e}")
        return False
    
    # Add transcripts
    print("\n3. Adding transcript segments...")
    try:
        manager.add_transcript("Speaker 1", "This is a test transcript", 1.0)
        manager.add_transcript("Speaker 2", "Another test message", 2.5)
        manager.add_transcript("Speaker 1", "Final test message", 5.0)
        print(f"   ✅ Added {len(manager.transcripts)} transcript segments")
    except Exception as e:
        print(f"   ❌ Adding transcripts failed: {e}")
        return False
    
    # End conflict
    print("\n4. Ending conflict (saves to DB + Storage)...")
    try:
        await manager.end_conflict()
        print("   ✅ Conflict ended successfully")
    except Exception as e:
        print(f"   ❌ End conflict failed: {e}")
        return False
    
    # Verify in database
    print("\n5. Verifying data in database...")
    try:
        client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
        result = client.table('conflicts').select('*').eq('id', conflict_id).execute()
        
        if len(result.data) == 1:
            conflict_record = result.data[0]
            print(f"   ✅ Found conflict in database")
            print(f"      Status: {conflict_record['status']}")
            print(f"      Transcript path: {conflict_record['transcript_path']}")
        else:
            print("   ❌ Conflict not found in database")
            return False
    except Exception as e:
        print(f"   ❌ Database verification failed: {e}")
        return False
    
    # Verify in storage
    print("\n6. Verifying transcript file in storage...")
    try:
        transcript_path = conflict_record['transcript_path']
        downloaded = client.storage.from_('transcripts').download(transcript_path)
        transcript_data = json.loads(downloaded.decode('utf-8'))
        
        if len(transcript_data) == 3:
            print(f"   ✅ Transcript file found with {len(transcript_data)} segments")
            print(f"      Sample: {transcript_data[0]}")
        else:
            print("   ❌ Transcript file has wrong number of segments")
            return False
    except Exception as e:
        print(f"   ❌ Storage verification failed: {e}")
        return False
    
    # Cleanup
    print("\n7. Cleaning up test data...")
    try:
        client.table('conflicts').delete().eq('id', conflict_id).execute()
        client.storage.from_('transcripts').remove([transcript_path])
        print("   ✅ Test data cleaned up")
    except Exception as e:
        print(f"   ⚠️  Cleanup warning: {e}")
    
    print("\n" + "=" * 50)
    print("✅ ConflictManager: ALL TESTS PASSED")
    print("=" * 50)
    return True

if __name__ == "__main__":
    asyncio.run(test_conflict_manager())
