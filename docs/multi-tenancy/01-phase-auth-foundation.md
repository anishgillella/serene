# Phase 1: Authentication Foundation

## Goal

Add Auth0 authentication to both frontend and backend without breaking existing functionality. This phase establishes the auth infrastructure that all subsequent phases depend on.

## Duration Estimate

~2-3 days of implementation

## Prerequisites

- Auth0 account with application configured
- Auth0 domain and client ID from dashboard
- API identifier configured in Auth0 for backend

---

## Database Migration

```sql
-- File: backend/app/models/migrations/001_relationship_members.sql

-- Create relationship_members table to link users to relationships
CREATE TABLE IF NOT EXISTS relationship_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    relationship_id UUID NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'partner' CHECK (role IN ('partner', 'invited')),
    display_name TEXT,
    invited_by UUID REFERENCES users(id),
    invitation_token TEXT UNIQUE,
    invitation_status TEXT DEFAULT 'accepted' CHECK (invitation_status IN ('pending', 'accepted', 'rejected', 'expired')),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, relationship_id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_relationship_members_user
    ON relationship_members(user_id);
CREATE INDEX IF NOT EXISTS idx_relationship_members_relationship
    ON relationship_members(relationship_id);
CREATE INDEX IF NOT EXISTS idx_relationship_members_token
    ON relationship_members(invitation_token)
    WHERE invitation_token IS NOT NULL;

-- Add created_by tracking to conflicts
ALTER TABLE conflicts
    ADD COLUMN IF NOT EXISTS created_by_user_id UUID REFERENCES users(id);
```

---

## Backend Changes

### 1. Update Configuration

**File: `backend/app/config.py`**

Add Auth0 settings:

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Auth0 Configuration
    AUTH0_DOMAIN: str = ""
    AUTH0_AUDIENCE: str = ""
    AUTH0_ALGORITHMS: list = ["RS256"]

    # Optional: Allow unauthenticated access during development
    AUTH_OPTIONAL: bool = True  # Set to False in production
```

**File: `.env`**

Add:
```env
AUTH0_DOMAIN=dev-xxxxxxxx.us.auth0.com
AUTH0_AUDIENCE=https://api.serene.app
AUTH_OPTIONAL=true
```

### 2. Create Auth Middleware

**File: `backend/app/middleware/auth.py`** (NEW)

```python
"""
Auth0 JWT verification middleware for FastAPI.
"""
from functools import lru_cache
from typing import Optional
import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel

from app.config import get_settings

security = HTTPBearer(auto_error=False)


class UserContext(BaseModel):
    """Authenticated user context."""
    user_id: str
    auth0_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    relationship_id: Optional[str] = None
    display_name: Optional[str] = None
    partner_display_name: Optional[str] = None


@lru_cache(maxsize=1)
def get_jwks(domain: str) -> dict:
    """Fetch and cache Auth0 JWKS."""
    jwks_url = f"https://{domain}/.well-known/jwks.json"
    response = httpx.get(jwks_url)
    return response.json()


def verify_token(token: str) -> dict:
    """Verify Auth0 JWT and return claims."""
    settings = get_settings()

    try:
        jwks = get_jwks(settings.AUTH0_DOMAIN)
        unverified_header = jwt.get_unverified_header(token)

        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break

        if not rsa_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate key"
            )

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=settings.AUTH0_ALGORITHMS,
            audience=settings.AUTH0_AUDIENCE,
            issuer=f"https://{settings.AUTH0_DOMAIN}/"
        )
        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}"
        )


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
            detail="Not authenticated"
        )

    claims = verify_token(credentials.credentials)
    auth0_id = claims.get("sub")

    # Import here to avoid circular imports
    from app.services.db_service import db_service

    # Get or create user in database
    user = db_service.get_user_by_auth0_id(auth0_id)
    if not user:
        # User doesn't exist yet - they need to complete onboarding
        return UserContext(
            user_id="",
            auth0_id=auth0_id,
            email=claims.get("email"),
            name=claims.get("name")
        )

    # Get user's relationship context
    relationship = db_service.get_user_relationship_context(user["id"])

    return UserContext(
        user_id=user["id"],
        auth0_id=auth0_id,
        email=user.get("email"),
        name=user.get("name"),
        relationship_id=relationship.get("relationship_id") if relationship else None,
        display_name=relationship.get("display_name") if relationship else None,
        partner_display_name=relationship.get("partner_display_name") if relationship else None
    )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[UserContext]:
    """
    Dependency to optionally get current user.
    Returns None if not authenticated (for backward compatibility during migration).
    """
    settings = get_settings()

    if not credentials:
        if settings.AUTH_OPTIONAL:
            return None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    try:
        return await get_current_user(credentials)
    except HTTPException:
        if settings.AUTH_OPTIONAL:
            return None
        raise
```

### 3. Add User Context Methods to DB Service

**File: `backend/app/services/db_service.py`**

Add these methods:

```python
def get_user_by_auth0_id(self, auth0_id: str) -> Optional[dict]:
    """Get user by Auth0 ID."""
    query = "SELECT * FROM users WHERE auth0_id = %s"
    with self.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (auth0_id,))
            row = cur.fetchone()
            if row:
                columns = [desc[0] for desc in cur.description]
                return dict(zip(columns, row))
    return None


def get_user_relationship_context(self, user_id: str) -> Optional[dict]:
    """
    Get user's relationship context including partner info.
    Returns: {relationship_id, display_name, partner_display_name, role}
    """
    query = """
        SELECT
            rm.relationship_id,
            rm.display_name,
            rm.role,
            partner.display_name as partner_display_name
        FROM relationship_members rm
        LEFT JOIN relationship_members partner
            ON partner.relationship_id = rm.relationship_id
            AND partner.user_id != rm.user_id
            AND partner.invitation_status = 'accepted'
        WHERE rm.user_id = %s
            AND rm.invitation_status = 'accepted'
        LIMIT 1
    """
    with self.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_id,))
            row = cur.fetchone()
            if row:
                columns = [desc[0] for desc in cur.description]
                return dict(zip(columns, row))
    return None


def create_user_with_relationship(
    self,
    auth0_id: str,
    email: str,
    name: str,
    display_name: str
) -> tuple[str, str]:
    """
    Create a new user and their relationship.
    Returns: (user_id, relationship_id)
    """
    user_id = str(uuid.uuid4())
    relationship_id = str(uuid.uuid4())

    with self.get_connection() as conn:
        with conn.cursor() as cur:
            # Create user
            cur.execute("""
                INSERT INTO users (id, auth0_id, email, name, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (auth0_id) DO UPDATE SET
                    email = EXCLUDED.email,
                    name = EXCLUDED.name,
                    last_login = NOW()
                RETURNING id
            """, (user_id, auth0_id, email, name))
            user_id = cur.fetchone()[0]

            # Create relationship
            cur.execute("""
                INSERT INTO relationships (id, created_at)
                VALUES (%s, NOW())
            """, (relationship_id,))

            # Link user to relationship
            cur.execute("""
                INSERT INTO relationship_members
                    (user_id, relationship_id, role, display_name, invitation_status, joined_at)
                VALUES (%s, %s, 'partner', %s, 'accepted', NOW())
            """, (user_id, relationship_id, display_name))

            conn.commit()

    return user_id, relationship_id
```

### 4. Update User Routes

**File: `backend/app/routes/user_routes.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.middleware.auth import get_current_user, get_current_user_optional, UserContext
from app.services.db_service import db_service

router = APIRouter(prefix="/api/users", tags=["users"])


class UserSyncRequest(BaseModel):
    auth0_id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None


class CreateProfileRequest(BaseModel):
    display_name: str


@router.post("/sync")
async def sync_user(user: UserSyncRequest):
    """Sync user from Auth0 to local database."""
    user_id = db_service.upsert_user(
        auth0_id=user.auth0_id,
        email=user.email,
        name=user.name,
        picture=user.picture
    )
    return {"user_id": user_id, "status": "synced"}


@router.get("/me")
async def get_current_user_profile(
    current_user: UserContext = Depends(get_current_user)
):
    """Get current user's profile and relationship context."""
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "name": current_user.name,
        "relationship_id": current_user.relationship_id,
        "display_name": current_user.display_name,
        "partner_display_name": current_user.partner_display_name
    }


@router.post("/profile")
async def create_user_profile(
    request: CreateProfileRequest,
    current_user: UserContext = Depends(get_current_user)
):
    """Create user profile with relationship (during onboarding)."""
    if current_user.relationship_id:
        raise HTTPException(
            status_code=400,
            detail="User already has a relationship"
        )

    user_id, relationship_id = db_service.create_user_with_relationship(
        auth0_id=current_user.auth0_id,
        email=current_user.email,
        name=current_user.name,
        display_name=request.display_name
    )

    return {
        "user_id": user_id,
        "relationship_id": relationship_id,
        "display_name": request.display_name
    }
```

### 5. Register Middleware in Main App

**File: `backend/app/main.py`**

Add import and use in select routes:

```python
from app.middleware.auth import get_current_user_optional, UserContext

# Example: Update an existing endpoint to use optional auth
@app.get("/api/conflicts")
async def list_conflicts(
    current_user: Optional[UserContext] = Depends(get_current_user_optional)
):
    # If authenticated, use user's relationship_id
    # If not (during migration), fall back to default
    if current_user and current_user.relationship_id:
        relationship_id = current_user.relationship_id
    else:
        relationship_id = DEFAULT_RELATIONSHIP_ID

    conflicts = db_service.get_all_conflicts(relationship_id)
    return {"conflicts": conflicts}
```

---

## Frontend Changes

### 1. Install Auth0 SDK

```bash
cd frontend
npm install @auth0/auth0-react
```

### 2. Create Auth Context

**File: `frontend/src/contexts/AuthContext.tsx`** (NEW)

```tsx
import React, { createContext, useContext, useEffect, useState } from 'react';
import { useAuth0 } from '@auth0/auth0-react';

interface UserContext {
  userId: string;
  email: string;
  name: string;
  relationshipId: string | null;
  displayName: string | null;
  partnerDisplayName: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

interface AuthContextType {
  user: UserContext | null;
  login: () => void;
  logout: () => void;
  getAccessToken: () => Promise<string>;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const {
    isAuthenticated,
    isLoading: auth0Loading,
    user: auth0User,
    loginWithRedirect,
    logout: auth0Logout,
    getAccessTokenSilently,
  } = useAuth0();

  const [userContext, setUserContext] = useState<UserContext | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchUserContext() {
      if (!isAuthenticated || !auth0User) {
        setUserContext(null);
        setIsLoading(false);
        return;
      }

      try {
        const token = await getAccessTokenSilently();
        const response = await fetch(`${import.meta.env.VITE_API_URL}/api/users/me`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          setUserContext({
            userId: data.user_id,
            email: data.email || auth0User.email || '',
            name: data.name || auth0User.name || '',
            relationshipId: data.relationship_id,
            displayName: data.display_name,
            partnerDisplayName: data.partner_display_name,
            isLoading: false,
            isAuthenticated: true,
          });
        } else {
          // User not in database yet - needs onboarding
          setUserContext({
            userId: '',
            email: auth0User.email || '',
            name: auth0User.name || '',
            relationshipId: null,
            displayName: null,
            partnerDisplayName: null,
            isLoading: false,
            isAuthenticated: true,
          });
        }
      } catch (error) {
        console.error('Failed to fetch user context:', error);
      } finally {
        setIsLoading(false);
      }
    }

    if (!auth0Loading) {
      fetchUserContext();
    }
  }, [isAuthenticated, auth0Loading, auth0User, getAccessTokenSilently]);

  const login = () => loginWithRedirect();

  const logout = () => auth0Logout({
    logoutParams: { returnTo: window.location.origin }
  });

  const getAccessToken = async () => {
    return await getAccessTokenSilently();
  };

  return (
    <AuthContext.Provider value={{
      user: userContext,
      login,
      logout,
      getAccessToken,
      isLoading: isLoading || auth0Loading
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
```

### 3. Wrap App with Auth0Provider

**File: `frontend/src/main.tsx`**

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { Auth0Provider } from '@auth0/auth0-react';
import { AuthProvider } from './contexts/AuthContext';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Auth0Provider
      domain={import.meta.env.VITE_AUTH0_DOMAIN}
      clientId={import.meta.env.VITE_AUTH0_CLIENT_ID}
      authorizationParams={{
        redirect_uri: window.location.origin,
        audience: import.meta.env.VITE_AUTH0_AUDIENCE,
      }}
    >
      <AuthProvider>
        <App />
      </AuthProvider>
    </Auth0Provider>
  </React.StrictMode>
);
```

### 4. Create Protected Route Component

**File: `frontend/src/components/ProtectedRoute.tsx`** (NEW)

```tsx
import { useAuth0 } from '@auth0/auth0-react';
import { Navigate, useLocation } from 'react-router-dom';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth0();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
```

### 5. Add Login Page

**File: `frontend/src/pages/Login.tsx`** (NEW)

```tsx
import { useAuth0 } from '@auth0/auth0-react';
import { Navigate } from 'react-router-dom';

export default function Login() {
  const { isAuthenticated, isLoading, loginWithRedirect } = useAuth0();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-purple-900 to-indigo-900">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white" />
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-purple-900 to-indigo-900 text-white">
      <div className="text-center space-y-8">
        <h1 className="text-5xl font-bold">Serene</h1>
        <p className="text-xl text-purple-200">
          AI-powered relationship mediation
        </p>
        <button
          onClick={() => loginWithRedirect()}
          className="px-8 py-3 bg-white text-purple-900 rounded-lg font-semibold hover:bg-purple-100 transition-colors"
        >
          Sign In
        </button>
      </div>
    </div>
  );
}
```

### 6. Update App.tsx Routes

**File: `frontend/src/App.tsx`**

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from './components/ProtectedRoute';
import Layout from './components/Layout';
import Login from './pages/Login';
import Home from './pages/Home';
// ... other imports

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<Login />} />

        {/* Protected routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Home />} />
          <Route path="capture" element={<FightCapture />} />
          <Route path="history" element={<History />} />
          {/* ... other routes */}
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

### 7. Update Layout with User Info

**File: `frontend/src/components/Layout.tsx`**

Add logout button and user display:

```tsx
import { useAuth } from '../contexts/AuthContext';

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1">
        <header className="flex justify-between items-center p-4">
          <h1>Serene</h1>
          {user && (
            <div className="flex items-center gap-4">
              <span>{user.displayName || user.name}</span>
              <button onClick={logout} className="text-sm text-gray-500">
                Logout
              </button>
            </div>
          )}
        </header>
        <Outlet />
      </main>
    </div>
  );
}
```

### 8. Update Environment Variables

**File: `frontend/.env`**

```env
VITE_API_URL=http://localhost:8000
VITE_AUTH0_DOMAIN=dev-xxxxxxxx.us.auth0.com
VITE_AUTH0_CLIENT_ID=your_client_id
VITE_AUTH0_AUDIENCE=https://api.serene.app
```

---

## Testing Checklist

- [ ] Auth0 login flow works (click login → Auth0 → redirect back)
- [ ] Logout clears session
- [ ] Protected routes redirect to login when unauthenticated
- [ ] `/api/users/me` returns user context when authenticated
- [ ] Existing features still work without authentication (AUTH_OPTIONAL=true)
- [ ] User sync creates/updates user in database
- [ ] relationship_members table created successfully

---

## Files Changed Summary

| File | Action |
|------|--------|
| `backend/app/config.py` | Modify - add Auth0 settings |
| `backend/app/middleware/auth.py` | Create - JWT verification |
| `backend/app/services/db_service.py` | Modify - add user context methods |
| `backend/app/routes/user_routes.py` | Modify - add /me endpoint |
| `backend/app/main.py` | Modify - register middleware |
| `backend/app/models/migrations/001_relationship_members.sql` | Create |
| `frontend/package.json` | Modify - add @auth0/auth0-react |
| `frontend/src/main.tsx` | Modify - wrap with Auth0Provider |
| `frontend/src/contexts/AuthContext.tsx` | Create |
| `frontend/src/components/ProtectedRoute.tsx` | Create |
| `frontend/src/pages/Login.tsx` | Create |
| `frontend/src/App.tsx` | Modify - add protected routes |
| `frontend/src/components/Layout.tsx` | Modify - add user info |

---

## Next Phase

Once authentication is working, proceed to [Phase 2: Multi-Tenancy Core](./02-phase-multi-tenancy-core.md) to remove hardcoded relationship IDs.
