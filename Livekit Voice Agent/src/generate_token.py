"""
Simple token generator for LiveKit.
In production, generate tokens server-side for security.
"""

import os
import time
from livekit import api
from dotenv import load_dotenv

load_dotenv(".env.local")

def generate_token(room_name: str, participant_name: str = "user"):
    """
    Generate a LiveKit access token for a participant.
    
    Args:
        room_name: Name of the room to join
        participant_name: Name of the participant
    
    Returns:
        Access token string
    """
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    
    if not api_key or not api_secret:
        raise ValueError("LIVEKIT_API_KEY and LIVEKIT_API_SECRET must be set in .env.local")
    
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

if __name__ == "__main__":
    # Example usage
    room_name = f"voice-agent-{int(time.time())}"
    token = generate_token(room_name, "user")
    print(f"Room: {room_name}")
    print(f"Token: {token}")

