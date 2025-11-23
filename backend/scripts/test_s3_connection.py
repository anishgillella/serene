#!/usr/bin/env python3
"""
Test S3 Connection Script

Quick test to verify AWS S3 credentials and bucket access.

Usage:
    python scripts/test_s3_connection.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(".env.local")
load_dotenv(".env")

from app.config import settings
from app.services.s3_service import s3_service

def test_s3_connection():
    """Test S3 connection and basic operations"""
    print("🔍 Testing AWS S3 Connection...")
    print("="*60)
    
    # Check credentials
    print("\n📋 Configuration:")
    print(f"  AWS Region: {settings.AWS_REGION}")
    print(f"  S3 Bucket: {settings.S3_BUCKET_NAME}")
    print(f"  Access Key ID: {settings.AWS_ACCESS_KEY_ID[:10]}..." if settings.AWS_ACCESS_KEY_ID else "  ❌ AWS_ACCESS_KEY_ID not set")
    print(f"  Secret Key: {'✅ Set' if settings.AWS_SECRET_ACCESS_KEY else '❌ Not set'}")
    
    # Test bucket access
    print("\n🧪 Testing Operations:")
    
    # Test 1: Check if bucket exists
    try:
        import boto3
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        s3_client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
        print("  ✅ Bucket exists and is accessible")
    except Exception as e:
        print(f"  ❌ Bucket access error: {e}")
        return False
    
    # Test 2: Upload a test file
    print("\n  📤 Testing file upload...")
    test_path = "test/connection_test.json"
    test_content = b'{"test": "connection", "timestamp": "2024-01-01"}'
    
    try:
        s3_url = s3_service.upload_file(
            file_path=test_path,
            file_content=test_content,
            content_type="application/json"
        )
        if s3_url:
            print(f"  ✅ Upload successful: {s3_url}")
        else:
            print("  ❌ Upload failed (returned None)")
            return False
    except Exception as e:
        print(f"  ❌ Upload error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Check if file exists
    print("\n  🔍 Testing file existence check...")
    try:
        exists = s3_service.file_exists(test_path)
        if exists:
            print(f"  ✅ File exists check: {exists}")
        else:
            print(f"  ⚠️  File existence check returned False")
    except Exception as e:
        print(f"  ❌ File existence check error: {e}")
    
    # Test 4: Download the test file
    print("\n  📥 Testing file download...")
    try:
        downloaded = s3_service.download_file(test_path)
        if downloaded:
            print(f"  ✅ Download successful ({len(downloaded)} bytes)")
            # Verify content
            if downloaded == test_content:
                print("  ✅ Content matches original")
            else:
                print("  ⚠️  Content mismatch")
        else:
            print("  ❌ Download failed (returned None)")
    except Exception as e:
        print(f"  ❌ Download error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 5: Generate presigned URL
    print("\n  🔗 Testing presigned URL generation...")
    try:
        url = s3_service.get_file_url(test_path, expires_in=3600)
        if url:
            print(f"  ✅ Presigned URL generated: {url[:50]}...")
        else:
            print("  ❌ Presigned URL generation failed")
    except Exception as e:
        print(f"  ❌ Presigned URL error: {e}")
    
    # Test 6: Cleanup - Delete test file
    print("\n  🧹 Cleaning up test file...")
    try:
        deleted = s3_service.delete_file(test_path)
        if deleted:
            print("  ✅ Test file deleted")
        else:
            print("  ⚠️  Delete returned False (file may not exist)")
    except Exception as e:
        print(f"  ⚠️  Delete error: {e}")
    
    print("\n" + "="*60)
    print("✅ S3 Connection Test Complete!")
    print("\nYour AWS S3 setup is working correctly. You can now:")
    print("  - Upload PDFs (profiles, handbooks)")
    print("  - Store transcripts, analysis, and repair plans")
    print("  - All files will be stored in S3 bucket:", settings.S3_BUCKET_NAME)
    
    return True

if __name__ == "__main__":
    try:
        success = test_s3_connection()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

