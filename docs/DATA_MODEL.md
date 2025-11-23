# HeartSync Data Model & Storage Architecture

Complete data storage architecture for ground truth verification and efficient querying.

---

## Storage Strategy: Triple Redundancy

Every critical piece of data is stored in **3 places** for maximum reliability and efficiency:

1. **Supabase Database** - Structured metadata, relationships, fast queries
2. **Supabase Storage** - Raw files (PDFs, JSON transcripts) for backup
3. **Pinecone** - Vector embeddings for semantic search and RAG

---

## Data Storage Matrix

| Data Type | Supabase DB | Supabase Storage | Pinecone | Purpose |
|-----------|-------------|------------------|----------|---------|
| **Profiles** | ✅ `profiles` table | ✅ `profiles` bucket (PDF) | ✅ `profiles` namespace | Personalization, RAG |
| **Handbooks** | ✅ `profiles` table | ✅ `handbooks` bucket (PDF) | ✅ `handbooks` namespace | Guidance, RAG |
| **Transcripts** | ✅ `conflicts` table | ✅ `transcripts` bucket (JSON) | ✅ `transcripts` namespace | Analysis, RAG |
| **Analysis** | ✅ `conflict_analysis` table | ✅ `analysis` bucket (JSON) | ✅ `analysis` namespace | Insights, RAG |
| **Repair Plans** | ✅ `repair_plans` table | ✅ `repair_plans` bucket (JSON) | ✅ `repair_plans` namespace | Coaching, RAG |
| **Rant Messages** | ✅ `rant_messages` table | ❌ | ❌ | Private conversations |
| **Mediator Sessions** | ✅ `mediator_sessions` table | ❌ | ❌ | Luna conversations |
| **Mediator Messages** | ✅ `mediator_messages` table | ❌ | ❌ | Luna messages |
| **Cycle Events** | ✅ `cycle_events` table | ❌ | ❌ | Tracking |
| **Intimacy Events** | ✅ `intimacy_events` table | ❌ | ❌ | Tracking |

---

## Database Schema (Supabase PostgreSQL)

### Core Tables

#### `relationships`
```sql
id UUID PRIMARY KEY
created_at TIMESTAMP
partner_a_name TEXT
partner_b_name TEXT
```

#### `conflicts`
```sql
id UUID PRIMARY KEY
relationship_id UUID REFERENCES relationships(id)
started_at TIMESTAMP
ended_at TIMESTAMP
transcript_path TEXT  -- Path in Supabase Storage
status TEXT  -- active, processing, completed
metadata JSONB
```

#### `profiles`
```sql
id UUID PRIMARY KEY
relationship_id UUID REFERENCES relationships(id)
pdf_type TEXT  -- boyfriend_profile, girlfriend_profile, handbook
partner_id TEXT  -- Optional
filename TEXT
file_path TEXT  -- Path in Supabase Storage
pdf_id UUID  -- Reference to Pinecone vector ID
extracted_text_length INTEGER
uploaded_at TIMESTAMP
metadata JSONB
```

#### `conflict_analysis` (NEW - to be added)
```sql
id UUID PRIMARY KEY
conflict_id UUID REFERENCES conflicts(id)
analysis_path TEXT  -- Path in Supabase Storage (JSON)
analyzed_at TIMESTAMP
metadata JSONB
```

#### `repair_plans` (NEW - to be added)
```sql
id UUID PRIMARY KEY
conflict_id UUID REFERENCES conflicts(id)
partner_requesting TEXT  -- partner_a or partner_b
plan_path TEXT  -- Path in Supabase Storage (JSON)
generated_at TIMESTAMP
metadata JSONB
```

#### `rant_messages`
```sql
id UUID PRIMARY KEY
conflict_id UUID REFERENCES conflicts(id)
partner_id TEXT  -- partner_a or partner_b
role TEXT  -- user or assistant
content TEXT
created_at TIMESTAMP
metadata JSONB
```

#### `mediator_sessions`
```sql
id UUID PRIMARY KEY
conflict_id UUID REFERENCES conflicts(id)
session_started_at TIMESTAMP
session_ended_at TIMESTAMP
partner_id TEXT  -- Optional
metadata JSONB
```

#### `mediator_messages`
```sql
id UUID PRIMARY KEY
session_id UUID REFERENCES mediator_sessions(id)
role TEXT  -- user or assistant
content TEXT
created_at TIMESTAMP
metadata JSONB
```

#### `cycle_events`
```sql
id UUID PRIMARY KEY
partner_id TEXT
event_type TEXT  -- period_start, period_end, ovulation, etc.
timestamp TIMESTAMP
notes TEXT
metadata JSONB
```

#### `intimacy_events`
```sql
id UUID PRIMARY KEY
relationship_id UUID REFERENCES relationships(id)
timestamp TIMESTAMP
initiator_partner_id TEXT
metadata JSONB
```

---

## Supabase Storage Buckets

### `transcripts` bucket
- **Format**: JSON files
- **Path**: `{relationship_id}/{conflict_id}.json`
- **Content**: Raw transcript segments with speaker labels
- **Purpose**: Backup, direct access, ground truth

### `profiles` bucket
- **Format**: PDF files
- **Path**: `{relationship_id}/{pdf_id}.pdf`
- **Content**: Original profile PDFs
- **Purpose**: Backup, re-processing, ground truth

### `handbooks` bucket
- **Format**: PDF files
- **Path**: `{relationship_id}/{pdf_id}.pdf`
- **Content**: Original handbook PDFs
- **Purpose**: Backup, re-processing, ground truth

### `analysis` bucket (NEW - to be added)
- **Format**: JSON files
- **Path**: `{relationship_id}/{conflict_id}_analysis.json`
- **Content**: Full analysis JSON
- **Purpose**: Backup, ground truth verification

### `repair_plans` bucket (NEW - to be added)
- **Format**: JSON files
- **Path**: `{relationship_id}/{conflict_id}_repair_{partner_id}.json`
- **Content**: Full repair plan JSON
- **Purpose**: Backup, ground truth verification

---

## Pinecone Namespaces

### `transcripts` namespace
- **Vector ID**: `transcript_{conflict_id}`
- **Metadata**: conflict_id, relationship_id, transcript_text (up to 35KB), timestamp, duration, partners
- **Purpose**: Semantic search for similar conflicts, RAG retrieval

### `analysis` namespace
- **Vector ID**: `analysis_{conflict_id}`
- **Metadata**: conflict_id, fight_summary, root_causes, full_analysis_json (up to 35KB)
- **Purpose**: Semantic search for similar analyses, RAG retrieval

### `repair_plans` namespace
- **Vector ID**: `repair_plan_{conflict_id}` (or `repair_plan_{conflict_id}_{partner_id}`)
- **Metadata**: conflict_id, partner_requesting, steps, apology_script, full_repair_plan_json (up to 35KB)
- **Purpose**: Semantic search for similar repair plans, RAG retrieval

### `profiles` namespace
- **Vector ID**: `{pdf_type}_{pdf_id}` (e.g., `boyfriend_profile_{uuid}`)
- **Metadata**: pdf_id, relationship_id, pdf_type, extracted_text (up to 40KB), filename
- **Purpose**: Semantic search for relevant profile information, RAG retrieval

### `handbooks` namespace
- **Vector ID**: `handbook_{pdf_id}` (or `handbook_{pdf_id}_chunk_{i}` for large docs)
- **Metadata**: pdf_id, relationship_id, extracted_text (chunked if >40KB), filename
- **Purpose**: Semantic search for handbook guidance, RAG retrieval

---

## Query Patterns & Performance

### Fast Lookups (Supabase DB)
- **Use Case**: Get conflict by ID, list conflicts for relationship
- **Latency**: <10ms
- **Query**: Direct SQL with indexes

### Semantic Search (Pinecone)
- **Use Case**: Find similar conflicts, relevant profile info, handbook guidance
- **Latency**: 50-200ms
- **Query**: Vector similarity search

### File Access (Supabase Storage)
- **Use Case**: Download original PDF, get raw transcript JSON
- **Latency**: 100-500ms
- **Query**: Direct file download

### Ground Truth Verification
- **Use Case**: Verify data integrity, compare sources
- **Process**: 
  1. Query Supabase DB for metadata
  2. Fetch file from Supabase Storage
  3. Query Pinecone for vector embedding
  4. Compare all three sources

---

## Data Flow Examples

### Upload Profile PDF
```
1. User uploads PDF → FastAPI endpoint
2. Extract text via OCR → Mistral
3. Generate embedding → Voyage-3
4. Store in Supabase Storage → profiles bucket
5. Store metadata in Supabase DB → profiles table
6. Store vector in Pinecone → profiles namespace
```

### Capture Conflict Transcript
```
1. Fight ends → Transcript segments collected
2. Store in Supabase Storage → transcripts bucket (JSON)
3. Update Supabase DB → conflicts table (metadata + path)
4. Generate embedding → Voyage-3
5. Store vector in Pinecone → transcripts namespace
```

### Generate Analysis
```
1. Analysis generated → LLM (OpenRouter)
2. Store in Supabase Storage → analysis bucket (JSON)
3. Store metadata in Supabase DB → conflict_analysis table
4. Generate embedding → Voyage-3
5. Store vector in Pinecone → analysis namespace
```

---

## Indexes for Performance

### Database Indexes
- `conflicts.relationship_id` - Fast relationship lookups
- `conflicts.started_at DESC` - Recent conflicts first
- `profiles.relationship_id` - Fast profile lookups
- `profiles.pdf_type` - Filter by type
- `mediator_messages.session_id` - Fast message retrieval
- `cycle_events.partner_id` - Fast cycle queries
- `intimacy_events.relationship_id` - Fast intimacy queries

### Pinecone Indexes
- Metadata filters: `conflict_id`, `relationship_id`, `pdf_type`
- Vector similarity: Cosine distance (default)

---

## Data Integrity & Verification

### Consistency Checks
1. **Conflict exists in all 3 places**: DB → Storage → Pinecone
2. **Profile exists in all 3 places**: DB → Storage → Pinecone
3. **Analysis exists in all 3 places**: DB → Storage → Pinecone
4. **Repair plan exists in all 3 places**: DB → Storage → Pinecone

### Verification Scripts
- `verify_data_integrity.py` - Check all conflicts/profiles/analysis
- `query_ground_truth.py` - Query and compare all sources
- `sync_missing_data.py` - Sync missing data between sources

---

## Storage Costs & Limits

### Supabase Database
- **Free Tier**: 500MB database, 1GB storage
- **Paid Tier**: $25/month for 8GB database, 100GB storage

### Supabase Storage
- **Free Tier**: 1GB
- **Paid Tier**: $0.021/GB/month

### Pinecone
- **Free Tier**: 1 index, 100K vectors
- **Paid Tier**: $70/month for 1M vectors (Serverless)

### Optimization
- Store only essential metadata in Pinecone (40KB limit)
- Store full data in Supabase Storage (unlimited)
- Use database for fast queries and relationships

---

## Migration Checklist

- [x] Create all database tables
- [x] Create Supabase Storage buckets
- [x] Implement triple storage for transcripts
- [x] Implement triple storage for profiles
- [x] Add `conflict_analysis` table
- [x] Add `repair_plans` table
- [x] Implement triple storage for analysis
- [x] Implement triple storage for repair plans
- [x] Create verification scripts
- [x] Create ground truth query scripts

## Verification Scripts

Located in `backend/scripts/`:

1. **`verify_data_integrity.py`** - Checks all data exists in all 3 locations
2. **`query_ground_truth.py`** - Query and compare data from all sources

See `backend/scripts/README.md` for usage instructions.

