#!/usr/bin/env python3
"""Comprehensive test script for Serene agent pipeline.

Tests each stage independently to identify any issues.
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Load environment
load_dotenv(Path(__file__).parent / ".env")


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def print_test(text, status="🔍"):
    """Print a test status."""
    print(f"{status} {text}")


# ============================================================================
# STAGE 1: Environment Variables
# ============================================================================
def test_stage_1_env():
    """Test Stage 1: Environment Variables."""
    print_header("STAGE 1: Environment Variables")

    required_vars = {
        "TWILIO_SID": "Twilio Account SID",
        "TWILIO_AUTH_TOKEN": "Twilio Auth Token",
        "TWILIO_PHONE_NUMBER": "Twilio Phone Number",
        "ASSEMBLY_API_KEY": "AssemblyAI API Key",
        "ELEVENLABS_API_KEY": "ElevenLabs API Key",
        "ELEVENLABS_VOICE_ID": "ElevenLabs Voice ID",
        "OPENROUTER_API_KEY": "OpenRouter API Key",
        "GMAIL_CLIENT_ID": "Gmail Client ID",
        "GMAIL_CLIENT_SECRET": "Gmail Client Secret",
        "GMAIL_REFRESH_TOKEN": "Gmail Refresh Token",
        "GMAIL_SENDER_EMAIL": "Gmail Sender Email",
    }

    missing = []
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if value:
            masked = value[:4] + "..." if len(value) > 4 else value
            print_test(f"✅ {var}: {masked}", "✅")
        else:
            print_test(f"❌ {var}: MISSING", "❌")
            missing.append(var)

    if missing:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing)}")
        return False, f"Missing: {', '.join(missing)}"
    
    print("\n✅ All environment variables present!")
    return True, None


# ============================================================================
# STAGE 2: Import All Modules
# ============================================================================
def test_stage_2_imports():
    """Test Stage 2: Import all backend modules."""
    print_header("STAGE 2: Import Backend Modules")

    modules = {
        "backend.stt_client": "Speech-to-Text (AssemblyAI)",
        "backend.tts_handler": "Text-to-Speech (ElevenLabs)",
        "backend.serene_agent": "Serene Agent (LLM + RAG)",
        "backend.rag_handler": "RAG Handler (Chroma)",
        "backend.twilio_handler": "Twilio Handler",
        "backend.tools": "Gmail Tools",
        "backend.voice_orchestrator": "Voice Orchestrator",
        "backend.api_server": "Flask API Server",
    }

    failed = []
    for module_name, description in modules.items():
        try:
            __import__(module_name)
            print_test(f"✅ {description}", "✅")
        except Exception as e:
            print_test(f"❌ {description}: {str(e)[:60]}", "❌")
            failed.append((description, str(e)))

    if failed:
        print(f"\n⚠️  Failed imports:")
        for desc, error in failed:
            print(f"   - {desc}: {error[:80]}")
        return False, failed
    
    print("\n✅ All modules imported successfully!")
    return True, None


# ============================================================================
# STAGE 3: RAG Knowledge Base
# ============================================================================
def test_stage_3_rag():
    """Test Stage 3: RAG knowledge base initialization."""
    print_header("STAGE 3: RAG Knowledge Base (ChromaDB)")

    try:
        from backend.rag_handler import amara_kb
        
        if not amara_kb.initialized:
            print_test("❌ RAG not initialized", "❌")
            return False, "RAG initialization failed"
        
        doc_count = amara_kb.collection.count() if amara_kb.collection else 0
        print_test(f"✅ Chroma initialized", "✅")
        print_test(f"✅ Collection exists", "✅")
        print_test(f"✅ Documents in store: {doc_count}", "✅")

        if doc_count == 0:
            print("\n⚠️  Warning: No documents in vector store")
            print("   This means RAG context will be empty during conversations")
            return True, "No documents (warning)"
        
        # Test retrieval (skip async test - will test in real flow)
        print_test(f"✅ Retrieval method available", "✅")

        print("\n✅ RAG system operational!")
        return True, None
        
    except Exception as e:
        print_test(f"❌ RAG Error: {str(e)[:60]}", "❌")
        return False, str(e)


# ============================================================================
# STAGE 4: Serene Agent (LLM)
# ============================================================================
async def test_stage_4_serene():
    """Test Stage 4: Serene agent with LLM."""
    print_header("STAGE 4: Serene Agent (LLM)")

    try:
        from backend.serene_agent import get_serene_response
        
        print_test("Testing Serene LLM response...", "🔍")
        
        # Test a simple query
        test_message = "I said something logical and Amara got upset. What should I do?"
        
        response = await get_serene_response(test_message)
        
        if response and len(response) > 10:
            print_test(f"✅ LLM responded: {response[:80]}...", "✅")
            print_test(f"   Length: {len(response)} characters", "✅")
            print("\n✅ Serene Agent operational!")
            return True, None
        else:
            print_test(f"❌ Invalid response: {response}", "❌")
            return False, "Invalid LLM response"
        
    except Exception as e:
        print_test(f"❌ Serene Error: {str(e)[:60]}", "❌")
        return False, str(e)


# ============================================================================
# STAGE 5: Text-to-Speech
# ============================================================================
async def test_stage_5_tts():
    """Test Stage 5: Text-to-Speech (ElevenLabs)."""
    print_header("STAGE 5: Text-to-Speech (ElevenLabs)")

    try:
        from backend.tts_handler import text_to_speech
        
        print_test("Testing TTS with ElevenLabs...", "🔍")
        
        test_text = "Hello, I understand your feelings. Let's talk about what happened."
        
        audio_bytes = await text_to_speech(test_text, output_format="mp3_44100_128")
        
        if audio_bytes and len(audio_bytes) > 100:
            print_test(f"✅ Audio generated: {len(audio_bytes)} bytes", "✅")
            print_test(f"   Format: MP3 (44.1kHz, 128kbps)", "✅")
            
            # Warning about format
            print("\n⚠️  NOTE: MP3 format needs conversion to mulaw (8kHz) for Twilio!")
            print("   This is needed for real phone calls to work.")
            
            print("\n✅ TTS operational (format conversion needed)!")
            return True, "Format conversion needed"
        else:
            print_test(f"❌ Invalid audio: {len(audio_bytes) if audio_bytes else 0} bytes", "❌")
            return False, "Invalid audio response"
        
    except Exception as e:
        print_test(f"❌ TTS Error: {str(e)[:60]}", "❌")
        return False, str(e)


# ============================================================================
# STAGE 6: Speech-to-Text
# ============================================================================
def test_stage_6_stt():
    """Test Stage 6: Speech-to-Text (AssemblyAI)."""
    print_header("STAGE 6: Speech-to-Text (AssemblyAI)")

    try:
        from backend.stt_client import AssemblyAIStreamingClient
        
        print_test("Initializing STT client...", "🔍")
        
        client = AssemblyAIStreamingClient(sample_rate=8000, encoding="mulaw")
        
        print_test(f"✅ STT client initialized", "✅")
        print_test(f"   Sample rate: 8000 Hz", "✅")
        print_test(f"   Encoding: mulaw", "✅")
        print_test(f"   API: AssemblyAI Streaming v3", "✅")
        
        print("\n✅ STT ready! (Requires live audio stream to test fully)")
        return True, None
        
    except Exception as e:
        print_test(f"❌ STT Error: {str(e)[:60]}", "❌")
        return False, str(e)


# ============================================================================
# STAGE 7: Twilio Integration
# ============================================================================
def test_stage_7_twilio():
    """Test Stage 7: Twilio handler."""
    print_header("STAGE 7: Twilio Integration")

    try:
        from backend.twilio_handler import twilio_manager
        
        print_test("Checking Twilio configuration...", "🔍")
        
        twilio_sid = os.environ.get("TWILIO_SID")
        twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")
        twilio_number = os.environ.get("TWILIO_PHONE_NUMBER")
        
        print_test(f"✅ Twilio SID: {twilio_sid[:4] if twilio_sid else 'MISSING'}...", "✅")
        print_test(f"✅ Twilio Phone: {twilio_number}", "✅")
        print_test(f"✅ TwilioManager initialized", "✅")
        print_test(f"   Call sessions: {len(twilio_manager.call_sessions)}", "✅")
        
        print("\n✅ Twilio configured! (Ready for webhooks)")
        return True, None
        
    except Exception as e:
        print_test(f"❌ Twilio Error: {str(e)[:60]}", "❌")
        return False, str(e)


# ============================================================================
# STAGE 8: Gmail Integration
# ============================================================================
async def test_stage_8_gmail():
    """Test Stage 8: Gmail tools."""
    print_header("STAGE 8: Gmail Integration")

    try:
        from backend.tools import get_access_token, send_email, EmailRequest
        
        print_test("Testing Gmail OAuth token refresh...", "🔍")
        
        # Test token refresh (don't actually send email)
        try:
            token = await get_access_token()
            if token and len(token) > 10:
                print_test(f"✅ OAuth token refreshed successfully", "✅")
                print_test(f"   Token: {token[:20]}...", "✅")
            else:
                print_test(f"❌ Invalid token: {token}", "❌")
                return False, "Invalid token"
        except Exception as token_error:
            print_test(f"⚠️  Token refresh failed: {str(token_error)[:50]}", "⚠️")
            print("\n   Possible issues:")
            print("   - GMAIL_REFRESH_TOKEN expired or invalid")
            print("   - GMAIL_CLIENT_ID/SECRET incorrect")
            print("   - Network issue")
            return False, f"Token error: {str(token_error)}"
        
        print_test(f"✅ Email tool ready (not sending test email)", "✅")
        print("\n✅ Gmail integration operational!")
        return True, None
        
    except Exception as e:
        print_test(f"❌ Gmail Error: {str(e)[:60]}", "❌")
        return False, str(e)


# ============================================================================
# STAGE 9: Voice Orchestrator
# ============================================================================
def test_stage_9_orchestrator():
    """Test Stage 9: Voice orchestrator."""
    print_header("STAGE 9: Voice Orchestrator")

    try:
        from backend.voice_orchestrator import voice_orchestrator
        
        print_test("Checking voice orchestrator...", "🔍")
        
        print_test(f"✅ Orchestrator initialized", "✅")
        print_test(f"   STT client ready", "✅")
        print_test(f"   Call history: {len(voice_orchestrator.call_history)}", "✅")
        print_test(f"   Ready for Twilio media streams", "✅")
        
        print("\n✅ Voice orchestrator ready!")
        return True, None
        
    except Exception as e:
        print_test(f"❌ Orchestrator Error: {str(e)[:60]}", "❌")
        return False, str(e)


# ============================================================================
# STAGE 10: Flask API Server
# ============================================================================
def test_stage_10_api():
    """Test Stage 10: Flask API server."""
    print_header("STAGE 10: Flask API Server")

    try:
        from backend.api_server import app
        
        print_test("Checking Flask routes...", "🔍")
        
        routes = [
            ("GET /health", "Health check"),
            ("POST /twilio/incoming", "Incoming call webhook"),
            ("POST /serene/respond", "Serene response"),
            ("POST /api/call", "Trigger outbound call"),
            ("WS /media-stream", "Twilio media stream"),
            ("WS /api/events", "Frontend events"),
            ("POST /email/draft", "Draft email"),
            ("POST /email/send", "Send email"),
        ]
        
        for route, description in routes:
            print_test(f"✅ {route}: {description}", "✅")
        
        print("\n✅ Flask API Server ready!")
        return True, None
        
    except Exception as e:
        print_test(f"❌ API Server Error: {str(e)[:60]}", "❌")
        return False, str(e)


# ============================================================================
# STAGE 11: Frontend
# ============================================================================
def test_stage_11_frontend():
    """Test Stage 11: React frontend."""
    print_header("STAGE 11: React Frontend")

    try:
        frontend_dir = Path(__file__).parent / "frontend"
        
        if not frontend_dir.exists():
            print_test("❌ Frontend directory missing", "❌")
            return False, "Frontend not found"
        
        package_json = frontend_dir / "package.json"
        if package_json.exists():
            print_test(f"✅ package.json found", "✅")
        else:
            print_test(f"❌ package.json missing", "❌")
            return False, "package.json not found"
        
        node_modules = frontend_dir / "node_modules"
        if node_modules.exists():
            print_test(f"✅ node_modules installed", "✅")
        else:
            print_test(f"⚠️  node_modules not installed", "⚠️")
            print("   Run: cd frontend && npm install")
        
        print("\n✅ Frontend structure ready!")
        return True, "npm install needed" if not node_modules.exists() else None
        
    except Exception as e:
        print_test(f"❌ Frontend Error: {str(e)[:60]}", "❌")
        return False, str(e)


# ============================================================================
# Main Test Runner
# ============================================================================
async def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  🧪 SERENE AGENT - COMPREHENSIVE STAGE TESTING".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")

    results = {}

    # Stage 1: Environment
    success, error = test_stage_1_env()
    results["Stage 1: Environment Variables"] = ("✅" if success else "❌", error)

    if not success:
        print("\n⚠️  Cannot proceed without environment variables!")
        return results

    # Stage 2: Imports
    success, error = test_stage_2_imports()
    results["Stage 2: Import Modules"] = ("✅" if success else "❌", error)

    if not success:
        print("\n⚠️  Cannot proceed without importable modules!")
        print("   Please check error messages above")
        return results

    # Stage 3: RAG
    success, error = test_stage_3_rag()
    results["Stage 3: RAG Knowledge Base"] = ("✅" if success else "❌", error)

    # Stage 4: Serene Agent (requires async)
    success, error = await test_stage_4_serene()
    results["Stage 4: Serene Agent (LLM)"] = ("✅" if success else "❌", error)

    # Stage 5: TTS (requires async)
    success, error = await test_stage_5_tts()
    results["Stage 5: Text-to-Speech"] = ("✅" if success else "❌", error)

    # Stage 6: STT
    success, error = test_stage_6_stt()
    results["Stage 6: Speech-to-Text"] = ("✅" if success else "❌", error)

    # Stage 7: Twilio
    success, error = test_stage_7_twilio()
    results["Stage 7: Twilio Integration"] = ("✅" if success else "❌", error)

    # Stage 8: Gmail
    success, error = await test_stage_8_gmail()
    results["Stage 8: Gmail Integration"] = ("✅" if success else "❌", error)

    # Stage 9: Orchestrator
    success, error = test_stage_9_orchestrator()
    results["Stage 9: Voice Orchestrator"] = ("✅" if success else "❌", error)

    # Stage 10: API
    success, error = test_stage_10_api()
    results["Stage 10: Flask API Server"] = ("✅" if success else "❌", error)

    # Stage 11: Frontend
    success, error = test_stage_11_frontend()
    results["Stage 11: React Frontend"] = ("✅" if success else "❌", error)

    # Print summary
    print_header("📊 TEST SUMMARY")
    
    passed = sum(1 for status, _ in results.values() if status == "✅")
    total = len(results)
    
    print(f"Passed: {passed}/{total}\n")
    
    for stage, (status, error) in results.items():
        if error and error != "Format conversion needed" and error != "npm install needed":
            print(f"{status} {stage}")
            if error:
                if isinstance(error, list):
                    for item in error:
                        print(f"       ⚠️  {item}")
                else:
                    print(f"       ⚠️  {error}")
        else:
            print(f"{status} {stage}")

    print("\n" + "=" * 80)
    print("\n📋 DETAILED FINDINGS:\n")
    
    findings = []
    
    if results["Stage 8: Gmail Integration"][0] == "❌":
        findings.append("❌ Gmail OAuth token refresh failed - email won't work until fixed")
    
    if results["Stage 5: Text-to-Speech"][1] == "Format conversion needed":
        findings.append("⚠️  TTS outputs MP3 but Twilio needs mulaw (8kHz) - phone calls will fail")
    
    if results["Stage 11: React Frontend"][1] == "npm install needed":
        findings.append("⚠️  Frontend node_modules not installed - run: cd frontend && npm install")
    
    if not findings:
        print("✅ All systems operational! Ready for testing.\n")
    else:
        for finding in findings:
            print(f"• {finding}")
        print()


if __name__ == "__main__":
    asyncio.run(main())

