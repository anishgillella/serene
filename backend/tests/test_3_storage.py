"""
Test 3: Supabase Storage
========================

Purpose:
    Tests cloud storage functionality for transcript JSON files.
    Verifies upload, download, list, and delete operations.

What This Tests:
    - Connection to Supabase Storage
    - Creating/uploading files to 'transcripts' bucket
    - Downloading files from storage
    - Listing bucket contents
    - Deleting files (cleanup)

Expected Result:
    ✅ All storage operations succeed
    ✅ Files can be uploaded and retrieved
    ✅ Cleanup removes test data
"""
from dotenv import load_dotenv
import os
import json
load_dotenv()

from supabase import create_client

def test_storage():
    print("=" * 50)
    print("TEST 3: Supabase Storage")
    print("=" * 50)
    
    # Connect
    print("\n1. Connecting to Supabase Storage...")
    try:
        client = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_KEY')
        )
        print("   ✅ Connected successfully")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False
    
    # List buckets
    print("\n2. Listing storage buckets...")
    try:
        buckets = client.storage.list_buckets()
        bucket_names = [b.name for b in buckets]
        print(f"   ✅ Found {len(buckets)} buckets: {bucket_names}")
        
        if 'transcripts' not in bucket_names:
            print("   ⚠️  'transcripts' bucket not found!")
            print("   Run: python setup_db.py to create it")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Upload test file
    print("\n3. Testing file upload...")
    try:
        test_data = {
            "test": True,
            "transcripts": [
                {"speaker": "Speaker 1", "text": "This is a test", "timestamp": 123.45}
            ]
        }
        test_path = "test/test_transcript.json"
        
        client.storage.from_('transcripts').upload(
            test_path,
            json.dumps(test_data).encode('utf-8'),
            {"content-type": "application/json"}
        )
        print(f"   ✅ File uploaded to: {test_path}")
    except Exception as e:
        print(f"   ❌ Upload failed: {e}")
        return False
    
    # Download file
    print("\n4. Testing file download...")
    try:
        downloaded = client.storage.from_('transcripts').download(test_path)
        downloaded_data = json.loads(downloaded.decode('utf-8'))
        
        if downloaded_data == test_data:
            print("   ✅ File downloaded and verified")
        else:
            print("   ❌ Downloaded data doesn't match uploaded data")
            return False
    except Exception as e:
        print(f"   ❌ Download failed: {e}")
        return False
    
    # List files
    print("\n5. Testing file listing...")
    try:
        files = client.storage.from_('transcripts').list('test/')
        print(f"   ✅ Found {len(files)} files in test/ folder")
    except Exception as e:
        print(f"   ❌ Listing failed: {e}")
        return False
    
    # Delete file (cleanup)
    print("\n6. Testing file deletion (cleanup)...")
    try:
        client.storage.from_('transcripts').remove([test_path])
        print("   ✅ Test file deleted successfully")
    except Exception as e:
        print(f"   ❌ Deletion failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ Storage: ALL TESTS PASSED")
    print("=" * 50)
    return True

if __name__ == "__main__":
    test_storage()
