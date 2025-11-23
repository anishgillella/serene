#!/bin/bash

# Test script for LiveKit Voice Agent

echo "🔍 Testing LiveKit Voice Agent Setup..."
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    exit 1
fi

echo "✅ .env file found"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "🔌 Activating virtual environment..."
source venv/bin/activate

echo "📥 Installing/updating dependencies..."
pip install -q -r requirements.txt

echo ""
echo "🧪 Testing environment variables..."
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv('.env')

required_vars = [
    'LIVEKIT_URL',
    'LIVEKIT_API_KEY', 
    'LIVEKIT_API_SECRET',
    'OPENROUTER_API_KEY',
    'DEEPGRAM_API_KEY',
    'ELEVENLABS_API_KEY'
]

missing = []
for var in required_vars:
    value = os.getenv(var)
    if value:
        print(f'✅ {var}: Set')
    else:
        print(f'❌ {var}: Missing')
        missing.append(var)

if missing:
    print(f'\n❌ Missing required environment variables: {missing}')
    exit(1)
else:
    print('\n✅ All required environment variables are set!')
"

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Environment check failed. Please check your .env file."
    exit 1
fi

echo ""
echo "📥 Downloading required model files..."
python3 src/agent.py download-files

echo ""
echo "✅ Setup complete!"
echo ""
echo "To test the agent, run one of these commands:"
echo ""
echo "1. Console mode (test in terminal):"
echo "   python3 src/agent.py console"
echo ""
echo "2. Development mode (connect to LiveKit Cloud):"
echo "   python3 src/agent.py dev"
echo ""

