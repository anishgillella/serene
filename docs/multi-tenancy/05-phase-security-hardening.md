# Phase 5: Security Hardening

## Goal

Implement proper Row-Level Security (RLS) policies, enforce authentication on all protected routes, and ensure complete data isolation between relationships.

## Duration Estimate

~2-3 days of implementation

## Prerequisites

- Phases 1-4 completed
- Authentication working
- All routes using user context

---

## Security Audit Checklist

Before implementation, verify these issues exist:

| Issue | Current State | Target State |
|-------|---------------|--------------|
| RLS Policies | "Allow public access" | User-based filtering |
| API Auth | Optional/fallback to default | Required for protected routes |
| Access Control | None | Verify ownership before operations |
| Rate Limiting | None | Implement per-user limits |
| Input Validation | Basic | Comprehensive Pydantic validation |
| Audit Logging | None | Log all data access |

---

## Database Migration

```sql
-- File: backend/app/models/migrations/005_security_hardening.sql

-- ============================================
-- PART 1: Drop Permissive Policies
-- ============================================

-- Drop all "allow public" policies
DROP POLICY IF EXISTS "Allow public access to relationships" ON relationships;
DROP POLICY IF EXISTS "Allow public access to conflicts" ON conflicts;
DROP POLICY IF EXISTS "Allow public access to rant_messages" ON rant_messages;
DROP POLICY IF EXISTS "Allow public access to mediator_sessions" ON mediator_sessions;
DROP POLICY IF EXISTS "Allow public access to mediator_messages" ON mediator_messages;
DROP POLICY IF EXISTS "Allow public access to profiles" ON profiles;
DROP POLICY IF EXISTS "Allow public access to cycle_events" ON cycle_events;
DROP POLICY IF EXISTS "Allow public access to intimacy_events" ON intimacy_events;
DROP POLICY IF EXISTS "Allow public access to memorable_dates" ON memorable_dates;
DROP POLICY IF EXISTS "Allow public access to conflict_analysis" ON conflict_analysis;
DROP POLICY IF EXISTS "Allow public access to repair_plans" ON repair_plans;
DROP POLICY IF EXISTS "Allow public access to chat_messages" ON chat_messages;

-- ============================================
-- PART 2: Helper Function
-- ============================================

-- Function to get user's relationship IDs
CREATE OR REPLACE FUNCTION get_user_relationship_ids(user_uuid UUID)
RETURNS SETOF UUID AS $$
    SELECT relationship_id
    FROM relationship_members
    WHERE user_id = user_uuid
      AND invitation_status = 'accepted';
$$ LANGUAGE SQL SECURITY DEFINER STABLE;

-- ============================================
-- PART 3: Relationship Policies
-- ============================================

-- Users can view relationships they're a member of
CREATE POLICY "rls_relationships_select"
    ON relationships FOR SELECT
    USING (id IN (SELECT get_user_relationship_ids(auth.uid())));

-- Users can update their own relationships
CREATE POLICY "rls_relationships_update"
    ON relationships FOR UPDATE
    USING (id IN (SELECT get_user_relationship_ids(auth.uid())));

-- ============================================
-- PART 4: Conflicts Policies
-- ============================================

CREATE POLICY "rls_conflicts_select"
    ON conflicts FOR SELECT
    USING (relationship_id IN (SELECT get_user_relationship_ids(auth.uid())));

CREATE POLICY "rls_conflicts_insert"
    ON conflicts FOR INSERT
    WITH CHECK (relationship_id IN (SELECT get_user_relationship_ids(auth.uid())));

CREATE POLICY "rls_conflicts_update"
    ON conflicts FOR UPDATE
    USING (relationship_id IN (SELECT get_user_relationship_ids(auth.uid())));

CREATE POLICY "rls_conflicts_delete"
    ON conflicts FOR DELETE
    USING (relationship_id IN (SELECT get_user_relationship_ids(auth.uid())));

-- ============================================
-- PART 5: Other Table Policies
-- ============================================

-- Rant Messages
CREATE POLICY "rls_rant_messages_all"
    ON rant_messages FOR ALL
    USING (conflict_id IN (
        SELECT id FROM conflicts
        WHERE relationship_id IN (SELECT get_user_relationship_ids(auth.uid()))
    ));

-- Mediator Sessions
CREATE POLICY "rls_mediator_sessions_all"
    ON mediator_sessions FOR ALL
    USING (conflict_id IN (
        SELECT id FROM conflicts
        WHERE relationship_id IN (SELECT get_user_relationship_ids(auth.uid()))
    ));

-- Mediator Messages
CREATE POLICY "rls_mediator_messages_all"
    ON mediator_messages FOR ALL
    USING (session_id IN (
        SELECT id FROM mediator_sessions
        WHERE conflict_id IN (
            SELECT id FROM conflicts
            WHERE relationship_id IN (SELECT get_user_relationship_ids(auth.uid()))
        )
    ));

-- Profiles
CREATE POLICY "rls_profiles_all"
    ON profiles FOR ALL
    USING (relationship_id IN (SELECT get_user_relationship_ids(auth.uid())));

-- Cycle Events
CREATE POLICY "rls_cycle_events_all"
    ON cycle_events FOR ALL
    USING (relationship_id IN (SELECT get_user_relationship_ids(auth.uid())));

-- Intimacy Events
CREATE POLICY "rls_intimacy_events_all"
    ON intimacy_events FOR ALL
    USING (relationship_id IN (SELECT get_user_relationship_ids(auth.uid())));

-- Memorable Dates
CREATE POLICY "rls_memorable_dates_all"
    ON memorable_dates FOR ALL
    USING (relationship_id IN (SELECT get_user_relationship_ids(auth.uid())));

-- Conflict Analysis
CREATE POLICY "rls_conflict_analysis_all"
    ON conflict_analysis FOR ALL
    USING (conflict_id IN (
        SELECT id FROM conflicts
        WHERE relationship_id IN (SELECT get_user_relationship_ids(auth.uid()))
    ));

-- Repair Plans
CREATE POLICY "rls_repair_plans_all"
    ON repair_plans FOR ALL
    USING (conflict_id IN (
        SELECT id FROM conflicts
        WHERE relationship_id IN (SELECT get_user_relationship_ids(auth.uid()))
    ));

-- Chat Messages
CREATE POLICY "rls_chat_messages_all"
    ON chat_messages FOR ALL
    USING (conflict_id IN (
        SELECT id FROM conflicts
        WHERE relationship_id IN (SELECT get_user_relationship_ids(auth.uid()))
    ));

-- ============================================
-- PART 6: Service Role Bypass
-- ============================================

-- Allow service role (backend) full access for operations that bypass RLS
-- This is for background jobs, admin operations, etc.

CREATE POLICY "service_role_relationships"
    ON relationships FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "service_role_conflicts"
    ON conflicts FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "service_role_rant_messages"
    ON rant_messages FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "service_role_mediator_sessions"
    ON mediator_sessions FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "service_role_mediator_messages"
    ON mediator_messages FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "service_role_profiles"
    ON profiles FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "service_role_cycle_events"
    ON cycle_events FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "service_role_intimacy_events"
    ON intimacy_events FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "service_role_memorable_dates"
    ON memorable_dates FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "service_role_conflict_analysis"
    ON conflict_analysis FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "service_role_repair_plans"
    ON repair_plans FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "service_role_chat_messages"
    ON chat_messages FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================
-- PART 7: Audit Log Table
-- ============================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);

-- Audit logs are append-only (no user access, only service role)
CREATE POLICY "service_role_audit_logs"
    ON audit_logs FOR ALL
    USING (auth.role() = 'service_role');
```

---

## Backend Changes

### 1. Enforce Authentication

**File: `backend/app/middleware/auth.py`**

Remove optional auth fallback in production:

```python
from app.config import get_settings

settings = get_settings()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserContext:
    """
    Dependency to get current authenticated user.
    Raises 401 if not authenticated.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return await _verify_and_get_user(credentials.credentials)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[UserContext]:
    """
    Dependency for optional authentication.
    Only use for truly public endpoints.
    """
    if not credentials:
        return None

    try:
        return await _verify_and_get_user(credentials.credentials)
    except HTTPException:
        return None


# Strict version that requires relationship
async def get_current_user_with_relationship(
    current_user: UserContext = Depends(get_current_user)
) -> UserContext:
    """Require user to have an active relationship."""
    if not current_user.relationship_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must complete onboarding and have an active relationship"
        )
    return current_user
```

### 2. Add Access Control Helpers

**File: `backend/app/middleware/access_control.py`** (NEW)

```python
"""
Access control utilities for verifying resource ownership.
"""
from fastapi import HTTPException, status
from app.services.db_service import db_service
from app.middleware.auth import UserContext


def verify_conflict_access(
    conflict_id: str,
    current_user: UserContext,
    require_owner: bool = False
):
    """
    Verify user has access to a conflict.

    Args:
        conflict_id: The conflict to check
        current_user: Authenticated user
        require_owner: If True, user must be the creator

    Raises:
        HTTPException 403 if access denied
        HTTPException 404 if conflict not found
    """
    conflict = db_service.get_conflict(conflict_id)

    if not conflict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conflict not found"
        )

    if conflict.get("relationship_id") != current_user.relationship_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this conflict"
        )

    if require_owner and conflict.get("created_by_user_id") != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the conflict creator can perform this action"
        )

    return conflict


def verify_profile_access(
    profile_id: str,
    current_user: UserContext
):
    """Verify user has access to a profile."""
    profile = db_service.get_profile(profile_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    if profile.get("relationship_id") != current_user.relationship_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this profile"
        )

    return profile


def verify_session_access(
    session_id: str,
    current_user: UserContext
):
    """Verify user has access to a mediator session."""
    session = db_service.get_mediator_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Get conflict to check relationship
    conflict = db_service.get_conflict(session.get("conflict_id"))

    if not conflict or conflict.get("relationship_id") != current_user.relationship_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this session"
        )

    return session
```

### 3. Add Audit Logging Service

**File: `backend/app/services/audit_service.py`** (NEW)

```python
"""
Audit logging service for security monitoring.
"""
import json
from typing import Optional
from fastapi import Request
from app.services.db_service import db_service


class AuditService:
    """Service for recording audit logs."""

    def log(
        self,
        user_id: Optional[str],
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[dict] = None,
        request: Optional[Request] = None
    ):
        """
        Log an audit event.

        Args:
            user_id: ID of the user performing the action
            action: What was done (create, read, update, delete)
            resource_type: Type of resource (conflict, profile, session)
            resource_id: ID of the affected resource
            details: Additional context
            request: FastAPI request for IP/user-agent
        """
        ip_address = None
        user_agent = None

        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")

        db_service.create_audit_log(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details) if details else None,
            ip_address=ip_address,
            user_agent=user_agent
        )

    def log_access(self, user_id: str, resource_type: str, resource_id: str, request: Request = None):
        """Log a read/access event."""
        self.log(user_id, "access", resource_type, resource_id, request=request)

    def log_create(self, user_id: str, resource_type: str, resource_id: str, details: dict = None, request: Request = None):
        """Log a create event."""
        self.log(user_id, "create", resource_type, resource_id, details, request)

    def log_update(self, user_id: str, resource_type: str, resource_id: str, details: dict = None, request: Request = None):
        """Log an update event."""
        self.log(user_id, "update", resource_type, resource_id, details, request)

    def log_delete(self, user_id: str, resource_type: str, resource_id: str, request: Request = None):
        """Log a delete event."""
        self.log(user_id, "delete", resource_type, resource_id, request=request)

    def log_auth_failure(self, details: dict, request: Request = None):
        """Log an authentication failure."""
        self.log(None, "auth_failure", "auth", details=details, request=request)


audit_service = AuditService()
```

### 4. Add Rate Limiting

**File: `backend/app/middleware/rate_limit.py`** (NEW)

```python
"""
Rate limiting middleware using slowapi.
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request


def get_user_identifier(request: Request) -> str:
    """Get rate limit key from user or IP."""
    # Try to get user ID from auth header
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        # Use token hash as identifier (more precise than IP)
        token = auth_header[7:]
        return f"user:{hash(token) % 10**9}"

    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


# Create limiter with user-aware key function
limiter = Limiter(key_func=get_user_identifier)


# Rate limit decorators
def rate_limit(limit: str):
    """
    Apply rate limit to an endpoint.

    Usage:
        @router.get("/endpoint")
        @rate_limit("10/minute")
        async def endpoint():
            ...
    """
    return limiter.limit(limit)


# Standard limits
LIMITS = {
    "default": "60/minute",
    "auth": "10/minute",      # Login/token endpoints
    "upload": "10/hour",       # File uploads
    "analysis": "30/hour",     # AI analysis (expensive)
    "search": "100/minute",    # Search/list endpoints
}
```

### 5. Update Main App with Security Middleware

**File: `backend/app/main.py`**

```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.middleware.rate_limit import limiter

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Remove server header
    response.headers.pop("server", None)

    return response


# Update CORS for production
from app.config import get_settings
settings = get_settings()

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
]

if settings.FRONTEND_URL:
    ALLOWED_ORIGINS.append(settings.FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # No more "*" wildcard
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### 6. Update Routes with Access Control

**File: `backend/app/routes/post_fight.py`**

```python
from app.middleware.auth import get_current_user_with_relationship, UserContext
from app.middleware.access_control import verify_conflict_access
from app.middleware.rate_limit import rate_limit, LIMITS
from app.services.audit_service import audit_service


@router.get("/conflicts/{conflict_id}")
@rate_limit(LIMITS["default"])
async def get_conflict(
    conflict_id: str,
    request: Request,
    current_user: UserContext = Depends(get_current_user_with_relationship)
):
    """Get conflict details with access control."""
    # Verify access (raises 403 if denied)
    conflict = verify_conflict_access(conflict_id, current_user)

    # Log access
    audit_service.log_access(
        current_user.user_id,
        "conflict",
        conflict_id,
        request
    )

    return conflict


@router.post("/conflicts/{conflict_id}/generate-analysis")
@rate_limit(LIMITS["analysis"])
async def generate_analysis(
    conflict_id: str,
    request: Request,
    current_user: UserContext = Depends(get_current_user_with_relationship)
):
    """Generate analysis with access control and rate limiting."""
    conflict = verify_conflict_access(conflict_id, current_user)

    # Log the action
    audit_service.log_create(
        current_user.user_id,
        "analysis",
        conflict_id,
        {"action": "generate"},
        request
    )

    # ... rest of implementation
```

### 7. Add Input Validation

**File: `backend/app/models/validators.py`** (NEW)

```python
"""
Enhanced Pydantic validators for input validation.
"""
import re
from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, List
from uuid import UUID


class ConflictCreateRequest(BaseModel):
    """Validated conflict creation request."""
    title: Optional[str] = Field(None, max_length=200)

    @validator("title")
    def sanitize_title(cls, v):
        if v:
            # Remove any HTML/script tags
            v = re.sub(r"<[^>]*>", "", v)
            # Limit special characters
            v = re.sub(r"[^\w\s\-.,!?']", "", v)
        return v


class TranscriptSegment(BaseModel):
    """Validated transcript segment."""
    speaker_id: str = Field(..., pattern=r"^partner_[ab]$")
    text: str = Field(..., max_length=10000)

    @validator("text")
    def sanitize_text(cls, v):
        # Remove null bytes and control characters
        v = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", v)
        return v.strip()


class TranscriptStoreRequest(BaseModel):
    """Validated transcript storage request."""
    conflict_id: UUID
    segments: List[TranscriptSegment] = Field(..., max_items=1000)
    duration_seconds: Optional[int] = Field(None, ge=0, le=36000)  # Max 10 hours


class InvitationSendRequest(BaseModel):
    """Validated invitation request."""
    email: EmailStr
    partner_display_name: Optional[str] = Field(None, max_length=50)

    @validator("partner_display_name")
    def sanitize_name(cls, v):
        if v:
            v = re.sub(r"[^\w\s\-']", "", v)
        return v


class ProfileUploadRequest(BaseModel):
    """Validated profile upload request."""
    pdf_type: str = Field(..., pattern=r"^(partner_profile|relationship_handbook)$")


class CalendarEventRequest(BaseModel):
    """Validated calendar event request."""
    event_type: str = Field(..., pattern=r"^(period_start|period_end|symptom|mood|intimacy)$")
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    notes: Optional[str] = Field(None, max_length=500)

    @validator("notes")
    def sanitize_notes(cls, v):
        if v:
            v = re.sub(r"<[^>]*>", "", v)
        return v
```

---

## Frontend Changes

### 1. Update API Error Handling

**File: `frontend/src/services/api.ts`**

```typescript
class ApiClient {
  async fetch(endpoint: string, options: RequestInit = {}): Promise<Response> {
    // ... existing code ...

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    });

    // Handle auth errors
    if (response.status === 401) {
      // Token expired or invalid - trigger re-login
      window.dispatchEvent(new CustomEvent('auth:expired'));
      throw new Error('Session expired. Please log in again.');
    }

    // Handle access denied
    if (response.status === 403) {
      throw new Error('You do not have access to this resource.');
    }

    // Handle rate limiting
    if (response.status === 429) {
      const retryAfter = response.headers.get('Retry-After') || '60';
      throw new Error(`Too many requests. Please wait ${retryAfter} seconds.`);
    }

    return response;
  }
}
```

### 2. Add Auth Expiration Handler

**File: `frontend/src/contexts/AuthContext.tsx`**

```typescript
useEffect(() => {
  const handleAuthExpired = () => {
    logout();
    // Navigate to login with message
    window.location.href = '/login?expired=true';
  };

  window.addEventListener('auth:expired', handleAuthExpired);
  return () => window.removeEventListener('auth:expired', handleAuthExpired);
}, [logout]);
```

### 3. Update Protected Route

**File: `frontend/src/components/ProtectedRoute.tsx`**

```tsx
import { useAuth } from '../contexts/AuthContext';
import { Navigate, useLocation } from 'react-router-dom';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireRelationship?: boolean;
}

export function ProtectedRoute({
  children,
  requireRelationship = false
}: ProtectedRouteProps) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (!user?.isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requireRelationship && !user.relationshipId) {
    return <Navigate to="/onboarding" replace />;
  }

  return <>{children}</>;
}
```

---

## Testing Checklist

### Authentication
- [ ] Unauthenticated requests return 401
- [ ] Invalid tokens return 401
- [ ] Expired tokens return 401 and trigger re-login

### Authorization
- [ ] User A cannot access User B's conflicts
- [ ] User A cannot access User B's profiles
- [ ] User A cannot access User B's sessions
- [ ] Access denied returns 403 (not 404)

### Rate Limiting
- [ ] Exceeding rate limit returns 429
- [ ] Rate limits are per-user (not global)
- [ ] Rate limit headers are present

### Input Validation
- [ ] XSS attempts are sanitized
- [ ] SQL injection patterns are rejected
- [ ] Oversized inputs are rejected

### Audit Logging
- [ ] All data access is logged
- [ ] Failed auth attempts are logged
- [ ] Logs include IP and user-agent

### RLS Policies
- [ ] Direct database queries respect RLS
- [ ] Service role can bypass RLS

---

## Files Created/Modified

| File | Action |
|------|--------|
| `backend/app/models/migrations/005_security_hardening.sql` | Create |
| `backend/app/middleware/auth.py` | Update - remove optional fallback |
| `backend/app/middleware/access_control.py` | Create |
| `backend/app/middleware/rate_limit.py` | Create |
| `backend/app/services/audit_service.py` | Create |
| `backend/app/models/validators.py` | Create |
| `backend/app/main.py` | Update - security middleware |
| `backend/app/routes/post_fight.py` | Update - access control |
| `backend/app/routes/calendar.py` | Update - access control |
| `backend/app/routes/analytics.py` | Update - access control |
| `frontend/src/services/api.ts` | Update - error handling |
| `frontend/src/contexts/AuthContext.tsx` | Update - expiration handler |
| `frontend/src/components/ProtectedRoute.tsx` | Update - relationship check |

---

## Environment Variables

Add for production:

```env
# Security
AUTH_OPTIONAL=false
RATE_LIMIT_ENABLED=true

# Allowed origins (no wildcards)
FRONTEND_URL=https://your-domain.com

# Supabase service role (for RLS bypass)
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

---

## Next Phase

Proceed to [Phase 6: Future Optimizations](./06-phase-future-optimizations.md) for performance and scalability improvements.
