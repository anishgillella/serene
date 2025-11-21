"""Gmail integration tool for sending emails via Google OAuth."""

from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import httpx

# Load environment
load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)


@dataclass
class EmailRequest:
    recipient: str
    subject: str
    body: str


# Gmail OAuth configuration
GMAIL_CLIENT_ID = os.environ.get("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.environ.get("GMAIL_CLIENT_SECRET")
GMAIL_REFRESH_TOKEN = os.environ.get("GMAIL_REFRESH_TOKEN")
GMAIL_SENDER_EMAIL = os.environ.get("GMAIL_SENDER_EMAIL")
GMAIL_API_BASE = "https://www.googleapis.com/gmail/v1/users/me"


async def get_access_token() -> str:
    """Get a fresh access token using the refresh token.
    
    Returns:
        str: Access token for Gmail API
        
    Raises:
        Exception: If token refresh fails
    """
    try:
        response = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GMAIL_CLIENT_ID,
                "client_secret": GMAIL_CLIENT_SECRET,
                "refresh_token": GMAIL_REFRESH_TOKEN,
                "grant_type": "refresh_token",
            },
            timeout=10.0,
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to refresh token: {response.text}")
            raise Exception(f"Token refresh failed: {response.status_code}")
        
        token_data = response.json()
        return token_data["access_token"]
        
    except Exception as e:
        logger.error(f"Error getting access token: {e}")
        raise


async def send_email(request: EmailRequest) -> bool:
    """Send an email using Gmail API via OAuth.
    
    Args:
        request: EmailRequest object containing recipient, subject, and body.
        
    Returns:
        bool: True if successful, False otherwise.
    """
    if not all([GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN, GMAIL_SENDER_EMAIL]):
        logger.error("Missing Gmail OAuth credentials in .env")
        return False
    
    try:
        logger.info(f"📧 Preparing email to {request.recipient}")
        logger.info(f"Subject: {request.subject}")
        
        # Get fresh access token
        access_token = await get_access_token()
        
        # Construct email message in RFC 2822 format
        email_message = f"""From: {GMAIL_SENDER_EMAIL}
To: {request.recipient}
Subject: {request.subject}

{request.body}
"""
        
        # Encode message in base64url (Gmail API requirement)
        message_bytes = email_message.encode("utf-8")
        message_b64 = base64.urlsafe_b64encode(message_bytes).decode("utf-8")
        
        # Send via Gmail API
        response = httpx.post(
            f"{GMAIL_API_BASE}/messages/send",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={
                "raw": message_b64,
            },
            timeout=10.0,
        )
        
        if response.status_code == 200:
            message_data = response.json()
            logger.info(f"✅ Email sent successfully! Message ID: {message_data.get('id')}")
            return True
        else:
            logger.error(f"Gmail API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending email: {e}", exc_info=True)
        return False
