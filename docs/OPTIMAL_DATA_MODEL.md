# Optimal Data Model for Serene (Relationship Mediator Application)

## Executive Summary

Based on analyzing your application's features and data flows, here's the **optimal data model** with rationale for each design decision.

---

## Core Application Features

1. **Real-time Voice Conversations** (Fight Capture, Mediator Sessions)
2. **Transcript Analysis & RAG** (Semantic search across conversations)
3. **Profile Management** (Partner personalities, relationship handbook)
4. **Calendar & Cycle Tracking** (Menstrual cycles, anniversaries, events)
5. **Conflict Analysis & Repair Plans** (Post-conflict insights)
6. **Private Venting** (Rant sessions for each partner)

---

## Recommended Data Model Architecture

### 🎯 **Hybrid Model: Relational (PostgreSQL) + Vector (Pinecone) + Object Storage (S3)**

```
┌─────────────────────────────────────────────────────────────┐
│                   DATA STORAGE LAYERS                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  PostgreSQL (Supabase)        Pinecone            S3         │
│  ─────────────────────        ────────────        ────────   │
│  • Relationships              • Embeddings        • PDFs     │
│  • Conflicts (metadata)       • Transcripts       • Audio    │
│  • Sessions                   • Profiles          • Large    │
│  • Messages (JSON)            • Semantic Search   • Files    │
│  • Calendar Events                                           │
│  • Cycle Data                                                │
│  • Analysis Results                                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Detailed Table Design with Rationale

### 1️⃣ **Core Entities**

#### `relationships`
**Purpose**: Top-level container for a couple's data
```sql
CREATE TABLE relationships (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    partner_a_id UUID REFERENCES users(id), -- Future: proper user accounts
    partner_b_id UUID REFERENCES users(id),
    partner_a_name TEXT, -- Current: simple names
    partner_b_name TEXT,
    status TEXT DEFAULT 'active', -- active, paused, ended
    metadata JSONB DEFAULT '{}'
);
```

**Rationale**:
- ✅ Central entity for data isolation (multi-tenancy ready)
- ✅ JSONB metadata for flexible custom fields
- ✅ Future-proof with user IDs for authentication

---

#### `conflicts`
**Purpose**: Individual fight/conflict sessions
```sql
CREATE TABLE conflicts (
    id UUID PRIMARY KEY,
    relationship_id UUID REFERENCES relationships(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    status TEXT DEFAULT 'active', -- active, processing, analyzed, resolved
    
    -- Transcript Storage Strategy
    transcript_summary TEXT, -- Brief summary for quick reference
    transcript_vector_id UUID, -- Reference to Pinecone vector
    transcript_s3_path TEXT, -- S3 path for full audio/transcript
    
    -- Conflict Metadata
    severity_score DECIMAL(3,2), -- 0.00 to 1.00 (ML-generated or user-rated)
    conflict_topics TEXT[], -- Array: ["communication", "finances", "intimacy"]
    cycle_phase TEXT, -- Context: which phase was partner in during conflict
    
    metadata JSONB DEFAULT '{}' -- Store additional context
);

CREATE INDEX idx_conflicts_relationship ON conflicts(relationship_id);
CREATE INDEX idx_conflicts_status ON conflicts(status);
CREATE INDEX idx_conflicts_started_at ON conflicts(started_at DESC);
CREATE INDEX idx_conflicts_topics ON conflicts USING GIN(conflict_topics); -- Array search
```

**Rationale**:
- ✅ Status tracking for async processing pipeline
- ✅ **Hybrid storage**: Summary in DB, full data in S3/Pinecone
- ✅ Severity score enables "worst fights" analytics
- ✅ Topics array allows multi-category conflicts
- ✅ Cycle phase correlation for pattern detection
- ✅ GIN index on array for fast topic searches

**Why this approach?**
- Large transcripts (10KB+) bloat the database
- Vector embeddings belong in Pinecone for semantic search
- PostgreSQL stores **metadata** for fast queries
- S3 stores **raw audio/full transcripts** for archival

---

### 2️⃣ **Conversation Storage** (Your Current Focus)

#### `mediator_sessions` + `mediator_messages`

**✅ RECOMMENDED: Single JSON Row Per Session**

```sql
CREATE TABLE mediator_sessions (
    id UUID PRIMARY KEY,
    conflict_id UUID REFERENCES conflicts(id) ON DELETE CASCADE,
    partner_id TEXT, -- "partner_a" or "partner_b"
    session_started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_ended_at TIMESTAMPTZ,
    
    -- Session Insights
    message_count INTEGER DEFAULT 0,
    session_duration_seconds INTEGER,
    sentiment_trend TEXT, -- "improving", "neutral", "worsening"
    
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE mediator_messages (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES mediator_sessions(id) ON DELETE CASCADE UNIQUE, -- ONE ROW PER SESSION
    
    -- Full conversation as JSON array
    content JSONB NOT NULL DEFAULT '[]', -- [{role, content, timestamp}, ...]
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Derived Metrics (updated on each append)
    total_messages INTEGER DEFAULT 0,
    user_message_count INTEGER DEFAULT 0,
    assistant_message_count INTEGER DEFAULT 0,
    
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_mediator_messages_session ON mediator_messages(session_id);
CREATE INDEX idx_mediator_messages_updated_at ON mediator_messages(updated_at DESC);

-- GIN index for fast JSONB queries (e.g., search within conversation)
CREATE INDEX idx_mediator_messages_content ON mediator_messages USING GIN(content);
```

**Rationale for JSON Storage**:
✅ **Atomic Operations**: Update entire conversation in one transaction
✅ **Natural Ordering**: Messages stay in chronological order
✅ **Reduced Complexity**: No JOINs to reconstruct conversation
✅ **Better Cache**: Single row = single cache entry
✅ **Efficient for RAG**: Load full context in one query
✅ **Message Counts**: Denormalized for fast analytics

**Why NOT individual rows?**
❌ More complex queries (need ORDER BY, GROUP BY)
❌ More rows = more index overhead
❌ Harder to ensure conversation atomicity
❌ Streaming updates require multiple writes

**Alternative for VERY long conversations (>1000 messages)**:
- Chunk into multiple rows per session (e.g., `chunk_index`)
- But for most use cases, single JSON is better

---

#### `rant_messages` (Private Venting)

**KEEP AS INDIVIDUAL ROWS** (Different use case!)

```sql
CREATE TABLE rant_messages (
    id UUID PRIMARY KEY,
    conflict_id UUID REFERENCES conflicts(id) ON DELETE CASCADE,
    partner_id TEXT NOT NULL, -- "partner_a" or "partner_b"
    role TEXT NOT NULL, -- "user" or "assistant"
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Sentiment Analysis
    sentiment_score DECIMAL(3,2), -- -1.00 (negative) to 1.00 (positive)
    emotion_tags TEXT[], -- ["frustrated", "hurt", "angry"]
    
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_rant_messages_conflict_partner ON rant_messages(conflict_id, partner_id);
CREATE INDEX idx_rant_messages_created_at ON rant_messages(created_at DESC);
```

**Rationale for ROWS (not JSON)**:
✅ **Sentiment analysis per message** requires individual records
✅ **Real-time streaming** displays messages as they arrive
✅ **Analytics**: Aggregate emotion trends over time
✅ **Filtering**: "Show me all frustrated messages"

---

### 3️⃣ **Profile & Knowledge Base**

#### `profiles`
```sql
CREATE TABLE profiles (
    id UUID PRIMARY KEY,
    relationship_id UUID REFERENCES relationships(id) ON DELETE CASCADE,
    partner_id TEXT, -- "partner_a", "partner_b", or NULL for shared
    
    profile_type TEXT NOT NULL, -- "personality", "handbook", "communication_guide"
    
    -- File Storage
    filename TEXT NOT NULL,
    s3_path TEXT NOT NULL, -- S3://bucket/profiles/relationship_id/profile_id.pdf
    pinecone_vector_id UUID NOT NULL, -- Reference to vector embedding
    
    -- Metadata
    extracted_text_length INTEGER,
    page_count INTEGER,
    upload_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ,
    
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_profiles_relationship ON profiles(relationship_id);
CREATE INDEX idx_profiles_type ON profiles(profile_type);
CREATE INDEX idx_profiles_partner ON profiles(partner_id);
```

**Rationale**:
- ✅ S3 stores actual PDF (cost-effective, durable)
- ✅ Pinecone stores vector embeddings (semantic search)
- ✅ PostgreSQL stores metadata (fast lookups)
- ✅ `last_accessed_at` for cache warming

---

### 4️⃣ **Calendar & Cycle Tracking**

#### `cycle_events` (Single Source of Truth)
```sql
CREATE TABLE cycle_events (
    id UUID PRIMARY KEY,
    relationship_id UUID REFERENCES relationships(id) ON DELETE CASCADE,
    partner_id TEXT NOT NULL,
    
    event_type TEXT NOT NULL, -- "period_start", "period_end", "symptom_log", "mood_log"
    event_date DATE NOT NULL, -- Actual date of event
    logged_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Cycle Context
    cycle_day INTEGER, -- Day of cycle (1 = first day of period)
    
    -- Symptoms/Notes
    symptoms TEXT[], -- ["cramps", "mood_swings", "headache"]
    notes TEXT,
    
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_cycle_events_relationship_partner ON cycle_events(relationship_id, partner_id);
CREATE INDEX idx_cycle_events_date ON cycle_events(event_date DESC);
CREATE INDEX idx_cycle_events_type ON cycle_events(event_type);
```

**Rationale**:
- ✅ **Single Table**: All cycle data (periods, symptoms, moods) in one place
- ✅ **Manual Entry**: Optimized for user-reported data
- ✅ **Simple History**: Focus on past month/recent history
- ✅ **No Predictions**: Removed complexity of ML/forecasting models

---

#### `memorable_dates` (Anniversaries, Birthdays)
```sql
CREATE TABLE memorable_dates (
    id UUID PRIMARY KEY,
    relationship_id UUID REFERENCES relationships(id) ON DELETE CASCADE,
    
    event_type TEXT NOT NULL, -- "anniversary", "birthday", "first_date", "milestone"
    title TEXT NOT NULL,
    description TEXT,
    
    event_date DATE NOT NULL, -- Original date
    is_recurring BOOLEAN DEFAULT TRUE, -- Annual recurrence
    
    -- Reminder Settings
    reminder_days_before INTEGER DEFAULT 7,
    reminder_enabled BOOLEAN DEFAULT TRUE,
    last_reminded_at TIMESTAMPTZ,
    
    -- UI Customization
    color_tag TEXT DEFAULT '#f59e0b',
    icon TEXT, -- "❤️", "🎂", "🎉"
    
    -- Association
    partner_id TEXT, -- NULL for couple events, set for individual
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_memorable_dates_relationship ON memorable_dates(relationship_id);
CREATE INDEX idx_memorable_dates_date ON memorable_dates(event_date);
CREATE INDEX idx_memorable_dates_recurring ON memorable_dates(is_recurring) WHERE is_recurring = TRUE;
```

**Rationale**:
- ✅ Recurring flag for annual events
- ✅ Reminder state tracking (avoid spam)
- ✅ Partial index on recurring events (query optimization)

---

### 5️⃣ **Analytics & Insights**

#### `conflict_analysis` (AI-generated insights)
```sql
CREATE TABLE conflict_analysis (
    id UUID PRIMARY KEY,
    conflict_id UUID REFERENCES conflicts(id) ON DELETE CASCADE,
    relationship_id UUID REFERENCES relationships(id) ON DELETE CASCADE,
    
    -- Analysis Results (stored as structured JSON)
    analysis_data JSONB NOT NULL, -- Full analysis object
    
    -- Quick Access Fields (denormalized from JSON)
    root_causes TEXT[], -- ["communication_breakdown", "unmet_expectations"]
    patterns_identified TEXT[],
    recommended_actions TEXT[],
    
    -- Analysis Metadata
    analysis_version TEXT, -- Track analysis model version
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    time_to_analyze_ms INTEGER, -- Performance tracking
    
    metadata JSONB DEFAULT '{}',
    
    -- Ensure one analysis per conflict
    CONSTRAINT unique_conflict_analysis UNIQUE(conflict_id, relationship_id)
);

CREATE INDEX idx_conflict_analysis_conflict ON conflict_analysis(conflict_id);
CREATE INDEX idx_conflict_analysis_relationship ON conflict_analysis(relationship_id);
CREATE INDEX idx_conflict_analysis_analyzed_at ON conflict_analysis(analyzed_at DESC);
```

**Rationale**:
- ✅ **JSONB for flexible schema**: Analysis format can evolve
- ✅ **Denormalized arrays**: Fast filtering without parsing JSON
- ✅ **Version tracking**: Compare old vs. new model outputs
- ✅ **UNIQUE constraint**: Prevent duplicate analyses

---

#### `repair_plans` (Actionable advice)
```sql
CREATE TABLE repair_plans (
    id UUID PRIMARY KEY,
    conflict_id UUID REFERENCES conflicts(id) ON DELETE CASCADE,
    relationship_id UUID REFERENCES relationships(id) ON DELETE CASCADE,
    partner_requesting TEXT NOT NULL, -- "partner_a" or "partner_b"
    
    -- Plan Data
    plan_data JSONB NOT NULL, -- Full repair plan
    
    -- Action Items (extracted for tracking)
    action_items JSONB DEFAULT '[]', -- [{action, completed, due_date}, ...]
    
    -- Progress Tracking
    completion_percentage DECIMAL(5,2) DEFAULT 0.00, -- 0.00 to 100.00
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Metadata
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    plan_version TEXT,
    
    metadata JSONB DEFAULT '{}',
    
    CONSTRAINT unique_repair_plan UNIQUE(conflict_id, relationship_id, partner_requesting)
);

CREATE INDEX idx_repair_plans_conflict ON repair_plans(conflict_id);
CREATE INDEX idx_repair_plans_relationship ON repair_plans(relationship_id);
CREATE INDEX idx_repair_plans_partner ON repair_plans(partner_requesting);
CREATE INDEX idx_repair_plans_completion ON repair_plans(completion_percentage);
```

**Rationale**:
- ✅ **Action items as JSONB**: Flexible task structure
- ✅ **Progress tracking**: Gamification & accountability
- ✅ **Per-partner plans**: Each partner gets personalized advice

---

### 6️⃣ **Intimacy Tracking**

#### `intimacy_events`
```sql
CREATE TABLE intimacy_events (
    id UUID PRIMARY KEY,
    relationship_id UUID REFERENCES relationships(id) ON DELETE CASCADE,
    
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    initiator_partner_id TEXT, -- NULL if mutual
    
    -- Context (for pattern analysis)
    days_since_last_event INTEGER,
    cycle_day INTEGER, -- Partner's cycle day (if tracked)
    days_since_last_conflict INTEGER,
    
    -- Privacy
    is_encrypted BOOLEAN DEFAULT FALSE, -- Future: E2E encryption
    
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_intimacy_events_relationship ON intimacy_events(relationship_id);
CREATE INDEX idx_intimacy_events_occurred_at ON intimacy_events(occurred_at DESC);
```

**Rationale**:
- ✅ **Minimal data**: Privacy-focused
- ✅ **Context tracking**: Analyze frequency patterns
- ✅ **Encryption flag**: Future-proof for E2E encryption

---

## Key Design Principles Applied

### 1. **Hybrid Storage Strategy**
```
PostgreSQL → Metadata, relationships, small structured data
Pinecone   → Vector embeddings, semantic search
S3         → Large files (PDFs, audio, full transcripts)
```

**Why?**
- Cost optimization (S3 cheapest for storage)
- Performance (Pinecone for semantic search, Postgres for structured queries)
- Scalability (Each system optimized for its workload)

### 2. **Denormalization Where It Matters**
- ✅ Message counts in `mediator_sessions`
- ✅ Root causes array in `conflict_analysis`
- ✅ Completion percentage in `repair_plans`

**Why?**
- Avoid expensive JOINs and aggregations
- Real-time dashboard queries stay fast
- Trade-off: Slightly more complex write logic

### 3. **JSONB for Flexibility**
- ✅ Metadata columns everywhere
- ✅ Full analysis/plan objects
- ✅ Conversation messages

**Why?**
- Schema can evolve without migrations
- Complex nested data (action items, analysis results)
- GIN indexes enable fast JSONB queries

### 4. **Array Types for Multi-Value Fields**
- ✅ Topics, symptoms, emotion tags, root causes

**Why?**
- Native PostgreSQL array support
- GIN indexes for fast array searches
- Cleaner than junction tables for simple lists

### 5. **Timestamp Tracking for Everything**
- `created_at`, `updated_at`, `logged_at`, `generated_at` etc.

**Why?**
- Audit trail
- Analytics (trend analysis over time)
- Debugging (when did this happen?)

### 6. **Composite Indexes for Common Queries**
```sql
-- Example: Query mediator sessions for a conflict by a specific partner
CREATE INDEX idx_mediator_sessions_conflict_partner 
ON mediator_sessions(conflict_id, partner_id);
```

**Why?**
- Single index covers multi-column WHERE clauses
- Faster than separate indexes

---

## Migration Path from Current to Optimal

### Phase 1: Immediate (Already Done ✅)
- [x] Convert `mediator_messages` to single JSON row per session

### Phase 2: Short-term (Next Sprint)
```sql
-- Add missing columns to conflicts
ALTER TABLE conflicts 
ADD COLUMN severity_score DECIMAL(3,2),
ADD COLUMN conflict_topics TEXT[],
ADD COLUMN cycle_phase TEXT;

-- Add derived metrics to mediator_sessions
ALTER TABLE mediator_sessions
ADD COLUMN message_count INTEGER DEFAULT 0,
ADD COLUMN session_duration_seconds INTEGER,
ADD COLUMN sentiment_trend TEXT;

-- Add version tracking to analysis/plans
ALTER TABLE conflict_analysis ADD COLUMN analysis_version TEXT;
ALTER TABLE repair_plans ADD COLUMN plan_version TEXT;
```

### Phase 3: Medium-term (Future)
- Add user authentication (replace TEXT partner_id with UUID user_id)
- Implement E2E encryption for sensitive data
- Add soft deletes (deleted_at columns) for data retention policies

---

## Performance Optimization Checklist

✅ **Indexes Created**
- All foreign keys indexed
- Timestamp columns for time-range queries
- GIN indexes for JSONB/array searches
- Composite indexes for multi-column WHERE clauses

✅ **Query Optimization**
- Denormalized counts to avoid COUNT(*) queries
- Partial indexes for frequent filtered queries
- Materialized views for complex analytics (future)

✅ **Caching Strategy**
- Redis for hot data (active sessions, recent conflicts)
- CDN for static assets (profile PDFs, analysis reports)
- Application-level caching for RAG context

---

## Conclusion

Your **optimal data model** is:

1. **Relational (PostgreSQL)** for structured data, relationships, and fast queries
2. **Vector (Pinecone)** for semantic search across transcripts/profiles
3. **Object Storage (S3)** for large files and archival
4. **JSONB** for flexible schemas and nested data
5. **Single JSON row per session** for conversation storage (performance + simplicity)

This hybrid approach gives you:
- ✅ Scalability (each component scales independently)
- ✅ Performance (optimized for each data type)
- ✅ Flexibility (JSONB for evolving schemas)
- ✅ Cost efficiency (S3 for cheap storage, Pinecone for AI)
- ✅ Query power (PostgreSQL for complex analytics)

---

**Next Steps**:
1. Review this model with your team
2. Run Phase 2 migrations (add missing columns)
3. Update application code to use new fields
4. Monitor query performance and add indexes as needed
