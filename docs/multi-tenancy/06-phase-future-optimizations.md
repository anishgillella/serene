# Phase 6: Future Optimizations

## Overview

This phase outlines future improvements for performance, scalability, and additional features. These are not required for the initial multi-tenant MVP but should be considered as the user base grows.

---

## Performance Optimizations

### 1. Redis Caching Layer

**Purpose**: Reduce database load and improve response times for frequently accessed data.

**What to Cache**:
```
- User context (5 min TTL)
- Relationship data (5 min TTL)
- Speaker labels (10 min TTL)
- Analytics dashboard (1 min TTL)
- Conflict lists (30 sec TTL)
```

**Implementation**:
```python
# backend/app/services/cache_service.py
import redis
import json
from functools import wraps

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

def cached(key_prefix: str, ttl: int = 300):
    """Decorator for caching function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{hash(str(args) + str(kwargs))}"

            # Try cache first
            cached_value = redis_client.get(cache_key)
            if cached_value:
                return json.loads(cached_value)

            # Call function and cache result
            result = await func(*args, **kwargs)
            redis_client.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator


# Usage:
@cached("user_context", ttl=300)
async def get_user_context(user_id: str):
    return db_service.get_user_relationship_context(user_id)
```

### 2. Database Connection Pooling

**Current**: New connection per request
**Target**: Connection pool with asyncpg

```python
# backend/app/services/db_pool.py
import asyncpg
from contextlib import asynccontextmanager

class DatabasePool:
    def __init__(self):
        self.pool = None

    async def init(self):
        self.pool = await asyncpg.create_pool(
            dsn=os.getenv("DATABASE_URL"),
            min_size=5,
            max_size=20,
            command_timeout=60
        )

    @asynccontextmanager
    async def connection(self):
        async with self.pool.acquire() as conn:
            yield conn

    async def close(self):
        await self.pool.close()

db_pool = DatabasePool()

# In main.py:
@app.on_event("startup")
async def startup():
    await db_pool.init()

@app.on_event("shutdown")
async def shutdown():
    await db_pool.close()
```

### 3. Query Optimization

**Add Missing Indexes**:
```sql
-- Frequently queried columns
CREATE INDEX CONCURRENTLY idx_conflicts_created_at
    ON conflicts(created_at DESC);

CREATE INDEX CONCURRENTLY idx_conflicts_relationship_status
    ON conflicts(relationship_id, status);

CREATE INDEX CONCURRENTLY idx_mediator_messages_session
    ON mediator_messages(session_id, created_at);

CREATE INDEX CONCURRENTLY idx_cycle_events_date
    ON cycle_events(relationship_id, event_date DESC);
```

### 4. Background Job Processing

**Current**: FastAPI BackgroundTasks (in-process)
**Target**: Celery or similar for reliable job processing

```python
# backend/app/tasks/celery.py
from celery import Celery

celery_app = Celery(
    "serene",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
)

@celery_app.task
def generate_conflict_analysis(conflict_id: str, relationship_id: str):
    """Background task for conflict analysis."""
    # ... analysis logic
    pass

@celery_app.task
def send_invitation_email(to_email: str, inviter_name: str, invitation_url: str):
    """Background task for sending emails."""
    # ... email logic
    pass
```

---

## Scalability Improvements

### 1. Read Replicas

**Architecture**:
```
                    ┌─────────────────┐
                    │   Primary DB    │
                    │   (Writes)      │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
       ┌──────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
       │  Replica 1  │ │  Replica 2 │ │  Replica 3 │
       │   (Reads)   │ │   (Reads)  │ │   (Reads)  │
       └─────────────┘ └────────────┘ └────────────┘
```

**Implementation**:
```python
# backend/app/services/db_service.py
class DatabaseService:
    def __init__(self):
        self.write_pool = create_pool(os.getenv("DATABASE_URL"))
        self.read_pool = create_pool(os.getenv("DATABASE_REPLICA_URL"))

    async def read(self, query, params):
        """Use replica for reads."""
        async with self.read_pool.connection() as conn:
            return await conn.fetch(query, *params)

    async def write(self, query, params):
        """Use primary for writes."""
        async with self.write_pool.connection() as conn:
            return await conn.execute(query, *params)
```

### 2. Pinecone Index Sharding

**Current**: Single index for all data
**Target**: Multiple indexes or namespaces per tenant

**Option A: Namespace per relationship** (simpler)
```python
namespace = f"relationship_{relationship_id}"
pinecone_index.upsert(vectors, namespace=namespace)
```

**Option B: Index per tier** (for scale)
```python
# Free tier: shared index with filters
# Premium tier: dedicated index
if is_premium_relationship(relationship_id):
    index = get_premium_index(relationship_id)
else:
    index = shared_index
```

### 3. CDN for Static Assets

**Setup**:
```
Frontend Build → S3 Bucket → CloudFront CDN
                                  ↓
                           Global Edge Locations
```

**Vite Config**:
```typescript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          livekit: ['livekit-client', '@livekit/components-react'],
        }
      }
    }
  }
})
```

---

## Feature Roadmap

### 1. Real-Time Partner Notifications

**WebSocket for partner activity**:
```python
# backend/app/routes/websocket.py
from fastapi import WebSocket

@app.websocket("/ws/{relationship_id}")
async def websocket_endpoint(websocket: WebSocket, relationship_id: str):
    await websocket.accept()
    # Subscribe to relationship channel
    async for message in pubsub.listen(f"relationship:{relationship_id}"):
        await websocket.send_json(message)
```

**Notifications**:
- Partner started recording
- New conflict analyzed
- Repair plan generated
- Partner accepted invitation

### 2. Multi-Language Support (i18n)

**Backend**:
```python
from fastapi_babel import Babel

babel = Babel(app, default_locale="en")

@babel.localeselector
def get_locale():
    return request.headers.get("Accept-Language", "en")[:2]
```

**Frontend**:
```typescript
// Using react-i18next
import i18n from 'i18next';
import { useTranslation } from 'react-i18next';

const { t } = useTranslation();
<h1>{t('welcome', { name: displayName })}</h1>
```

### 3. Offline Mode with Sync

**Service Worker**:
```typescript
// Register service worker for offline support
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js');
}

// IndexedDB for local storage
const db = await openDB('serene', 1, {
  upgrade(db) {
    db.createObjectStore('conflicts', { keyPath: 'id' });
    db.createObjectStore('pending_transcripts', { keyPath: 'id' });
  }
});
```

### 4. Partner Availability Status

**Show when partner is online**:
```typescript
interface PartnerStatus {
  online: boolean;
  lastSeen: Date;
  currentActivity?: 'recording' | 'reviewing' | 'idle';
}

// Heartbeat every 30 seconds
setInterval(() => {
  api.post('/api/presence/heartbeat');
}, 30000);
```

---

## Billing & Monetization

### 1. Subscription Plans

**Database Schema**:
```sql
CREATE TABLE subscription_plans (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    price_monthly DECIMAL(10,2),
    price_yearly DECIMAL(10,2),
    features JSONB,
    limits JSONB
);

CREATE TABLE subscriptions (
    id UUID PRIMARY KEY,
    relationship_id UUID REFERENCES relationships(id),
    plan_id UUID REFERENCES subscription_plans(id),
    status TEXT CHECK (status IN ('active', 'past_due', 'canceled')),
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    stripe_subscription_id TEXT
);
```

**Plans**:
```
Free:
  - 3 conflicts/month
  - Basic analysis
  - 5 Luna minutes/month

Premium ($9.99/month):
  - Unlimited conflicts
  - Advanced analysis
  - Unlimited Luna
  - Cycle insights
  - Partner notifications

Couples Therapy ($29.99/month):
  - Everything in Premium
  - Therapist dashboard access
  - Progress reports
  - Video session recordings
```

### 2. Stripe Integration

```python
# backend/app/routes/billing.py
import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@router.post("/create-checkout-session")
async def create_checkout(
    plan_id: str,
    current_user: UserContext = Depends(get_current_user)
):
    session = stripe.checkout.Session.create(
        customer_email=current_user.email,
        line_items=[{"price": plan_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{FRONTEND_URL}/billing/success",
        cancel_url=f"{FRONTEND_URL}/billing/cancel",
        metadata={"relationship_id": current_user.relationship_id}
    )
    return {"checkout_url": session.url}

@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    event = stripe.Webhook.construct_event(
        payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
    )

    if event.type == "checkout.session.completed":
        # Activate subscription
        pass
    elif event.type == "invoice.payment_failed":
        # Handle failed payment
        pass

    return {"status": "ok"}
```

### 3. Usage Tracking

```python
# backend/app/services/usage_service.py
class UsageService:
    def track_conflict(self, relationship_id: str):
        """Track conflict usage for billing limits."""
        key = f"usage:{relationship_id}:{current_month()}"
        redis_client.hincrby(key, "conflicts", 1)
        redis_client.expire(key, 60 * 60 * 24 * 35)  # 35 days

    def track_luna_minutes(self, relationship_id: str, minutes: float):
        """Track Luna usage."""
        key = f"usage:{relationship_id}:{current_month()}"
        redis_client.hincrbyfloat(key, "luna_minutes", minutes)

    def check_limit(self, relationship_id: str, feature: str) -> bool:
        """Check if user is within their plan limits."""
        usage = self.get_usage(relationship_id)
        limits = self.get_plan_limits(relationship_id)

        return usage.get(feature, 0) < limits.get(feature, float('inf'))
```

---

## Monitoring & Observability

### 1. Application Metrics

```python
# backend/app/middleware/metrics.py
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response
```

### 2. Error Tracking (Sentry)

```python
# backend/app/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,
    environment=os.getenv("ENVIRONMENT", "development")
)
```

### 3. Logging Infrastructure

```python
# backend/app/logging.py
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
)

logger = structlog.get_logger()

# Usage:
logger.info("conflict_created", conflict_id=conflict_id, user_id=user_id)
```

---

## Implementation Priority

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| **P0** | Redis caching | 2 days | High |
| **P0** | Connection pooling | 1 day | High |
| **P1** | Background job queue | 3 days | Medium |
| **P1** | WebSocket notifications | 2 days | Medium |
| **P2** | Read replicas | 2 days | Medium |
| **P2** | Billing integration | 5 days | High |
| **P3** | Multi-language | 3 days | Low |
| **P3** | Offline mode | 5 days | Low |

---

## Summary

This phase provides a roadmap for scaling Serene from MVP to production-grade application. Prioritize based on:

1. **User growth rate** - Scale infrastructure before hitting limits
2. **Revenue goals** - Implement billing when ready to monetize
3. **User feedback** - Add features users actually request

The core multi-tenancy (Phases 1-5) should be completed first before investing in these optimizations.
