#!/usr/bin/env python3
"""
Check if boyfriend and girlfriend profile PDFs are stored in Pinecone
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(".env.local")
load_dotenv(".env")

from app.services.pinecone_service import pinecone_service
from app.services.embeddings_service import embeddings_service

def check_profiles():
    """Check what profiles exist in Pinecone"""
    if not pinecone_service.index:
        print("❌ Pinecone not initialized")
        return
    
    print("🔍 Checking Pinecone for profile PDFs...")
    print("=" * 60)
    
    # Create a dummy query vector (1024 dimensions for Voyage-3)
    dummy_vector = [0.0] * 1024
    
    # Check for boyfriend profiles (any relationship_id)
    print("\n📋 Checking for boyfriend_profile PDFs...")
    try:
        boyfriend_results = pinecone_service.index.query(
            vector=dummy_vector,
            top_k=10,
            namespace="profiles",
            include_metadata=True,
            filter={
                "pdf_type": {"$eq": "boyfriend_profile"}
            }
        )
        
        if boyfriend_results.matches:
            print(f"✅ Found {len(boyfriend_results.matches)} boyfriend profile(s):")
            for i, match in enumerate(boyfriend_results.matches, 1):
                metadata = match.metadata
                print(f"\n  {i}. PDF ID: {metadata.get('pdf_id', 'N/A')}")
                print(f"     Filename: {metadata.get('filename', 'N/A')}")
                print(f"     Relationship ID: {metadata.get('relationship_id', 'N/A')}")
                print(f"     Text Length: {metadata.get('text_length', 0)} chars")
                if metadata.get('extracted_text'):
                    preview = metadata['extracted_text'][:200]
                    print(f"     Preview: {preview}...")
        else:
            print("❌ No boyfriend profiles found")
    except Exception as e:
        print(f"❌ Error querying boyfriend profiles: {e}")
    
    # Check for girlfriend profiles (any relationship_id)
    print("\n📋 Checking for girlfriend_profile PDFs...")
    try:
        girlfriend_results = pinecone_service.index.query(
            vector=dummy_vector,
            top_k=10,
            namespace="profiles",
            include_metadata=True,
            filter={
                "pdf_type": {"$eq": "girlfriend_profile"}
            }
        )
        
        if girlfriend_results.matches:
            print(f"✅ Found {len(girlfriend_results.matches)} girlfriend profile(s):")
            for i, match in enumerate(girlfriend_results.matches, 1):
                metadata = match.metadata
                print(f"\n  {i}. PDF ID: {metadata.get('pdf_id', 'N/A')}")
                print(f"     Filename: {metadata.get('filename', 'N/A')}")
                print(f"     Relationship ID: {metadata.get('relationship_id', 'N/A')}")
                print(f"     Text Length: {metadata.get('text_length', 0)} chars")
                if metadata.get('extracted_text'):
                    preview = metadata['extracted_text'][:200]
                    print(f"     Preview: {preview}...")
        else:
            print("❌ No girlfriend profiles found")
    except Exception as e:
        print(f"❌ Error querying girlfriend profiles: {e}")
    
    # Check default relationship_id specifically
    print("\n📋 Checking for profiles with default relationship_id...")
    default_rel_id = "00000000-0000-0000-0000-000000000000"
    try:
        default_results = pinecone_service.index.query(
            vector=dummy_vector,
            top_k=10,
            namespace="profiles",
            include_metadata=True,
            filter={
                "relationship_id": {"$eq": default_rel_id}
            }
        )
        
        if default_results.matches:
            print(f"✅ Found {len(default_results.matches)} profile(s) for default relationship:")
            for i, match in enumerate(default_results.matches, 1):
                metadata = match.metadata
                print(f"\n  {i}. Type: {metadata.get('pdf_type', 'N/A')}")
                print(f"     PDF ID: {metadata.get('pdf_id', 'N/A')}")
                print(f"     Filename: {metadata.get('filename', 'N/A')}")
        else:
            print(f"❌ No profiles found for relationship_id: {default_rel_id}")
    except Exception as e:
        print(f"❌ Error querying default relationship profiles: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Profile check complete")

if __name__ == "__main__":
    check_profiles()

