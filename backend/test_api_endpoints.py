"""
Test API endpoints for Phase 2
Run: python test_api_endpoints.py
Note: Requires backend server running on port 8000
"""
import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_analyze_endpoint():
    """Test POST /api/post-fight/conflicts/{conflict_id}/analyze"""
    print("\n" + "="*60)
    print("TEST: Analyze Conflict Endpoint")
    print("="*60)
    
    # First, we need a conflict_id that exists in Pinecone
    # Use the test conflict from previous test
    conflict_id = "test-conflict-001"
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/post-fight/conflicts/{conflict_id}/analyze",
            json={"partner_id": "partner_a"},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Analyze endpoint working!")
            print(f"   Success: {data.get('success')}")
            if 'analysis' in data:
                analysis = data['analysis']
                print(f"   Summary: {analysis.get('fight_summary', '')[:80]}...")
                print(f"   Root causes: {len(analysis.get('root_causes', []))}")
            return True
        else:
            print(f"❌ Analyze endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to backend. Is it running on {BASE_URL}?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_repair_plan_endpoint():
    """Test POST /api/post-fight/conflicts/{conflict_id}/repair-plan"""
    print("\n" + "="*60)
    print("TEST: Repair Plan Endpoint")
    print("="*60)
    
    conflict_id = "test-conflict-001"
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/post-fight/conflicts/{conflict_id}/repair-plan",
            json={"partner_id": "partner_a"},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Repair plan endpoint working!")
            print(f"   Success: {data.get('success')}")
            if 'repair_plan' in data:
                plan = data['repair_plan']
                print(f"   Partner: {plan.get('partner_requesting')}")
                print(f"   Steps: {len(plan.get('steps', []))}")
                print(f"   Apology script: {plan.get('apology_script', '')[:80]}...")
            return True
        else:
            print(f"❌ Repair plan endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to backend. Is it running on {BASE_URL}?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_rant_endpoint():
    """Test POST /api/post-fight/conflicts/{conflict_id}/rant"""
    print("\n" + "="*60)
    print("TEST: Store Rant Endpoint")
    print("="*60)
    
    conflict_id = "test-conflict-001"
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/post-fight/conflicts/{conflict_id}/rant",
            json={
                "content": "This is a test rant about feeling frustrated.",
                "partner_id": "partner_a",
                "is_shared": False
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Rant endpoint working!")
            print(f"   Success: {data.get('success')}")
            print(f"   Message: {data.get('message')}")
            return True
        else:
            print(f"❌ Rant endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to backend. Is it running on {BASE_URL}?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def run_all_tests():
    """Run all API endpoint tests"""
    print("\n" + "="*60)
    print("API ENDPOINTS TEST SUITE")
    print("="*60)
    print(f"Testing against: {BASE_URL}")
    print("Note: Backend server must be running!")
    
    results = []
    results.append(("Analyze Conflict", test_analyze_endpoint()))
    results.append(("Repair Plan", test_repair_plan_endpoint()))
    results.append(("Store Rant", test_rant_endpoint()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All API endpoint tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)

