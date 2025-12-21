# Phase 3: Partner Invitation Flow

## Goal

Enable one partner to invite another to join their relationship via email. This creates the complete onboarding experience for couples.

## Duration Estimate

~2-3 days of implementation

## Prerequisites

- Phase 1 (Auth) and Phase 2 (Multi-tenancy) completed
- User can create account and relationship
- Email service configured (SendGrid, SES, or similar)

---

## User Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Partner A (Adrian)                           │
├─────────────────────────────────────────────────────────────────┤
│  1. Signs up with Auth0                                         │
│  2. Completes onboarding (enters display name)                  │
│  3. Relationship created automatically                          │
│  4. Clicks "Invite Partner"                                     │
│  5. Enters partner's email                                      │
│  6. System sends invitation email                               │
│  7. Sees "Waiting for partner..." status                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Email to Partner B                           │
├─────────────────────────────────────────────────────────────────┤
│  Subject: Adrian invited you to join Serene                     │
│                                                                 │
│  "Adrian wants to share their relationship journey with you     │
│   on Serene. Click below to accept the invitation."             │
│                                                                 │
│  [Accept Invitation]                                            │
│                                                                 │
│  This invitation expires in 7 days.                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Partner B (Elara)                            │
├─────────────────────────────────────────────────────────────────┤
│  1. Clicks link in email                                        │
│  2. Lands on invitation page (shows Adrian's name)              │
│  3. Clicks "Accept & Sign Up"                                   │
│  4. Signs up/logs in with Auth0                                 │
│  5. Enters display name                                         │
│  6. Joined to Adrian's relationship                             │
│  7. Both partners can now use the app together                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Migration

```sql
-- File: backend/app/models/migrations/003_invitation_tracking.sql

-- Add invitation tracking columns
ALTER TABLE relationship_members
ADD COLUMN IF NOT EXISTS invitation_email TEXT,
ADD COLUMN IF NOT EXISTS invitation_sent_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS invitation_expires_at TIMESTAMP WITH TIME ZONE;

-- Create index for invitation lookups
CREATE INDEX IF NOT EXISTS idx_relationship_members_invitation_email
    ON relationship_members(invitation_email)
    WHERE invitation_email IS NOT NULL;

-- Create index for expiration cleanup
CREATE INDEX IF NOT EXISTS idx_relationship_members_expires
    ON relationship_members(invitation_expires_at)
    WHERE invitation_status = 'pending';
```

---

## Backend Changes

### 1. Create Email Service

**File: `backend/app/services/email_service.py`** (NEW)

```python
"""
Email service for sending invitation and notification emails.
Supports SendGrid, AWS SES, or SMTP.
"""
import os
from typing import Optional
import httpx
from app.config import get_settings


class EmailService:
    def __init__(self):
        self.settings = get_settings()
        self.provider = os.getenv("EMAIL_PROVIDER", "sendgrid")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@serene.app")
        self.from_name = os.getenv("FROM_NAME", "Serene")

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send an email using configured provider."""
        if self.provider == "sendgrid":
            return await self._send_sendgrid(to_email, subject, html_content, text_content)
        elif self.provider == "ses":
            return await self._send_ses(to_email, subject, html_content, text_content)
        else:
            # Log-only mode for development
            print(f"[EMAIL] To: {to_email}, Subject: {subject}")
            print(f"[EMAIL] Content: {html_content[:200]}...")
            return True

    async def _send_sendgrid(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str]
    ) -> bool:
        """Send via SendGrid API."""
        api_key = os.getenv("SENDGRID_API_KEY")
        if not api_key:
            raise ValueError("SENDGRID_API_KEY not configured")

        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": self.from_email, "name": self.from_name},
            "subject": subject,
            "content": [
                {"type": "text/html", "value": html_content}
            ]
        }

        if text_content:
            payload["content"].insert(0, {"type": "text/plain", "value": text_content})

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
            )
            return response.status_code in [200, 202]

    async def send_invitation_email(
        self,
        to_email: str,
        inviter_name: str,
        invitation_url: str
    ) -> bool:
        """Send partner invitation email."""
        subject = f"{inviter_name} invited you to join Serene"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .logo {{ font-size: 32px; font-weight: bold; color: #7c3aed; }}
                .content {{ background: #f9fafb; border-radius: 12px; padding: 30px; }}
                .button {{ display: inline-block; background: #7c3aed; color: white; padding: 14px 28px;
                          text-decoration: none; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
                .footer {{ text-align: center; color: #6b7280; font-size: 14px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">Serene</div>
                </div>
                <div class="content">
                    <h2>You're Invited!</h2>
                    <p><strong>{inviter_name}</strong> wants to share their relationship journey with you on Serene.</p>
                    <p>Serene helps couples navigate conflicts with AI-powered mediation, providing
                       personalized insights and repair strategies.</p>
                    <p style="text-align: center;">
                        <a href="{invitation_url}" class="button">Accept Invitation</a>
                    </p>
                    <p style="color: #6b7280; font-size: 14px;">
                        This invitation expires in 7 days. If you didn't expect this email,
                        you can safely ignore it.
                    </p>
                </div>
                <div class="footer">
                    <p>Serene - AI-Powered Relationship Mediation</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
{inviter_name} invited you to join Serene

{inviter_name} wants to share their relationship journey with you on Serene.

Accept the invitation: {invitation_url}

This invitation expires in 7 days.

---
Serene - AI-Powered Relationship Mediation
        """

        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_invitation_accepted_email(
        self,
        to_email: str,
        accepter_name: str
    ) -> bool:
        """Notify inviter that partner accepted."""
        subject = f"{accepter_name} joined your relationship on Serene!"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: -apple-system, sans-serif; padding: 40px;">
            <h2>Great news! 🎉</h2>
            <p><strong>{accepter_name}</strong> has accepted your invitation and joined
               your relationship on Serene.</p>
            <p>You can now record conversations together and get personalized insights
               as a couple.</p>
            <p><a href="{os.getenv('FRONTEND_URL', 'http://localhost:5173')}">Open Serene</a></p>
        </body>
        </html>
        """

        return await self.send_email(to_email, subject, html_content)


email_service = EmailService()
```

### 2. Create Invitations Router

**File: `backend/app/routes/invitations.py`** (NEW)

```python
"""
Partner invitation endpoints.
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.middleware.auth import get_current_user, UserContext
from app.services.db_service import db_service
from app.services.email_service import email_service

router = APIRouter(prefix="/api/invitations", tags=["invitations"])

INVITATION_EXPIRY_DAYS = 7


class SendInvitationRequest(BaseModel):
    email: EmailStr
    partner_display_name: Optional[str] = None  # Optional hint for their name


class InvitationResponse(BaseModel):
    invitation_id: str
    email: str
    status: str
    expires_at: str


class AcceptInvitationRequest(BaseModel):
    display_name: str


@router.post("/send")
async def send_invitation(
    request: SendInvitationRequest,
    current_user: UserContext = Depends(get_current_user)
):
    """Send invitation email to partner."""
    if not current_user.relationship_id:
        raise HTTPException(
            status_code=400,
            detail="You must complete onboarding before inviting a partner"
        )

    # Check if partner already exists
    existing_partner = db_service.get_relationship_partner(
        current_user.relationship_id,
        current_user.user_id
    )
    if existing_partner and existing_partner.get("invitation_status") == "accepted":
        raise HTTPException(
            status_code=400,
            detail="A partner has already joined this relationship"
        )

    # Check for existing pending invitation
    existing_invitation = db_service.get_pending_invitation(
        current_user.relationship_id,
        request.email
    )
    if existing_invitation:
        # Resend existing invitation
        invitation_token = existing_invitation["invitation_token"]
    else:
        # Create new invitation
        invitation_token = secrets.token_urlsafe(32)

        db_service.create_invitation(
            relationship_id=current_user.relationship_id,
            email=request.email,
            invited_by=current_user.user_id,
            token=invitation_token,
            display_name_hint=request.partner_display_name,
            expires_at=datetime.utcnow() + timedelta(days=INVITATION_EXPIRY_DAYS)
        )

    # Build invitation URL
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    invitation_url = f"{frontend_url}/invite/{invitation_token}"

    # Send email
    email_sent = await email_service.send_invitation_email(
        to_email=request.email,
        inviter_name=current_user.display_name or "Your partner",
        invitation_url=invitation_url
    )

    if not email_sent:
        raise HTTPException(
            status_code=500,
            detail="Failed to send invitation email"
        )

    return {
        "status": "sent",
        "email": request.email,
        "expires_in_days": INVITATION_EXPIRY_DAYS
    }


@router.get("/{token}")
async def get_invitation(token: str):
    """Get invitation details (public endpoint for invitation page)."""
    invitation = db_service.get_invitation_by_token(token)

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation["invitation_status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Invitation already {invitation['invitation_status']}"
        )

    if invitation["invitation_expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invitation has expired")

    # Get inviter info
    inviter = db_service.get_user(invitation["invited_by"])

    return {
        "valid": True,
        "inviter_name": inviter.get("name") if inviter else "Someone",
        "display_name_hint": invitation.get("display_name"),
        "expires_at": invitation["invitation_expires_at"].isoformat()
    }


@router.post("/{token}/accept")
async def accept_invitation(
    token: str,
    request: AcceptInvitationRequest,
    current_user: UserContext = Depends(get_current_user)
):
    """Accept an invitation and join the relationship."""
    invitation = db_service.get_invitation_by_token(token)

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation["invitation_status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Invitation already {invitation['invitation_status']}"
        )

    if invitation["invitation_expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invitation has expired")

    # Check if user already has a relationship
    if current_user.relationship_id:
        raise HTTPException(
            status_code=400,
            detail="You are already in a relationship. Leave your current relationship first."
        )

    # Accept the invitation
    db_service.accept_invitation(
        token=token,
        user_id=current_user.user_id,
        display_name=request.display_name
    )

    # Notify inviter
    inviter = db_service.get_user(invitation["invited_by"])
    if inviter and inviter.get("email"):
        await email_service.send_invitation_accepted_email(
            to_email=inviter["email"],
            accepter_name=request.display_name
        )

    return {
        "status": "accepted",
        "relationship_id": invitation["relationship_id"]
    }


@router.post("/{token}/reject")
async def reject_invitation(token: str):
    """Reject an invitation."""
    invitation = db_service.get_invitation_by_token(token)

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation["invitation_status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Invitation already {invitation['invitation_status']}"
        )

    db_service.reject_invitation(token)

    return {"status": "rejected"}


@router.get("/")
async def list_invitations(
    current_user: UserContext = Depends(get_current_user)
):
    """List pending invitations for current user's relationship."""
    if not current_user.relationship_id:
        return {"invitations": []}

    invitations = db_service.get_pending_invitations(current_user.relationship_id)

    return {"invitations": invitations}
```

### 3. Add Invitation DB Methods

**File: `backend/app/services/db_service.py`**

Add these methods:

```python
def create_invitation(
    self,
    relationship_id: str,
    email: str,
    invited_by: str,
    token: str,
    display_name_hint: Optional[str],
    expires_at: datetime
) -> str:
    """Create a pending invitation."""
    invitation_id = str(uuid.uuid4())

    query = """
        INSERT INTO relationship_members (
            id, relationship_id, role, display_name, invited_by,
            invitation_token, invitation_email, invitation_status,
            invitation_sent_at, invitation_expires_at, created_at
        ) VALUES (
            %s, %s, 'invited', %s, %s, %s, %s, 'pending', NOW(), %s, NOW()
        )
        RETURNING id
    """

    with self.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (
                invitation_id, relationship_id, display_name_hint,
                invited_by, token, email, expires_at
            ))
            conn.commit()
            return cur.fetchone()[0]


def get_invitation_by_token(self, token: str) -> Optional[dict]:
    """Get invitation by token."""
    query = """
        SELECT * FROM relationship_members
        WHERE invitation_token = %s
    """
    with self.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (token,))
            row = cur.fetchone()
            if row:
                columns = [desc[0] for desc in cur.description]
                return dict(zip(columns, row))
    return None


def get_pending_invitation(self, relationship_id: str, email: str) -> Optional[dict]:
    """Get pending invitation for email in relationship."""
    query = """
        SELECT * FROM relationship_members
        WHERE relationship_id = %s
          AND invitation_email = %s
          AND invitation_status = 'pending'
    """
    with self.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (relationship_id, email))
            row = cur.fetchone()
            if row:
                columns = [desc[0] for desc in cur.description]
                return dict(zip(columns, row))
    return None


def accept_invitation(self, token: str, user_id: str, display_name: str):
    """Accept an invitation - link user to relationship."""
    query = """
        UPDATE relationship_members
        SET user_id = %s,
            display_name = %s,
            role = 'partner',
            invitation_status = 'accepted',
            joined_at = NOW()
        WHERE invitation_token = %s
    """
    with self.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_id, display_name, token))
            conn.commit()


def reject_invitation(self, token: str):
    """Reject an invitation."""
    query = """
        UPDATE relationship_members
        SET invitation_status = 'rejected'
        WHERE invitation_token = %s
    """
    with self.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (token,))
            conn.commit()


def get_relationship_partner(self, relationship_id: str, exclude_user_id: str) -> Optional[dict]:
    """Get the other partner in a relationship."""
    query = """
        SELECT * FROM relationship_members
        WHERE relationship_id = %s AND user_id != %s
    """
    with self.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (relationship_id, exclude_user_id))
            row = cur.fetchone()
            if row:
                columns = [desc[0] for desc in cur.description]
                return dict(zip(columns, row))
    return None


def get_pending_invitations(self, relationship_id: str) -> list:
    """Get all pending invitations for a relationship."""
    query = """
        SELECT id, invitation_email, invitation_status,
               invitation_sent_at, invitation_expires_at
        FROM relationship_members
        WHERE relationship_id = %s AND invitation_status = 'pending'
        ORDER BY created_at DESC
    """
    with self.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (relationship_id,))
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in rows]
```

### 4. Register Router in Main App

**File: `backend/app/main.py`**

```python
from app.routes.invitations import router as invitations_router

app.include_router(invitations_router)
```

---

## Frontend Changes

### 1. Create Invite Partner Page

**File: `frontend/src/pages/InvitePartner.tsx`** (NEW)

```tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail, Send, CheckCircle, Clock } from 'lucide-react';
import { apiClient } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

export default function InvitePartner() {
  const [email, setEmail] = useState('');
  const [displayNameHint, setDisplayNameHint] = useState('');
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { user } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('sending');
    setError('');

    try {
      await apiClient.post('/api/invitations/send', {
        email,
        partner_display_name: displayNameHint || undefined,
      });
      setStatus('sent');
    } catch (err: any) {
      setStatus('error');
      setError(err.message || 'Failed to send invitation');
    }
  };

  if (status === 'sent') {
    return (
      <div className="max-w-md mx-auto mt-20 text-center">
        <div className="bg-green-100 rounded-full w-20 h-20 flex items-center justify-center mx-auto mb-6">
          <CheckCircle className="w-10 h-10 text-green-600" />
        </div>
        <h1 className="text-2xl font-bold mb-4">Invitation Sent!</h1>
        <p className="text-gray-600 mb-6">
          We've sent an invitation to <strong>{email}</strong>.
          They have 7 days to accept.
        </p>
        <div className="space-y-3">
          <button
            onClick={() => navigate('/')}
            className="w-full py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700"
          >
            Go to Dashboard
          </button>
          <button
            onClick={() => {
              setStatus('idle');
              setEmail('');
            }}
            className="w-full py-3 border border-gray-300 rounded-lg font-semibold hover:bg-gray-50"
          >
            Send Another Invitation
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto mt-20">
      <div className="text-center mb-8">
        <div className="bg-purple-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
          <Mail className="w-8 h-8 text-purple-600" />
        </div>
        <h1 className="text-2xl font-bold">Invite Your Partner</h1>
        <p className="text-gray-600 mt-2">
          Send an invitation so you can use Serene together
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Partner's Email
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="partner@example.com"
            required
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            What should we call them? (optional)
          </label>
          <input
            type="text"
            value={displayNameHint}
            onChange={(e) => setDisplayNameHint(e.target.value)}
            placeholder="e.g., Alex"
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          />
          <p className="text-sm text-gray-500 mt-1">
            They can change this when they accept
          </p>
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={status === 'sending'}
          className="w-full py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {status === 'sending' ? (
            <>
              <Clock className="w-5 h-5 animate-spin" />
              Sending...
            </>
          ) : (
            <>
              <Send className="w-5 h-5" />
              Send Invitation
            </>
          )}
        </button>
      </form>

      <div className="mt-8 text-center">
        <button
          onClick={() => navigate('/')}
          className="text-gray-500 hover:text-gray-700"
        >
          Skip for now
        </button>
      </div>
    </div>
  );
}
```

### 2. Create Accept Invitation Page

**File: `frontend/src/pages/AcceptInvitation.tsx`** (NEW)

```tsx
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Heart, CheckCircle, XCircle, Loader } from 'lucide-react';
import { useAuth0 } from '@auth0/auth0-react';
import { apiClient } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

interface InvitationDetails {
  valid: boolean;
  inviter_name: string;
  display_name_hint?: string;
  expires_at: string;
}

export default function AcceptInvitation() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, loginWithRedirect } = useAuth0();
  const { user } = useAuth();

  const [invitation, setInvitation] = useState<InvitationDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [accepting, setAccepting] = useState(false);

  useEffect(() => {
    async function fetchInvitation() {
      try {
        const data = await apiClient.get(`/api/invitations/${token}`);
        setInvitation(data);
        if (data.display_name_hint) {
          setDisplayName(data.display_name_hint);
        }
      } catch (err: any) {
        setError(err.message || 'Invalid or expired invitation');
      } finally {
        setLoading(false);
      }
    }
    fetchInvitation();
  }, [token]);

  const handleAccept = async () => {
    if (!isAuthenticated) {
      // Store token in session and redirect to login
      sessionStorage.setItem('pendingInvitation', token!);
      loginWithRedirect({
        appState: { returnTo: `/invite/${token}` }
      });
      return;
    }

    setAccepting(true);
    try {
      await apiClient.post(`/api/invitations/${token}/accept`, {
        display_name: displayName,
      });
      navigate('/', { replace: true });
    } catch (err: any) {
      setError(err.message || 'Failed to accept invitation');
      setAccepting(false);
    }
  };

  const handleReject = async () => {
    try {
      await apiClient.post(`/api/invitations/${token}/reject`, {});
      navigate('/login', { replace: true });
    } catch (err) {
      // Ignore errors on rejection
      navigate('/login', { replace: true });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader className="w-8 h-8 animate-spin text-purple-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-md mx-auto mt-20 text-center">
        <div className="bg-red-100 rounded-full w-20 h-20 flex items-center justify-center mx-auto mb-6">
          <XCircle className="w-10 h-10 text-red-600" />
        </div>
        <h1 className="text-2xl font-bold mb-4">Invalid Invitation</h1>
        <p className="text-gray-600 mb-6">{error}</p>
        <button
          onClick={() => navigate('/login')}
          className="px-6 py-3 bg-purple-600 text-white rounded-lg font-semibold"
        >
          Go to Login
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto mt-20">
      <div className="text-center mb-8">
        <div className="bg-purple-100 rounded-full w-20 h-20 flex items-center justify-center mx-auto mb-6">
          <Heart className="w-10 h-10 text-purple-600" />
        </div>
        <h1 className="text-2xl font-bold">You're Invited!</h1>
        <p className="text-gray-600 mt-2">
          <strong>{invitation?.inviter_name}</strong> wants to share their
          relationship journey with you on Serene.
        </p>
      </div>

      <div className="bg-white shadow-lg rounded-xl p-6 space-y-4">
        {isAuthenticated ? (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                What should we call you?
              </label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Your name"
                required
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
              />
            </div>

            <button
              onClick={handleAccept}
              disabled={!displayName || accepting}
              className="w-full py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {accepting ? (
                <Loader className="w-5 h-5 animate-spin" />
              ) : (
                <CheckCircle className="w-5 h-5" />
              )}
              Accept Invitation
            </button>
          </>
        ) : (
          <button
            onClick={handleAccept}
            className="w-full py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700"
          >
            Sign Up to Accept
          </button>
        )}

        <button
          onClick={handleReject}
          className="w-full py-3 border border-gray-300 text-gray-600 rounded-lg font-semibold hover:bg-gray-50"
        >
          Decline
        </button>
      </div>

      <p className="text-center text-sm text-gray-500 mt-6">
        By accepting, you'll join {invitation?.inviter_name}'s relationship on Serene
        and be able to use the app together.
      </p>
    </div>
  );
}
```

### 3. Create Partner Status Banner

**File: `frontend/src/components/PartnerStatusBanner.tsx`** (NEW)

```tsx
import { Link } from 'react-router-dom';
import { UserPlus, Clock } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export function PartnerStatusBanner() {
  const { user } = useAuth();

  if (!user?.relationshipId) return null;
  if (user?.partnerDisplayName) return null; // Partner exists

  return (
    <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-6">
      <div className="flex items-center gap-3">
        <div className="bg-purple-100 rounded-full p-2">
          <UserPlus className="w-5 h-5 text-purple-600" />
        </div>
        <div className="flex-1">
          <p className="font-medium text-purple-900">
            Invite your partner to get the most out of Serene
          </p>
          <p className="text-sm text-purple-700">
            Recording conversations together provides better insights
          </p>
        </div>
        <Link
          to="/invite"
          className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-semibold hover:bg-purple-700"
        >
          Invite Partner
        </Link>
      </div>
    </div>
  );
}
```

### 4. Update Routes

**File: `frontend/src/App.tsx`**

Add invitation routes:

```tsx
import InvitePartner from './pages/InvitePartner';
import AcceptInvitation from './pages/AcceptInvitation';

// Inside Routes:
<Route path="/invite" element={<ProtectedRoute><InvitePartner /></ProtectedRoute>} />
<Route path="/invite/:token" element={<AcceptInvitation />} />
```

### 5. Update Onboarding Flow

**File: `frontend/src/pages/Onboarding.tsx`**

After completing profile, redirect to invite:

```tsx
const completeOnboarding = async () => {
  // ... existing onboarding logic ...

  // After completing profile setup
  navigate('/invite');
};
```

### 6. Add Banner to Home

**File: `frontend/src/pages/Home.tsx`**

```tsx
import { PartnerStatusBanner } from '../components/PartnerStatusBanner';

export default function Home() {
  return (
    <div>
      <PartnerStatusBanner />
      {/* ... rest of home page */}
    </div>
  );
}
```

---

## Environment Variables

Add to `.env`:

```env
# Email Service
EMAIL_PROVIDER=sendgrid  # or "ses" or "log" for development
SENDGRID_API_KEY=SG.xxxxx
FROM_EMAIL=noreply@serene.app
FROM_NAME=Serene

# Frontend URL (for invitation links)
FRONTEND_URL=http://localhost:5173
```

---

## Testing Checklist

- [ ] Send invitation to valid email
- [ ] Invitation email received with correct link
- [ ] Invitation page shows inviter name
- [ ] Accept invitation as new user
- [ ] Accept invitation as existing user
- [ ] Reject invitation works
- [ ] Expired invitation shows error
- [ ] Already-accepted invitation shows error
- [ ] Partner status banner shows when no partner
- [ ] Banner disappears after partner joins
- [ ] Inviter receives notification when partner accepts

---

## Files Created/Modified

| File | Action |
|------|--------|
| `backend/app/services/email_service.py` | Create |
| `backend/app/routes/invitations.py` | Create |
| `backend/app/services/db_service.py` | Add invitation methods |
| `backend/app/main.py` | Register invitations router |
| `frontend/src/pages/InvitePartner.tsx` | Create |
| `frontend/src/pages/AcceptInvitation.tsx` | Create |
| `frontend/src/components/PartnerStatusBanner.tsx` | Create |
| `frontend/src/App.tsx` | Add routes |
| `frontend/src/pages/Onboarding.tsx` | Redirect to invite |
| `frontend/src/pages/Home.tsx` | Add banner |

---

## Next Phase

Proceed to [Phase 4: Data Model Cleanup](./04-phase-data-model-cleanup.md) to remove gender-specific fields.
