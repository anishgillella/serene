#!/bin/bash
# LiveKit CLI Test Script
# Tests the HeartSync voice agent by connecting via CLI

echo "🎙️ Testing HeartSync Voice Agent with LiveKit CLI"
echo "=================================================="

# Get token from backend
echo ""
echo "1. Generating LiveKit token..."
TOKEN=$(curl -s -X POST "http://localhost:8000/api/token?room_name=cli-test-room&participant_name=cli-tester" | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to get token. Is backend running?"
    exit 1
fi

echo "✅ Token generated: ${TOKEN:0:50}..."

# Get LiveKit URL from .env
LIVEKIT_URL=$(grep LIVEKIT_URL .env | cut -d '=' -f2)

echo ""
echo "2. Connecting to LiveKit room..."
echo "   URL: $LIVEKIT_URL"
echo "   Room: cli-test-room"
echo ""
echo "📝 Instructions:"
echo "   - Once connected, speak into your microphone"
echo "   - Watch the agent terminal for transcript output"
echo "   - Press Ctrl+C to disconnect"
echo ""
echo "Connecting in 3 seconds..."
sleep 3

# Connect to room
livekit-cli join-room \
  --url "$LIVEKIT_URL" \
  --token "$TOKEN" \
  --publish-demo
