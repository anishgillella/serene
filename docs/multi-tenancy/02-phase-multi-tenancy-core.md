# Phase 2: Multi-Tenancy Core (No Auth Required)

## Goal

Enable multiple couples to use Serene by:
1. Creating a `couple_profiles` table to store partner names
2. Passing `relationship_id` in API requests instead of using hardcoded values
3. Using localStorage to persist the current couple's relationship_id
4. Seeding Adrian & Elara as test data

## Duration Estimate

~2-3 days of implementation

## Prerequisites

- Existing database with `relationships` table
- Default relationship `00000000-0000-0000-0000-000000000000` exists

---

## Database Migration

```sql
-- File: backend/app/models/migrations/002_couple_profiles.sql

-- Create couple_profiles table for storing partner details
CREATE TABLE IF NOT EXISTS couple_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    relationship_id UUID UNIQUE NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,

    -- Partner A (first partner / creator)
    partner_a_name TEXT NOT NULL,
    partner_a_email TEXT,

    -- Partner B (second partner)
    partner_b_name TEXT,
    partner_b_email TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_couple_profiles_relationship
    ON couple_profiles(relationship_id);

-- Enable RLS (permissive for now)
ALTER TABLE couple_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public access to couple_profiles"
    ON couple_profiles FOR ALL USING (true);

-- Seed test data: Adrian & Elara
INSERT INTO couple_profiles (relationship_id, partner_a_name, partner_b_name)
VALUES ('00000000-0000-0000-0000-000000000000', 'Adrian', 'Elara')
ON CONFLICT (relationship_id) DO UPDATE SET
    partner_a_name = EXCLUDED.partner_a_name,
    partner_b_name = EXCLUDED.partner_b_name,
    updated_at = NOW();
```

---

## Backend Changes

### 1. Add Couple Profile Methods to DB Service

**File: `backend/app/services/db_service.py`**

Add these methods:

```python
def get_couple_profile(self, relationship_id: str) -> Optional[Dict[str, Any]]:
    """Get couple profile by relationship_id."""
    try:
        with self.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, relationship_id, partner_a_name, partner_a_email,
                           partner_b_name, partner_b_email, created_at, updated_at
                    FROM couple_profiles
                    WHERE relationship_id = %s;
                """, (relationship_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
    except Exception as e:
        print(f"Error getting couple profile: {e}")
        return None


def create_couple_profile(
    self,
    partner_a_name: str,
    partner_b_name: str = None,
    partner_a_email: str = None,
    partner_b_email: str = None
) -> tuple:
    """
    Create a new relationship and couple profile.

    Returns:
        (relationship_id, profile_id)
    """
    import uuid
    relationship_id = str(uuid.uuid4())

    try:
        with self.get_db_context() as conn:
            with conn.cursor() as cursor:
                # Create relationship
                cursor.execute("""
                    INSERT INTO relationships (id, created_at, partner_a_name, partner_b_name)
                    VALUES (%s, NOW(), %s, %s)
                    RETURNING id;
                """, (relationship_id, partner_a_name, partner_b_name))
                relationship_id = str(cursor.fetchone()[0])

                # Create couple profile
                cursor.execute("""
                    INSERT INTO couple_profiles
                        (relationship_id, partner_a_name, partner_b_name,
                         partner_a_email, partner_b_email)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id;
                """, (relationship_id, partner_a_name, partner_b_name,
                      partner_a_email, partner_b_email))
                profile_id = str(cursor.fetchone()[0])

                conn.commit()
                return (relationship_id, profile_id)
    except Exception as e:
        print(f"Error creating couple profile: {e}")
        raise e


def update_couple_profile(
    self,
    relationship_id: str,
    partner_a_name: str = None,
    partner_b_name: str = None,
    partner_a_email: str = None,
    partner_b_email: str = None
) -> bool:
    """Update couple profile fields."""
    try:
        with self.get_db_context() as conn:
            with conn.cursor() as cursor:
                updates = []
                values = []

                if partner_a_name is not None:
                    updates.append("partner_a_name = %s")
                    values.append(partner_a_name)
                if partner_b_name is not None:
                    updates.append("partner_b_name = %s")
                    values.append(partner_b_name)
                if partner_a_email is not None:
                    updates.append("partner_a_email = %s")
                    values.append(partner_a_email)
                if partner_b_email is not None:
                    updates.append("partner_b_email = %s")
                    values.append(partner_b_email)

                if not updates:
                    return False

                updates.append("updated_at = NOW()")
                values.append(relationship_id)

                cursor.execute(f"""
                    UPDATE couple_profiles
                    SET {', '.join(updates)}
                    WHERE relationship_id = %s;
                """, values)

                conn.commit()
                return cursor.rowcount > 0
    except Exception as e:
        print(f"Error updating couple profile: {e}")
        return False


def get_partner_names(self, relationship_id: str) -> Dict[str, str]:
    """
    Get partner names for a relationship.

    Returns:
        {"partner_a": "Adrian", "partner_b": "Elara"}
    """
    profile = self.get_couple_profile(relationship_id)
    if profile:
        return {
            "partner_a": profile.get("partner_a_name") or "Partner A",
            "partner_b": profile.get("partner_b_name") or "Partner B"
        }
    return {"partner_a": "Partner A", "partner_b": "Partner B"}
```

### 2. Create Couple Routes

**File: `backend/app/routes/couple_routes.py`** (NEW)

```python
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.services.db_service import db_service, DEFAULT_RELATIONSHIP_ID

router = APIRouter(prefix="/api/couple", tags=["couple"])


class CreateCoupleRequest(BaseModel):
    partner_a_name: str
    partner_b_name: Optional[str] = None
    partner_a_email: Optional[str] = None
    partner_b_email: Optional[str] = None


class UpdateCoupleRequest(BaseModel):
    partner_a_name: Optional[str] = None
    partner_b_name: Optional[str] = None
    partner_a_email: Optional[str] = None
    partner_b_email: Optional[str] = None


@router.post("/create")
async def create_couple(request: CreateCoupleRequest):
    """Create a new couple/relationship."""
    try:
        relationship_id, profile_id = db_service.create_couple_profile(
            partner_a_name=request.partner_a_name,
            partner_b_name=request.partner_b_name,
            partner_a_email=request.partner_a_email,
            partner_b_email=request.partner_b_email
        )

        return {
            "success": True,
            "relationship_id": relationship_id,
            "profile_id": profile_id,
            "partner_a_name": request.partner_a_name,
            "partner_b_name": request.partner_b_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile")
async def get_couple_profile(
    relationship_id: str = Query(default=DEFAULT_RELATIONSHIP_ID)
):
    """Get couple profile by relationship_id."""
    profile = db_service.get_couple_profile(relationship_id)

    if not profile:
        raise HTTPException(status_code=404, detail="Couple profile not found")

    return {
        "relationship_id": str(profile["relationship_id"]),
        "partner_a_name": profile["partner_a_name"],
        "partner_b_name": profile["partner_b_name"],
        "partner_a_email": profile["partner_a_email"],
        "partner_b_email": profile["partner_b_email"]
    }


@router.put("/profile")
async def update_couple_profile(
    request: UpdateCoupleRequest,
    relationship_id: str = Query(default=DEFAULT_RELATIONSHIP_ID)
):
    """Update couple profile."""
    success = db_service.update_couple_profile(
        relationship_id=relationship_id,
        partner_a_name=request.partner_a_name,
        partner_b_name=request.partner_b_name,
        partner_a_email=request.partner_a_email,
        partner_b_email=request.partner_b_email
    )

    if not success:
        raise HTTPException(status_code=404, detail="Couple profile not found")

    return {"success": True, "relationship_id": relationship_id}


@router.get("/names")
async def get_partner_names(
    relationship_id: str = Query(default=DEFAULT_RELATIONSHIP_ID)
):
    """Get just the partner names (lightweight endpoint for UI)."""
    names = db_service.get_partner_names(relationship_id)
    return names
```

### 3. Register Couple Routes

**File: `backend/app/main.py`**

Add:

```python
from app.routes.couple_routes import router as couple_router

app.include_router(couple_router)
```

### 4. Update Existing Routes to Accept relationship_id

**Pattern to apply to all endpoints:**

```python
# Before:
@router.get("/conflicts")
async def list_conflicts():
    relationship_id = DEFAULT_RELATIONSHIP_ID  # Hardcoded
    conflicts = db_service.get_all_conflicts(relationship_id)
    return {"conflicts": conflicts}

# After:
@router.get("/conflicts")
async def list_conflicts(
    relationship_id: str = Query(default=DEFAULT_RELATIONSHIP_ID)
):
    conflicts = db_service.get_all_conflicts(relationship_id)
    return {"conflicts": conflicts}
```

**Files to update:**
- `backend/app/main.py` - `/api/conflicts`, `/api/conflicts/{id}`, `/api/conflicts/create`
- `backend/app/routes/post_fight.py` - All endpoints
- `backend/app/routes/calendar.py` - All endpoints
- `backend/app/routes/analytics.py` - `/api/analytics/dashboard`
- `backend/app/routes/transcription.py` - `/api/transcription/store-transcript`

### 5. Fix RAG Security Bug

**File: `backend/app/services/transcript_rag.py`**

Find the query that's missing `relationship_id` filter and fix it:

```python
# BEFORE (line ~226-233) - SECURITY BUG:
results = await asyncio.to_thread(
    self.pinecone_index.query,
    vector=query_embedding,
    top_k=5,
    namespace="transcript_chunks",
    filter={"conflict_id": {"$ne": conflict_id}},  # Missing relationship filter!
    include_metadata=True,
)

# AFTER - FIXED:
results = await asyncio.to_thread(
    self.pinecone_index.query,
    vector=query_embedding,
    top_k=5,
    namespace="transcript_chunks",
    filter={
        "conflict_id": {"$ne": conflict_id},
        "relationship_id": {"$eq": relationship_id}  # Added filter
    },
    include_metadata=True,
)
```

---

## Frontend Changes

### 1. Create Relationship Context

**File: `frontend/src/contexts/RelationshipContext.tsx`** (NEW)

```typescript
import React, { createContext, useContext, useState, useEffect } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const DEFAULT_RELATIONSHIP_ID = '00000000-0000-0000-0000-000000000000';
const STORAGE_KEY = 'serene_relationship_id';

interface CoupleProfile {
  relationshipId: string;
  partnerAName: string;
  partnerBName: string | null;
}

interface RelationshipContextType {
  relationshipId: string;
  profile: CoupleProfile | null;
  isLoading: boolean;
  setRelationshipId: (id: string) => void;
  createCouple: (partnerAName: string, partnerBName?: string) => Promise<string>;
  refreshProfile: () => Promise<void>;
}

const RelationshipContext = createContext<RelationshipContextType | null>(null);

export function RelationshipProvider({ children }: { children: React.ReactNode }) {
  const [relationshipId, setRelationshipIdState] = useState<string>(() => {
    // Check URL param first, then localStorage, then default
    const urlParams = new URLSearchParams(window.location.search);
    const urlId = urlParams.get('r') || urlParams.get('relationship_id');
    if (urlId) {
      localStorage.setItem(STORAGE_KEY, urlId);
      return urlId;
    }
    return localStorage.getItem(STORAGE_KEY) || DEFAULT_RELATIONSHIP_ID;
  });

  const [profile, setProfile] = useState<CoupleProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const setRelationshipId = (id: string) => {
    localStorage.setItem(STORAGE_KEY, id);
    setRelationshipIdState(id);
  };

  const refreshProfile = async () => {
    try {
      const response = await fetch(
        `${API_URL}/api/couple/profile?relationship_id=${relationshipId}`
      );
      if (response.ok) {
        const data = await response.json();
        setProfile({
          relationshipId: data.relationship_id,
          partnerAName: data.partner_a_name,
          partnerBName: data.partner_b_name,
        });
      } else {
        setProfile(null);
      }
    } catch (error) {
      console.error('Failed to fetch couple profile:', error);
      setProfile(null);
    } finally {
      setIsLoading(false);
    }
  };

  const createCouple = async (
    partnerAName: string,
    partnerBName?: string
  ): Promise<string> => {
    const response = await fetch(`${API_URL}/api/couple/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        partner_a_name: partnerAName,
        partner_b_name: partnerBName,
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to create couple');
    }

    const data = await response.json();
    setRelationshipId(data.relationship_id);
    return data.relationship_id;
  };

  useEffect(() => {
    refreshProfile();
  }, [relationshipId]);

  return (
    <RelationshipContext.Provider
      value={{
        relationshipId,
        profile,
        isLoading,
        setRelationshipId,
        createCouple,
        refreshProfile,
      }}
    >
      {children}
    </RelationshipContext.Provider>
  );
}

export function useRelationship() {
  const context = useContext(RelationshipContext);
  if (!context) {
    throw new Error('useRelationship must be used within a RelationshipProvider');
  }
  return context;
}
```

### 2. Wrap App with Provider

**File: `frontend/src/index.tsx`**

```typescript
import { RelationshipProvider } from './contexts/RelationshipContext';

createRoot(rootElement).render(
  <React.StrictMode>
    <RelationshipProvider>
      <App />
    </RelationshipProvider>
  </React.StrictMode>
);
```

### 3. Update Sidebar to Use Dynamic Names

**File: `frontend/src/components/navigation/Sidebar.tsx`**

```typescript
import { useRelationship } from '../../contexts/RelationshipContext';

const Sidebar = () => {
    const { profile, isLoading } = useRelationship();

    const displayName = profile?.partnerAName || 'Partner A';
    const partnerName = profile?.partnerBName || 'Partner B';

    // ... rest of component uses displayName and partnerName
};
```

### 4. Create API Helper with Relationship ID

**File: `frontend/src/services/api.ts`** (NEW or update existing)

```typescript
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const STORAGE_KEY = 'serene_relationship_id';
const DEFAULT_RELATIONSHIP_ID = '00000000-0000-0000-0000-000000000000';

function getRelationshipId(): string {
  return localStorage.getItem(STORAGE_KEY) || DEFAULT_RELATIONSHIP_ID;
}

export async function apiFetch(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const relationshipId = getRelationshipId();

  // Add relationship_id to URL
  const url = new URL(`${API_URL}${endpoint}`);
  if (!url.searchParams.has('relationship_id')) {
    url.searchParams.set('relationship_id', relationshipId);
  }

  return fetch(url.toString(), {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
}

// Convenience methods
export const api = {
  get: (endpoint: string) => apiFetch(endpoint).then(r => r.json()),

  post: (endpoint: string, data: any) =>
    apiFetch(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    }).then(r => r.json()),

  put: (endpoint: string, data: any) =>
    apiFetch(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    }).then(r => r.json()),
};
```

### 5. Update Pages to Use API Helper

Example for `Home.tsx`:

```typescript
import { api } from '../services/api';
import { useRelationship } from '../contexts/RelationshipContext';

export default function Home() {
  const { profile } = useRelationship();
  const [conflicts, setConflicts] = useState([]);

  useEffect(() => {
    // API helper auto-includes relationship_id
    api.get('/api/conflicts').then(data => {
      setConflicts(data.conflicts);
    });
  }, []);

  return (
    <div>
      <h1>Good morning, {profile?.partnerAName || 'there'}.</h1>
      {/* ... */}
    </div>
  );
}
```

---

## Testing Checklist

- [ ] Migration runs successfully, Adrian/Elara seeded
- [ ] `GET /api/couple/profile?relationship_id=00000...` returns Adrian/Elara
- [ ] `POST /api/couple/create` creates new relationship
- [ ] New relationship_id stored in localStorage
- [ ] All API endpoints accept `relationship_id` parameter
- [ ] Default relationship_id falls back to Adrian/Elara
- [ ] Sidebar shows dynamic partner names
- [ ] URL param `?r={id}` switches relationship context
- [ ] RAG queries are filtered by relationship_id

---

## Files Summary

| File | Action |
|------|--------|
| `backend/app/models/migrations/002_couple_profiles.sql` | Create |
| `backend/app/services/db_service.py` | Add couple profile methods |
| `backend/app/routes/couple_routes.py` | Create |
| `backend/app/main.py` | Register couple routes, update conflict endpoints |
| `backend/app/routes/post_fight.py` | Add relationship_id param |
| `backend/app/routes/calendar.py` | Add relationship_id param |
| `backend/app/routes/analytics.py` | Add relationship_id param |
| `backend/app/services/transcript_rag.py` | Fix security bug |
| `frontend/src/contexts/RelationshipContext.tsx` | Create |
| `frontend/src/services/api.ts` | Create |
| `frontend/src/index.tsx` | Add RelationshipProvider |
| `frontend/src/components/navigation/Sidebar.tsx` | Use dynamic names |
