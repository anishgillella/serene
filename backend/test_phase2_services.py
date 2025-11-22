"""
Test script for Phase 2 services and endpoints
Run: python test_phase2_services.py
"""
import asyncio
import sys
import os
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.config import settings
from app.services.pinecone_service import pinecone_service
from app.services.embeddings_service import embeddings_service
from app.services.llm_service import llm_service
from app.services.tts_service import tts_service
from app.tools.conflict_analysis import analyze_conflict_transcript
from app.tools.repair_coaching import generate_repair_plan
from app.models.schemas import ConflictAnalysis, RepairPlan

def test_pinecone_connection():
    """Test 1: Pinecone connection"""
    print("\n" + "="*60)
    print("TEST 1: Pinecone Connection")
    print("="*60)
    try:
        # Test index stats
        stats = pinecone_service.index.describe_index_stats()
        print(f"✅ Pinecone connected successfully!")
        print(f"   Index: {pinecone_service.index_name}")
        print(f"   Total vectors: {stats.get('total_vector_count', 'N/A')}")
        return True
    except Exception as e:
        print(f"❌ Pinecone connection failed: {e}")
        return False

def test_voyage_embeddings():
    """Test 2: Voyage embeddings"""
    print("\n" + "="*60)
    print("TEST 2: Voyage Embeddings")
    print("="*60)
    try:
        test_text = "This is a test transcript about a relationship conflict."
        embedding = embeddings_service.embed_text(test_text)
        print(f"✅ Embedding generated successfully!")
        print(f"   Text: {test_text[:50]}...")
        print(f"   Embedding dimension: {len(embedding)}")
        print(f"   First 5 values: {embedding[:5]}")
        
        if len(embedding) != 1024:
            print(f"⚠️  Warning: Expected 1024 dimensions, got {len(embedding)}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Embedding generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_llm_service():
    """Test 3: LLM Service (GPT-4o-mini via OpenRouter)"""
    print("\n" + "="*60)
    print("TEST 3: LLM Service (GPT-4o-mini)")
    print("="*60)
    try:
        messages = [
            {
                "role": "user",
                "content": "Say 'Hello, this is a test' in exactly 5 words."
            }
        ]
        response = llm_service.chat_completion(messages, temperature=0.7)
        print(f"✅ LLM service working!")
        print(f"   Response: {response}")
        return True
    except Exception as e:
        print(f"❌ LLM service failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_structured_output():
    """Test 4: Structured output with Pydantic"""
    print("\n" + "="*60)
    print("TEST 4: Structured Output (Pydantic)")
    print("="*60)
    try:
        # Create a simple test model
        from pydantic import BaseModel
        from typing import List
        
        class TestAnalysis(BaseModel):
            summary: str
            points: List[str]
            score: int
        
        prompt = """Analyze this simple conflict: "I feel ignored when you're on your phone."
        Return JSON with: summary (string), points (list of strings), score (integer 1-10)."""
        
        messages = [{"role": "user", "content": prompt}]
        result = llm_service.structured_output(
            messages=messages,
            response_model=TestAnalysis,
            temperature=0.7
        )
        
        print(f"✅ Structured output working!")
        print(f"   Summary: {result.summary}")
        print(f"   Points: {result.points}")
        print(f"   Score: {result.score}")
        return True
    except Exception as e:
        print(f"❌ Structured output failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tts_service():
    """Test 5: TTS Service (ElevenLabs)"""
    print("\n" + "="*60)
    print("TEST 5: TTS Service (ElevenLabs)")
    print("="*60)
    try:
        test_text = "Hello, this is a test of the text to speech service."
        audio = tts_service.generate_audio(test_text)
        print(f"✅ TTS service working!")
        print(f"   Text: {test_text}")
        print(f"   Audio size: {len(audio)} bytes")
        return True
    except Exception as e:
        print(f"❌ TTS service failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_conflict_analysis():
    """Test 6: Conflict Analysis Tool"""
    print("\n" + "="*60)
    print("TEST 6: Conflict Analysis Tool")
    print("="*60)
    try:
        test_transcript = """
        Boyfriend: I feel like you're always on your phone when we're together.
        Girlfriend: I'm just checking work emails, it's important.
        Boyfriend: But we're supposed to be spending time together. I feel ignored.
        Girlfriend: You're being too sensitive. I can multitask.
        Boyfriend: That's not the point. I want your attention.
        Girlfriend: Fine, I'll put it away. But you're being unreasonable.
        """
        
        conflict_id = "test-conflict-001"
        analysis = await analyze_conflict_transcript(
            conflict_id=conflict_id,
            transcript_text=test_transcript,
            relationship_id="test-relationship",
            partner_a_id="partner_a",
            partner_b_id="partner_b",
            speaker_labels={0: "Boyfriend", 1: "Girlfriend"},
            duration=120.0,
            timestamp=datetime.now()
        )
        
        print(f"✅ Conflict analysis working!")
        print(f"   Conflict ID: {analysis.conflict_id}")
        print(f"   Summary: {analysis.fight_summary[:100]}...")
        print(f"   Root causes: {analysis.root_causes}")
        print(f"   Escalation points: {len(analysis.escalation_points)}")
        print(f"   Unmet needs (Boyfriend): {analysis.unmet_needs_boyfriend}")
        print(f"   Unmet needs (Girlfriend): {analysis.unmet_needs_girlfriend}")
        return True
    except Exception as e:
        print(f"❌ Conflict analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_repair_plan():
    """Test 7: Repair Plan Tool"""
    print("\n" + "="*60)
    print("TEST 7: Repair Plan Tool")
    print("="*60)
    try:
        test_transcript = """
        Boyfriend: I feel like you're always on your phone when we're together.
        Girlfriend: I'm just checking work emails, it's important.
        Boyfriend: But we're supposed to be spending time together. I feel ignored.
        """
        
        conflict_id = "test-conflict-001"
        repair_plan = await generate_repair_plan(
            conflict_id=conflict_id,
            transcript_text=test_transcript,
            partner_requesting_id="partner_a",
            relationship_id="test-relationship",
            partner_a_id="partner_a",
            partner_b_id="partner_b"
        )
        
        print(f"✅ Repair plan generation working!")
        print(f"   Conflict ID: {repair_plan.conflict_id}")
        print(f"   Partner requesting: {repair_plan.partner_requesting}")
        print(f"   Steps: {repair_plan.steps}")
        print(f"   Apology script: {repair_plan.apology_script[:100]}...")
        print(f"   Timing suggestion: {repair_plan.timing_suggestion}")
        return True
    except Exception as e:
        print(f"❌ Repair plan generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pinecone_storage():
    """Test 8: Pinecone Storage"""
    print("\n" + "="*60)
    print("TEST 8: Pinecone Storage & Retrieval")
    print("="*60)
    try:
        # Store a test transcript
        test_conflict_id = "test-storage-001"
        test_text = "This is a test transcript for storage verification."
        embedding = embeddings_service.embed_text(test_text)
        
        from app.models.schemas import SpeakerSegment
        transcript_data = {
            "conflict_id": test_conflict_id,
            "relationship_id": "test-relationship",
            "transcript_text": test_text,
            "speaker_segments": [
                SpeakerSegment(speaker="Boyfriend", text="Hello", start_time=0.0, end_time=1.0),
                SpeakerSegment(speaker="Girlfriend", text="Hi there", start_time=1.0, end_time=2.0)
            ],
            "timestamp": datetime.now(),
            "start_time": datetime.now(),
            "end_time": datetime.now(),
            "duration": 60.0,
            "partner_a_id": "partner_a",
            "partner_b_id": "partner_b",
            "speaker_labels": {0: "Boyfriend", 1: "Girlfriend"}
        }
        
        # Store
        pinecone_service.upsert_transcript(
            conflict_id=test_conflict_id,
            embedding=embedding,
            transcript_data=transcript_data,
            namespace="transcripts"
        )
        print(f"✅ Stored transcript in Pinecone")
        
        # Retrieve
        result = pinecone_service.get_by_conflict_id(
            conflict_id=test_conflict_id,
            namespace="transcripts"
        )
        
        if result and result.metadata:
            print(f"✅ Retrieved transcript from Pinecone")
            print(f"   Conflict ID: {result.metadata.get('conflict_id')}")
            print(f"   Transcript preview: {result.metadata.get('transcript_text', '')[:50]}...")
            return True
        else:
            print(f"❌ Failed to retrieve transcript")
            return False
            
    except Exception as e:
        print(f"❌ Pinecone storage test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("PHASE 2 SERVICES TEST SUITE")
    print("="*60)
    
    results = []
    
    # Sync tests
    results.append(("Pinecone Connection", test_pinecone_connection()))
    results.append(("Voyage Embeddings", test_voyage_embeddings()))
    results.append(("LLM Service", test_llm_service()))
    results.append(("Structured Output", test_structured_output()))
    results.append(("TTS Service", test_tts_service()))
    results.append(("Pinecone Storage", test_pinecone_storage()))
    
    # Async tests
    results.append(("Conflict Analysis", await test_conflict_analysis()))
    results.append(("Repair Plan", await test_repair_plan()))
    
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
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)

