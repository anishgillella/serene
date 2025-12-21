"""
Auth0 JWT verification middleware for FastAPI.
Provides authentication and user context for API endpoints.
"""
import os
from functools import lru_cache
from typing import Optional
import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, jwk
from jose.utils import base64url_decode
from pydantic import BaseModel
import json

from app.config import get_settings

security = HTTPBearer(auto_error=False)


class UserContext(BaseModel):
    """Authenticated user context passed to endpoints."""
    user_id: str  # Our internal user ID (from users table)
    auth0_id: str  # Auth0 sub claim
    email: Optional[str] = None
    name: Optional[str] = None
    relationship_id: Optional[str] = None
    display_name: Optional[str] = None
    partner_display_name: Optional[str] = None


def get_jwks(domain: str) -> dict:
    """Fetch Auth0 JWKS (JSON Web Key Set) for token verification."""
    jwks_url = f"https://{domain}/.well-known/jwks.json"
    try:
        response = httpx.get(jwks_url, timeout=10.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Failed to fetch JWKS: {e}")
        return {"keys": []}


# Cache JWKS for 1 hour to avoid repeated requests
_jwks_cache = {}
_jwks_cache_time = {}

def get_cached_jwks(domain: str) -> dict:
    """Get JWKS with caching."""
    import time
    current_time = time.time()
    cache_duration = 3600  # 1 hour

    if domain in _jwks_cache:
        if current_time - _jwks_cache_time.get(domain, 0) < cache_duration:
            return _jwks_cache[domain]

    jwks = get_jwks(domain)
    _jwks_cache[domain] = jwks
    _jwks_cache_time[domain] = current_time
    return jwks


def verify_token(token: str) -> dict:
    """
    Verify Auth0 JWT and return claims.

    Args:
        token: The JWT access token

    Returns:
        dict: Token claims including 'sub' (Auth0 user ID)

    Raises:
        HTTPException: If token is invalid
    """
    settings = get_settings()

    if not settings.AUTH0_DOMAIN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth0 domain not configured"
        )

    try:
        # Get the key ID from token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing key ID"
            )

        # Fetch JWKS and find matching key
        jwks = get_cached_jwks(settings.AUTH0_DOMAIN)
        rsa_key = None

        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
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
                detail="Unable to find appropriate signing key"
            )

        # Verify and decode the token
        # Note: For Auth0 with default settings, audience might not be set
        # We'll verify with flexible options
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=settings.AUTH0_ALGORITHMS,
                audience=settings.AUTH0_AUDIENCE if settings.AUTH0_AUDIENCE else None,
                issuer=f"https://{settings.AUTH0_DOMAIN}/"
            )
        except JWTError:
            # Try without audience verification (common for Auth0 ID tokens)
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=settings.AUTH0_ALGORITHMS,
                issuer=f"https://{settings.AUTH0_DOMAIN}/",
                options={"verify_aud": False}
            )

        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}"
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserContext:
    """
    Dependency to get current authenticated user.
    Raises 401 if not authenticated.

    Usage:
        @router.get("/protected")
        async def protected_route(current_user: UserContext = Depends(get_current_user)):
            return {"user_id": current_user.user_id}
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Verify the token
    claims = verify_token(credentials.credentials)
    auth0_id = claims.get("sub")

    if not auth0_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing sub claim"
        )

    # Import here to avoid circular imports
    from app.services.db_service import db_service

    # Get or create user in database
    user = db_service.get_user_by_auth0_id(auth0_id)

    if not user:
        # User doesn't exist yet - they need to complete onboarding
        # Return a partial UserContext
        return UserContext(
            user_id="",
            auth0_id=auth0_id,
            email=claims.get("email"),
            name=claims.get("name") or claims.get("nickname")
        )

    # Get user's relationship context
    relationship = db_service.get_user_relationship_context(user["id"])

    return UserContext(
        user_id=str(user["id"]),
        auth0_id=auth0_id,
        email=user.get("email"),
        name=user.get("name"),
        relationship_id=str(relationship["relationship_id"]) if relationship else None,
        display_name=relationship.get("display_name") if relationship else None,
        partner_display_name=relationship.get("partner_display_name") if relationship else None
    )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[UserContext]:
    """
    Dependency to optionally get current user.
    Returns None if not authenticated (for backward compatibility during migration).

    Usage:
        @router.get("/optional-auth")
        async def optional_route(current_user: Optional[UserContext] = Depends(get_current_user_optional)):
            if current_user:
                return {"user_id": current_user.user_id}
            return {"message": "anonymous access"}
    """
    settings = get_settings()

    if not credentials:
        if settings.AUTH_OPTIONAL:
            return None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        return await get_current_user(credentials)
    except HTTPException:
        if settings.AUTH_OPTIONAL:
            return None
        raise


async def get_current_user_with_relationship(
    current_user: UserContext = Depends(get_current_user)
) -> UserContext:
    """
    Dependency that requires user to have an active relationship.
    Use for endpoints that require relationship context.

    Usage:
        @router.get("/relationship-required")
        async def relationship_route(
            current_user: UserContext = Depends(get_current_user_with_relationship)
        ):
            return {"relationship_id": current_user.relationship_id}
    """
    if not current_user.relationship_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must complete onboarding and have an active relationship"
        )
    return current_user
