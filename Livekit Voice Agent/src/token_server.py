"""
Simple Flask server for generating LiveKit tokens.
Run this alongside your agent for local development.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from livekit import api
import os
from dotenv import load_dotenv

# Load environment variables from .env.local or .env
load_dotenv(".env.local")
load_dotenv(".env")  # Also check .env file

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

def generate_token(room_name: str, participant_name: str = "user"):
    """Generate a LiveKit access token"""
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    
    if not api_key or not api_secret:
        raise ValueError("LIVEKIT_API_KEY and LIVEKIT_API_SECRET must be set")
    
    token = api.AccessToken(api_key, api_secret) \
        .with_identity(participant_name) \
        .with_name(participant_name) \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        ))
    
    return token.to_jwt()

@app.route('/token', methods=['POST'])
def get_token():
    """Generate a token for the frontend"""
    try:
        data = request.json or {}
        room_name = data.get('room', f'voice-agent-{os.urandom(8).hex()}')
        participant_name = data.get('participant', 'user')
        
        token = generate_token(room_name, participant_name)
        
        return jsonify({
            'token': token,
            'room': room_name,
            'url': os.getenv('LIVEKIT_URL')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    print("Token server running on http://localhost:8080")
    print("Make sure your .env.local file has LIVEKIT_API_KEY and LIVEKIT_API_SECRET")
    app.run(port=8080, debug=True)

