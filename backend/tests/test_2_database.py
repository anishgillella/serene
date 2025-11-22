"""
Test 2: Database (Supabase PostgreSQL)
======================================

Purpose:
    Tests database connectivity and all CRUD operations.
    Verifies that the HeartSync database schema is properly configured.

What This Tests:
    - Connection to Supabase PostgreSQL
    - 'relationships' table is accessible
    - 'conflicts' table is accessible
    - INSERT operations (create new conflicts)
    - UPDATE operations (modify existing records)
    - DELETE operations (cleanup test data)

Expected Result:
    ✅ Database connection succeeds
    ✅ Both tables are accessible
    ✅ All CRUD operations work correctly
    ✅ Test data is cleaned up after

Prerequisites:
    - SUPABASE_URL and SUPABASE_KEY in .env
    - Tables created (run: python setup_db.py)
    - RLS disabled or proper GRANT permissions applied
"""
from dotenv import load_dotenv
import os
load_dotenv()

from supabase import create_client
import uuid
from datetime import datetime

def test_database():
    print("=" * 50)
    print("TEST 2: Database (Supabase PostgreSQL)")
    print("=" * 50)
    
    # Connect
    print("\n1. Connecting to database...")
    try:
        client = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_KEY')
        )
        print("   ✅ Connected successfully")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False
    
    # Test relationships table
    print("\n2. Testing 'relationships' table...")
    try:
        result = client.table('relationships').select('*').limit(5).execute()
        print(f"   ✅ Table accessible, found {len(result.data)} relationships")
        if result.data:
            print(f"   Sample: {result.data[0]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test conflicts table
    print("\n3. Testing 'conflicts' table...")
    try:
        result = client.table('conflicts').select('*').limit(5).execute()
        print(f"   ✅ Table accessible, found {len(result.data)} conflicts")
        if result.data:
            print(f"   Sample: {result.data[0]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test INSERT (create test conflict)
    print("\n4. Testing INSERT operation...")
    try:
        test_conflict_id = str(uuid.uuid4())
        default_relationship_id = "00000000-0000-0000-0000-000000000000"
        
        insert_data = {
            "id": test_conflict_id,
            "relationship_id": default_relationship_id,
            "started_at": datetime.now().isoformat(),
            "status": "test"
        }
        
        client.table('conflicts').insert(insert_data).execute()
        print(f"   ✅ INSERT successful, conflict_id: {test_conflict_id}")
    except Exception as e:
        print(f"   ❌ INSERT failed: {e}")
        return False
    
    # Test UPDATE
    print("\n5. Testing UPDATE operation...")
    try:
        client.table('conflicts').update({
            "status": "completed",
            "ended_at": datetime.now().isoformat()
        }).eq("id", test_conflict_id).execute()
        print("   ✅ UPDATE successful")
    except Exception as e:
        print(f"   ❌ UPDATE failed: {e}")
        return False
    
    # Test DELETE (cleanup)
    print("\n6. Testing DELETE operation (cleanup)...")
    try:
        client.table('conflicts').delete().eq("id", test_conflict_id).execute()
        print("   ✅ DELETE successful (test data cleaned up)")
    except Exception as e:
        print(f"   ❌ DELETE failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ Database: ALL TESTS PASSED")
    print("=" * 50)
    return True

if __name__ == "__main__":
    test_database()
