"""
Local auth routes — signup / login / me  (JWT + bcrypt)
Mounted at /api/auth in main.py
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.services.db_service import db_service, DEFAULT_RELATIONSHIP_ID
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_token,
    get_current_user,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_partner_role(user_id: str, user_name: str):
    """Look up relationship and return partner_role dict (or None)."""
    try:
        from psycopg2.extras import RealDictCursor

        with db_service.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, partner_a_id, partner_b_id, partner_a_name, partner_b_name
                    FROM relationships
                    WHERE partner_a_id = %s OR partner_b_id = %s
                    LIMIT 1
                    """,
                    (user_id, user_id),
                )
                rel = cur.fetchone()

        if not rel:
            return None

        if str(rel["partner_a_id"]) == user_id:
            return {
                "partner_role": "partner_a",
                "partner_name": rel["partner_a_name"] or user_name,
                "other_partner_name": rel["partner_b_name"] or "Partner",
                "relationship_id": str(rel["id"]),
            }
        else:
            return {
                "partner_role": "partner_b",
                "partner_name": rel["partner_b_name"] or user_name,
                "other_partner_name": rel["partner_a_name"] or "Partner",
                "relationship_id": str(rel["id"]),
            }
    except Exception:
        return None


def _auto_link_user(user_id: str, email: str, name: str):
    """
    If the email matches one of the seeded accounts, link the user into
    the default relationship as partner_a or partner_b.
    """
    try:
        role = None
        if email == "adrian@serene.app" or (name and "adrian" in name.lower()):
            role = "partner_a"
            col_id = "partner_a_id"
            col_name = "partner_a_name"
            display = name or "Adrian Malhotra"
        elif email == "elara@serene.app" or (name and "elara" in name.lower()):
            role = "partner_b"
            col_id = "partner_b_id"
            col_name = "partner_b_name"
            display = name or "Elara Voss"

        if not role:
            return

        with db_service.get_db_context() as conn:
            with conn.cursor() as cur:
                # Ensure default relationship exists
                cur.execute(
                    """
                    INSERT INTO relationships (id, partner_a_name, partner_b_name, created_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (DEFAULT_RELATIONSHIP_ID, "Adrian Malhotra", "Elara Voss"),
                )
                # Link user
                cur.execute(
                    f"UPDATE relationships SET {col_id} = %s, {col_name} = %s WHERE id = %s",
                    (user_id, display, DEFAULT_RELATIONSHIP_ID),
                )
                conn.commit()
    except Exception as e:
        print(f"Auto-link warning: {e}")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/signup")
async def signup(body: SignupRequest):
    """Create a new user with hashed password, auto-link to relationship, return JWT."""
    from psycopg2.extras import RealDictCursor

    # Check for duplicate email
    try:
        with db_service.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id FROM serene_users WHERE email = %s", (body.email,))
                if cur.fetchone():
                    raise HTTPException(status_code=409, detail="Email already registered")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Create user
    try:
        pw_hash = hash_password(body.password)
        with db_service.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO serene_users (email, name, password_hash, created_at, last_login)
                    VALUES (%s, %s, %s, NOW(), NOW())
                    RETURNING id, email, name
                    """,
                    (body.email, body.name, pw_hash),
                )
                user = cur.fetchone()
                conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    user_id = str(user["id"])

    # Auto-link to default relationship if applicable
    _auto_link_user(user_id, body.email, body.name)

    token = create_token(user_id, user["email"], user["name"])
    role_info = _resolve_partner_role(user_id, user["name"]) or {}

    return {
        "token": token,
        "user": {
            "id": user_id,
            "email": user["email"],
            "name": user["name"],
        },
        **role_info,
    }


@router.post("/login")
async def login(body: LoginRequest):
    """Verify credentials, return JWT + user info + partner_role."""
    from psycopg2.extras import RealDictCursor

    try:
        with db_service.get_db_context() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, email, name, password_hash FROM serene_users WHERE email = %s",
                    (body.email,),
                )
                user = cur.fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not user or not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_id = str(user["id"])

    # Update last_login
    try:
        with db_service.get_db_context() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE serene_users SET last_login = NOW() WHERE id = %s", (user_id,))
                conn.commit()
    except Exception:
        pass

    token = create_token(user_id, user["email"], user["name"])
    role_info = _resolve_partner_role(user_id, user["name"]) or {}

    return {
        "token": token,
        "user": {
            "id": user_id,
            "email": user["email"],
            "name": user["name"],
        },
        **role_info,
    }


@router.get("/me")
async def me(request: Request):
    """Protected endpoint -- return current user info + partner_role."""
    payload = get_current_user(request)
    user_id = payload["sub"]
    role_info = _resolve_partner_role(user_id, payload.get("name", "")) or {}

    return {
        "user": {
            "id": user_id,
            "email": payload.get("email"),
            "name": payload.get("name"),
        },
        **role_info,
    }
