"""
Security middleware for Phase 5: Security Hardening

Includes:
- Rate limiting
- Security headers
- Input validation
- Audit logging
- Request sanitization
"""
import os
import re
import time
import logging
import hashlib
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
from collections import defaultdict
from functools import wraps

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("security-middleware")


# ============================================
# Rate Limiting
# ============================================

class RateLimiter:
    """In-memory rate limiter with sliding window."""

    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self.config = {
            # Default limits: requests per minute
            "default": {"limit": 60, "window": 60},
            # Specific endpoint limits
            "/api/conflicts/create": {"limit": 10, "window": 60},
            "/api/relationships/create": {"limit": 5, "window": 60},
            "/api/post-fight/analyze": {"limit": 5, "window": 60},
            "/api/mediator/chat": {"limit": 30, "window": 60},
            "/api/pdfs/upload": {"limit": 10, "window": 300},
        }

    def _get_identifier(self, request: Request) -> str:
        """Get unique identifier for rate limiting (IP + relationship_id if available)."""
        # Get client IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        # Try to get relationship_id for more granular limiting
        relationship_id = (
            request.headers.get("X-Relationship-ID") or
            request.query_params.get("relationship_id") or
            ""
        )

        return f"{ip}:{relationship_id}"

    def _get_config(self, path: str) -> Dict[str, int]:
        """Get rate limit config for endpoint."""
        # Check for exact match
        if path in self.config:
            return self.config[path]

        # Check for prefix match
        for endpoint, config in self.config.items():
            if path.startswith(endpoint):
                return config

        return self.config["default"]

    def is_allowed(self, request: Request) -> tuple[bool, Dict[str, Any]]:
        """Check if request is allowed under rate limits."""
        identifier = self._get_identifier(request)
        path = request.url.path
        config = self._get_config(path)

        limit = config["limit"]
        window = config["window"]
        now = time.time()

        # Clean old requests
        self.requests[identifier] = [
            t for t in self.requests[identifier]
            if now - t < window
        ]

        # Check limit
        request_count = len(self.requests[identifier])
        remaining = max(0, limit - request_count - 1)
        reset_time = int(now + window)

        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_time),
        }

        if request_count >= limit:
            headers["Retry-After"] = str(window)
            return False, headers

        # Record request
        self.requests[identifier].append(now)
        return True, headers


# Global rate limiter instance
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
            return await call_next(request)

        allowed, headers = rate_limiter.is_allowed(request)

        if not allowed:
            logger.warning(f"Rate limit exceeded for {request.url.path}")
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please slow down.",
                    "retry_after": headers.get("Retry-After", "60")
                }
            )
            for key, value in headers.items():
                response.headers[key] = value
            return response

        response = await call_next(request)

        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value

        return response


# ============================================
# Security Headers
# ============================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Enable XSS filter
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy (basic)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https: wss:; "
            "frame-ancestors 'none';"
        )

        # Strict Transport Security (for HTTPS)
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # Permissions Policy
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(self), geolocation=()"
        )

        return response


# ============================================
# Input Validation & Sanitization
# ============================================

class InputValidator:
    """Validate and sanitize user input."""

    # Patterns for validation
    UUID_PATTERN = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )

    # XSS patterns to remove
    XSS_PATTERNS = [
        re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'on\w+\s*=', re.IGNORECASE),
        re.compile(r'<iframe[^>]*>', re.IGNORECASE),
        re.compile(r'<object[^>]*>', re.IGNORECASE),
        re.compile(r'<embed[^>]*>', re.IGNORECASE),
    ]

    # SQL injection patterns
    SQL_PATTERNS = [
        re.compile(r"('\s*(OR|AND)\s*')", re.IGNORECASE),
        re.compile(r'(--\s*$)', re.IGNORECASE),
        re.compile(r'(;\s*(DROP|DELETE|UPDATE|INSERT)\s)', re.IGNORECASE),
        re.compile(r"(UNION\s+SELECT)", re.IGNORECASE),
    ]

    @classmethod
    def is_valid_uuid(cls, value: str) -> bool:
        """Check if value is a valid UUID."""
        if not value:
            return False
        return bool(cls.UUID_PATTERN.match(value))

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Sanitize text input to prevent XSS."""
        if not text:
            return text

        result = text
        for pattern in cls.XSS_PATTERNS:
            result = pattern.sub('', result)

        # HTML encode special characters
        result = (
            result
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#x27;')
        )

        return result

    @classmethod
    def check_sql_injection(cls, text: str) -> bool:
        """Check if text contains SQL injection patterns."""
        if not text:
            return False

        for pattern in cls.SQL_PATTERNS:
            if pattern.search(text):
                return True
        return False

    @classmethod
    def validate_relationship_id(cls, relationship_id: str) -> bool:
        """Validate relationship_id format."""
        return cls.is_valid_uuid(relationship_id)

    @classmethod
    def validate_conflict_id(cls, conflict_id: str) -> bool:
        """Validate conflict_id format."""
        return cls.is_valid_uuid(conflict_id)


# Convenience function for route handlers
def validate_uuid(value: str, field_name: str = "ID") -> str:
    """Validate UUID and raise HTTPException if invalid."""
    if not InputValidator.is_valid_uuid(value):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name} format. Must be a valid UUID."
        )
    return value


# ============================================
# Audit Logging
# ============================================

class AuditLogger:
    """Log security-relevant events."""

    def __init__(self):
        self.db_service = None

    def _get_db_service(self):
        """Lazy load db_service to avoid circular imports."""
        if self.db_service is None:
            try:
                from app.services.db_service import db_service
                self.db_service = db_service
            except ImportError:
                pass
        return self.db_service

    def log(
        self,
        action: str,
        table_name: str,
        request: Request,
        record_id: str = None,
        relationship_id: str = None,
        status_code: int = None,
        error_message: str = None,
        metadata: Dict = None
    ):
        """Log an audit event."""
        try:
            # Get client info
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                ip = forwarded.split(",")[0].strip()
            else:
                ip = request.client.host if request.client else None

            user_agent = request.headers.get("User-Agent", "")[:500]

            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": action,
                "table_name": table_name,
                "record_id": record_id,
                "relationship_id": relationship_id,
                "ip_address": ip,
                "user_agent": user_agent,
                "request_path": str(request.url.path),
                "request_method": request.method,
                "status_code": status_code,
                "error_message": error_message,
                "metadata": metadata or {}
            }

            # Log to file/console
            logger.info(f"AUDIT: {action} on {table_name} - {record_id or 'N/A'}")

            # Try to log to database
            db = self._get_db_service()
            if db:
                try:
                    db.create_audit_log(log_entry)
                except Exception as e:
                    logger.warning(f"Failed to write audit log to DB: {e}")

        except Exception as e:
            logger.error(f"Audit logging error: {e}")


# Global audit logger instance
audit_logger = AuditLogger()


# Decorator for auditing route handlers
def audit_action(action: str, table_name: str):
    """Decorator to automatically audit route handler actions."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get('request') or (args[0] if args else None)
            relationship_id = kwargs.get('relationship_id')
            record_id = kwargs.get('conflict_id') or kwargs.get('id')

            try:
                result = await func(*args, **kwargs)
                if request:
                    audit_logger.log(
                        action=action,
                        table_name=table_name,
                        request=request,
                        record_id=record_id,
                        relationship_id=relationship_id,
                        status_code=200
                    )
                return result
            except HTTPException as e:
                if request:
                    audit_logger.log(
                        action=action,
                        table_name=table_name,
                        request=request,
                        record_id=record_id,
                        relationship_id=relationship_id,
                        status_code=e.status_code,
                        error_message=str(e.detail)
                    )
                raise
            except Exception as e:
                if request:
                    audit_logger.log(
                        action=action,
                        table_name=table_name,
                        request=request,
                        record_id=record_id,
                        relationship_id=relationship_id,
                        status_code=500,
                        error_message=str(e)
                    )
                raise

        return wrapper
    return decorator


# ============================================
# Request ID Tracking
# ============================================

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request for tracing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = hashlib.sha256(
            f"{time.time()}{request.client.host if request.client else ''}{request.url.path}".encode()
        ).hexdigest()[:16]

        # Add to request state
        request.state.request_id = request_id

        response = await call_next(request)

        # Add to response headers
        response.headers["X-Request-ID"] = request_id

        return response
