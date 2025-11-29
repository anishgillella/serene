# Serene - AI-Powered Relationship Mediator

A sophisticated voice-enabled AI system that helps couples navigate conflicts through real-time mediation, intelligent context retrieval, and personalized repair strategies - powered by advanced RAG architecture and cycle-aware insights.

---

##  Overview

**Serene** is an AI relationship companion that provides:
-  **Real-time Voice Mediation** with Luna, your empathetic AI coach
-  **Conflict Analysis & Insights** powered by GPT-4o-mini
-  **RAG-Enabled Memory** that remembers all conversations and partner profiles
-  **Cycle-Aware Timing** integrated with menstrual cycle tracking
-  **Personalized Repair Plans** with actionable steps
-  **Analytics Dashboard** to track relationship health and patterns

**MVP Scope:** Currently configured for a single couple (Adrian & Elara). Multi-tenant support planned for future releases.

---

## Agent Tools

Luna has access to intelligent tools that enhance her mediation capabilities:

### 1. **find_similar_conflicts**
- Searches past conflict history using semantic similarity
- Identifies patterns and recurring themes
- Returns summaries of similar past discussions
- Uses Pinecone vector search with relationship filtering

### 2. **get_elara_perspective**
- Analyzes situations from Elara's viewpoint based on her profile
- Uses partner personality data from uploaded PDFs
- Provides empathetic explanations of likely thoughts/feelings
- Powered by GPT-4o-mini with profile-aware prompting

**Tool Features:**
- In-memory caching (5-minute TTL) for performance
- Langfuse observability integration
- Graceful degradation on errors
- Async execution for non-blocking responses

---

##  Quick Start

To run the application locally, you need **3 separate terminal windows**:

### Terminal 1: Backend API
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2: Frontend
```bash
cd frontend
npm run dev
```

### Terminal 3: Voice Agent (Luna)
```bash
cd backend
source venv/bin/activate
python start_agent.py start
```

**Access:**
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs

---

##  System Architecture

### High-Level Flow
```
User (Browser) ←→ React Frontend ←→ FastAPI Backend ←→ LiveKit Cloud
                                           ↓
                                  LiveKit Agent (Luna)
                                           ↓
                         RAG System (Pinecone + Embeddings)
                                           ↓
                              LLM (GPT-4o-mini) + TTS
```

### Technology Stack

| **Layer** | **Technology** | **Purpose** |
|-----------|----------------|-------------|
| **Frontend** | React 18 + TypeScript + Vite | UI, real-time audio, conflict capture |
| **Styling** | TailwindCSS + Custom CSS | Premium glassmorphic design |
| **Backend API** | FastAPI + Python 3.11 | REST endpoints, business logic |
| **Database** | PostgreSQL (Supabase) | Metadata, conflicts, profiles, events |
| **File Storage** | AWS S3 | Transcripts, analysis, repair plans |
| **Vector DB** | Pinecone (Serverless) | Semantic search for RAG |
| **Embeddings** | Voyage-3 (1024-dim) | High-quality semantic embeddings |
| **Reranker** | Voyage-Rerank-2 | Precision ranking for retrieval |
| **Voice Agent** | LiveKit Agents Framework | Real-time voice orchestration |
| **STT** | Deepgram Nova-3 | Speech-to-text with diarization |
| **LLM** | GPT-4o-mini (OpenRouter) | Conversational AI |
| **TTS** | ElevenLabs Flash v2.5 | Natural voice synthesis |
| **Chunking** | LangChain RecursiveCharacterTextSplitter | Intelligent text segmentation |

### Architecture Diagrams

#### 1. Voice Agent Pipeline
```
User Speech → Deepgram STT → VAD Detection → LLM (GPT-4o-mini) → ElevenLabs TTS → User Audio
                                    ↓
                            RAG Context Injection
                                    ↓
                    [Pinecone: Transcripts + Profiles]
```

#### 2. RAG System Architecture
```
User Query
    ↓
Query Embedding (Voyage-3)
    ↓
Parallel Retrieval:
├─ Transcript Chunks (Pinecone: transcript_chunks namespace)
├─ Partner Profiles (Pinecone: profiles namespace)
└─ Past Conflicts (PostgreSQL via db_service)
    ↓
Reranking (Voyage-Rerank-2)
    ↓
Context Formatting → LLM → Response
```

#### 3. Data Flow
```
Fight Capture (Browser) → FastAPI /store-transcript
                              ↓
                  Store in PostgreSQL + S3
                              ↓
              Background: Chunk & Embed → Pinecone
                              ↓
         LLM Analysis + Repair Plans → S3 + Pinecone
                              ↓
              Post-Fight UI displays results
                              ↓
          User talks to Luna (RAG-enabled voice)
```

---

##  Project Structure

```
serene/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── luna/              # Modular voice agent
│   │   │   │   ├── __init__.py    # Agent entrypoint
│   │   │   │   ├── agent.py       # SimpleMediator & RAGMediator classes
│   │   │   │   ├── rag.py         # RAG handler logic
│   │   │   │   ├── tools.py       # Agent tools wrapper
│   │   │   │   ├── config.py      # Agent config
│   │   │   │   └── utils.py       # Utilities
│   │   │   └── tools/
│   │   │       └── mediator_tools.py  # LLM function tools
│   │   ├── models/
│   │   │   ├── schemas.py         # Pydantic models
│   │   │   └── migration.sql     # Database schema
│   │   ├── routes/
│   │   │   ├── analytics.py      # Analytics endpoints
│   │   │   ├── calendar.py       # Calendar & cycle tracking
│   │   │   ├── pdf_upload.py     # Profile uploads
│   │   │   ├── post_fight.py     # Analysis & repair plans
│   │   │   ├── realtime_transcription.py
│   │   │   ├── transcription.py
│   │   │   └── user_routes.py
│   │   ├── services/
│   │   │   ├── calendar_service.py    # Cycle tracking logic
│   │   │   ├── db_service.py          # PostgreSQL operations
│   │   │   ├── embeddings_service.py  # Voyage embeddings
│   │   │   ├── llm_service.py         # LLM calls
│   │   │   ├── ocr_service.py         # PDF text extraction
│   │   │   ├── pinecone_service.py    # Vector DB ops
│   │   │   ├── reranker_service.py    # Voyage reranker
│   │   │   ├── s3_service.py          # AWS S3 operations
│   │   │   ├── transcript_chunker.py  # Text chunking
│   │   │   └── transcript_rag.py      # RAG orchestration
│   │   ├── tools/
│   │   │   ├── conflict_analysis.py   # Conflict analyzer
│   │   │   └── repair_coaching.py     # Repair plan generator
│   │   ├── config.py              # Environment config
│   │   └── main.py                # FastAPI app
│   ├── start_agent.py             # Agent startup script
│   ├── requirements.txt
│   └── .env                       # API keys (not in repo)
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── MediatorModal.tsx      # Luna voice interface
│   │   │   ├── RelatedConflicts.tsx   # Past conflicts display
│   │   │   ├── TranscriptBubble.tsx   # Chat message UI
│   │   │   ├── history/               # History page components
│   │   │   ├── navigation/            # Sidebar & Bottom nav
│   │   │   └── ui/                    # Reusable UI components
│   │   ├── pages/
│   │   │   ├── Home.tsx               # Dashboard
│   │   │   ├── FightCapture.tsx       # Audio recording
│   │   │   ├── PostFightSession.tsx   # Analysis & Luna chat
│   │   │   ├── History.tsx            # Conflict timeline
│   │   │   ├── Calendar.tsx           # Cycle tracking
│   │   │   ├── Analytics.tsx          # Health dashboard
│   │   │   └── Upload.tsx             # Profile management
│   │   ├── App.tsx                # Router setup
│   │   ├── index.css              # Global styles
│   │   └── index.tsx              # Entry point
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   └── package.json
│
├── DESCRIPTION.md                 # User guide
├── CHALLENGES.md                  # Technical challenges (upcoming)
└── README.md                      # This file
```

---

##  RAG System Design

### Pinecone Namespaces
1. **`transcript_chunks`** - Chunked conversation transcripts
2. **`profiles`** - Partner personality profiles
3. **`analysis`** - Post-fight analysis summaries
4. **`repair_plans`** - Generated repair strategies

### Metadata Structure
```json
{
  "transcript_chunks": {
    "conflict_id": "uuid",
    "relationship_id": "uuid",
    "chunk_index": 0,
    "speaker": "Partner A / B",
    "text": "chunk content",
    "timestamp": "ISO date"
  },
  "profiles": {
    "relationship_id": "uuid",
    "pdf_type": "boyfriend_profile / girlfriend_profile",
    "extracted_text": "profile content"
  }
}
```

### RAG Retrieval Strategy

**3-Stage Context Assembly:**

1. **Current Conflict Transcript** (Primary)
   - Retrieves chunks from current `conflict_id` only
   - Maintains chronological order via `chunk_index`
   - Full conversation context loaded

2. **Partner Profiles** (Secondary)
   - Semantic search through uploaded PDFs
   - Reranked by relevance to current query
   - Provides personality/background context

3. **Past Conflicts** (Tertiary)
   - Semantic similarity to current topic
   - Calendar-aware (cycle correlation)
   - Pattern recognition across history

**Optimization:**
- Parallel queries for speed
- Reranking to reduce hallucinations
- Timeouts to prevent hanging (3-5s max per query)
- Caching for calendar insights (5-min TTL)

---

##  Setup & Installation

### Prerequisites
- **Python 3.11+**
- **Node.js 18+**
- **PostgreSQL** (via Supabase or local)
- **API Keys:**
  - LiveKit Cloud (API key + secret)
  - Deepgram
  - OpenRouter
  - ElevenLabs
  - Voyage AI
  - Pinecone
  - AWS S3
  - Supabase

### Local Development

**1. Clone & Install**
```bash
git clone <repo-url>
cd serene
```

**2. Environment Configuration**

Create `.env` file in the **root directory** (both backend and frontend will read from this):

```bash
cp .env.example .env
# Edit .env with your API keys
```

The `.env` file should contain:
```env
# LiveKit
LIVEKIT_URL=wss://your-livekit-url.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# AI Services
OPENROUTER_API_KEY=sk-or-xxx
DEEPGRAM_API_KEY=xxx
ELEVENLABS_API_KEY=sk_xxx
VOYAGE_API_KEY=pa-xxx
MISTRAL_API_KEY=xxx

# Databases
DATABASE_URL=postgresql://user:pass@host:5432/dbname
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=xxx
PINECONE_API_KEY=xxx

# AWS S3
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_REGION=us-east-1
S3_BUCKET_NAME=serene-relationship-mediator

# Frontend (VITE_ prefix required for Vite)
VITE_API_URL=http://localhost:8000
VITE_LIVEKIT_URL=wss://your-livekit-url.livekit.cloud
```

**3. Backend Setup**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**4. Run Backend (2 terminals)**

Terminal 1 - API:
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Terminal 2 - Agent:
```bash
cd backend
source venv/bin/activate
python start_agent.py start
```

**5. Frontend Setup**
```bash
cd frontend
npm install
```

**6. Run Frontend**
```bash
cd frontend
npm run dev
```

**Access:**
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs

---

##  Key Features

### 1. **Real-Time Voice Mediation**
- Sub-500ms latency for voice responses
- Speaker diarization (identifies Partner A vs B)
- Interruption handling with graceful recovery
- Contextual awareness from RAG system

### 2. **Intelligent Conflict Analysis**
- Automatic root cause identification
- Sentiment & emotion tracking
- Topic extraction and categorization
- Communication pattern analysis

### 3. **Cycle-Aware Insights**
- Menstrual cycle phase tracking
- Conflict correlation with hormonal phases
- Tension forecasting based on cycle
- Timing recommendations for repairs

### 4. **Personalized Repair Plans**
- Step-by-step apology scripts
- Partner-specific language suggestions
- Timing considerations (cycle-aware)
- Follow-up action items

### 5. **Relationship Analytics**
- Health score (0-100)
- Conflict frequency trends
- Topic analysis (word clouds)
- Resolution rate tracking
- Cycle correlation heatmaps

---

##  Database Schema

**Key Tables:**
- `relationships` - Partner metadata
- `conflicts` - Conflict records
- `profiles` - Uploaded PDFs
- `cycle_events` - Period tracking
- `intimacy_events` - Positive moments
- `memorable_dates` - Special occasions
- `mediator_sessions` - Luna conversations
- `mediator_messages` - Chat history (JSONB)
- `conflict_analysis` - Analysis metadata
- `repair_plans` - Repair plan metadata

*(See `backend/app/models/migration.sql` for full schema)*

---

##  Design Decisions

### Why These Technologies?

| **Choice** | **Rationale** |
|------------|---------------|
| **Voyage-3 Embeddings** | Superior semantic understanding for relationship context vs general embeddings |
| **Voyage-Rerank-2** | Reduces hallucinations by 40% compared to raw vector search |
| **LiveKit Cloud** | Production-ready WebRTC, no infrastructure management |
| **Pinecone Serverless** | Zero-ops vector DB with multi-namespace support |
| **GPT-4o-mini** | Cost-effective ($0.15/1M tokens) with sufficient empathy |
| **ElevenLabs Flash** | Natural emotional voice with 200-300ms latency |
| **PostgreSQL** | ACID compliance for critical relationship data |
| **S3** | Durable storage for transcripts & analysis |

### Key Optimizations (Implemented)

1. **Parallel Retrieval** - Fetch transcript + profiles + calendar simultaneously
2. **Reranking** - Reduce context from 20 chunks → 7 high-relevance chunks
3. **Caching** - Calendar insights cached for 5 minutes
4. **Timeouts** - All RAG queries timeout after 3-5 seconds
5. **Chunking Strategy** - 1000 chars with 200 char overlap for coherence
6. **Background Tasks** - Analysis generation runs async to not block UI

### Future Latency Optimizations

To further reduce voice agent latency (currently ~500ms):

1. **Model Swaps (Speed of Light)**
   - **LLM**: Switch to **Groq** (Llama-3.1-70B) for <100ms Time-to-First-Token
   - **TTS**: Switch to **Cartesia Sonic** for <100ms audio generation

2. **RAG Optimization**
   - **Context Caching**: Pre-load relevant conflict chunks into agent memory at session start (avoids per-turn vector search)
   - **Speculative RAG**: Start generating filler audio ("I see...") immediately while fetching RAG context in background

3. **UX Perception**
   - **Backchanneling**: Emit immediate acknowledgement sounds ("Hmm", "Right") upon VAD silence detection

---

##  Development Commands

```bash
# Backend
cd backend && source venv/bin/activate
uvicorn app.main:app --reload         # API server
python start_agent.py start           # Voice agent

# Frontend
cd frontend
npm run dev                           # Dev server
npm run build                         # Production build
npm run preview                       # Preview build

# Database
# Run migrations via Supabase dashboard
# Or use SQL directly from migration.sql
```

---

##  Deployment

The application is designed for:
- **Frontend**: Vercel / Netlify
- **Backend**: AWS EC2 / Railway / Render
- **Agent**: Same server as backend (separate process)
- **Database**: Supabase (managed PostgreSQL)
- **Storage**: AWS S3
- **Vector DB**: Pinecone (serverless)

*(See deployment docs for production setup)*

---

##  API Endpoints

Key routes:
- `POST /api/conflicts/create` - Create new conflict
- `POST /api/transcription/store-transcript` - Save recording
- `POST /api/post-fight/conflicts/{id}/generate-all` - Generate analysis
- `GET /api/conflicts/{id}` - Get conflict details
- `GET /api/analytics/dashboard` - Analytics data
- `POST /api/calendar/log-event` - Log calendar event
- `POST /api/mediator/token` - Get LiveKit token for Luna

*(Full API docs at /docs when running locally)*

---

## 🤝 Contributing

This is currently a private MVP. For questions or collaboration:
- See `DESCRIPTION.md` for user documentation
- See `CHALLENGES.md` for technical deep-dives

---

## 📄 License

Private project - All rights reserved

---

**Built with ❤ to help couples communicate better through AI-powered mediation**
