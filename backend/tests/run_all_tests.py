"""
Backend Component Test Suite
============================

Purpose:
    Master test runner that executes all individual component tests.
    Provides a comprehensive health check of the entire backend system.

Components Tested:
    1. FastAPI Server - API endpoints and token generation
    2. Database - PostgreSQL CRUD operations
    3. Storage - Supabase Storage file operations
    4. ConflictManager - Business logic and data flow
    5. LiveKit - Cloud connectivity and token validation

Usage:
    python tests/run_all_tests.py

Expected Result:
    ✅ All 5 component tests pass
    📊 Summary report showing test results
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_all_tests():
    print("\n" + "=" * 60)
    print("HEARTSYNC BACKEND - COMPONENT TEST SUITE")
    print("=" * 60)
    print("\nRunning all component tests...")
    print("This will verify:")
    print("  ✓ FastAPI Server")
    print("  ✓ Database (Supabase PostgreSQL)")
    print("  ✓ Storage (Supabase Storage)")
    print("  ✓ ConflictManager Service")
    print("  ✓ LiveKit Connectivity")
    print()
    
    results = {}
    
    # Test 1: FastAPI
    print("\n" + "🔹" * 30)
    try:
        from tests.test_1_fastapi import test_fastapi
        results['FastAPI'] = test_fastapi()
    except Exception as e:
        print(f"❌ FastAPI test crashed: {e}")
        results['FastAPI'] = False
    
    # Test 2: Database
    print("\n" + "🔹" * 30)
    try:
        from tests.test_2_database import test_database
        results['Database'] = test_database()
    except Exception as e:
        print(f"❌ Database test crashed: {e}")
        results['Database'] = False
    
    # Test 3: Storage
    print("\n" + "🔹" * 30)
    try:
        from tests.test_3_storage import test_storage
        results['Storage'] = test_storage()
    except Exception as e:
        print(f"❌ Storage test crashed: {e}")
        results['Storage'] = False
    
    # Test 4: ConflictManager
    print("\n" + "🔹" * 30)
    try:
        import asyncio
        from tests.test_4_conflict_manager import test_conflict_manager
        results['ConflictManager'] = asyncio.run(test_conflict_manager())
    except Exception as e:
        print(f"❌ ConflictManager test crashed: {e}")
        results['ConflictManager'] = False
    
    # Test 5: LiveKit
    print("\n" + "🔹" * 30)
    try:
        from tests.test_5_livekit import test_livekit
        results['LiveKit'] = test_livekit()
    except Exception as e:
        print(f"❌ LiveKit test crashed: {e}")
        results['LiveKit'] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for component, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{component:20} {status}")
    
    print("\n" + "-" * 60)
    print(f"Total: {passed}/{total} tests passed")
    print("-" * 60)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Backend is fully operational.")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check output above for details.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
