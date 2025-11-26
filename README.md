# Luna – RAG-Enabled Voice Mediator Agent

A voice-based AI mediator that helps couples navigate conflicts through empathetic conversations, real-time transcription, and RAG-enabled insights from conversation history and partner profiles.

---

## Overview

**Luna** is an AI mediator for Adrian and Elara that:
- Takes Adrian's perspective while helping him understand Elara's viewpoint
- Uses real-time speech-to-text with speaker diarization
- Retrieves context from conversation history and partner profiles via RAG
- Provides empathetic, contextualized responses through voice

**Key Features:**
- ✅ **Real-time Voice Mediation**: Dual speaker identification with < 500ms latency.
- ✅ **Cycle-Aware Context**: Calendar integration that informs Luna about cycle phases and emotional context.
- ✅ **Relationship Intelligence**: Graph database (Neo4j) tracks recurring themes and conflict sagas.
- ✅ **Conflict Analytics**: Dashboard showing conflict frequency, intensity trends, and resolution rates.
- ✅ **Smart RAG**: 3-stage retrieval (Summary → Graph → Transcript) for optimal context.
- ✅ **Post-Fight Reflection**: Guided repair plans and retrospective analysis.

---

## System Architecture

```
User (Browser) → React Frontend → LiveKit Cloud → Python Agent → RAG + Graph + LLM → TTS Response
```

**Components:**
- **Frontend**: React 18 + Vite (real-time transcription, analysis, graph visualization)
- **Backend**: FastAPI (token generation, transcript storage, analysis endpoints)
- **Agent**: LiveKit voice agent with Deepgram STT → OpenRouter LLM → ElevenLabs TTS
- **RAG**: Pinecone vector DB + Voyage-3 embeddings + Voyage-Rerank-2
- **Graph Brain**: Neo4j (tracks relationships between conflicts and recurring topics)
- **Storage**: PostgreSQL (metadata) + S3 (documents) + Pinecone (vectors) + Neo4j (graph)

---

## RAG Strategy (Critical Design)

**Three-Stage Context Retrieval:**

1. **SUMMARY CONTEXT** (Optimization - Phase 1)
   - Checks if `conflict_analysis` exists for the current session.
   - If yes, loads the 300-token summary instead of the 5000-token transcript.
   - **Benefit**: 94% token reduction + faster startup.

2. **GRAPH CONTEXT** (Relationship Intelligence - Phase 2)
   - Queries Neo4j for "Related Conflicts".
   - Finds "Sagas" (direct continuations) and "Recurring Themes" (shared topics).
   - **Benefit**: Luna knows *"This is the 3rd time you fought about Money"*.

3. **TRANSCRIPT RAG** (Fallback/Deep Dive)
   - If no summary exists, fetches full transcript chunks from Pinecone.
   - Used when user asks specific questions about "what was said".

---

## Graph Memory (Neo4j)

To solve the "Kitchen Sink" problem (fights about everything) and "Sagas" (multi-day fights), we use a Graph Database.

- **Nodes**: `Conflict`, `Topic`, `Person`
- **Edges**: `(:Conflict)-[:ABOUT]->(:Topic)`, `(:Conflict)-[:EVOLVED_FROM]->(:Conflict)`
- **Visualization**: Frontend shows a timeline of related conflicts and badges for recurring themes.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Voice** | LiveKit (Cloud) + Deepgram nova-3 (STT) |
| **LLM** | GPT-4o-mini via OpenRouter |
| **TTS** | ElevenLabs eleven_flash_v2_5 (voice: ODq5zmih8GrVes37Dizd) |
| **Embeddings** | Voyage-3 (1024 dimensions) |
| **Reranking** | Voyage-Rerank-2 |
| **Vector DB** | Pinecone (4 namespaces: transcripts, profiles, analysis, repair_plans) |
| **Graph DB** | Neo4j Community (Docker) |
| **Backend** | FastAPI + PostgreSQL + S3 |
| **Frontend** | React 18 + Vite + TailwindCSS |
| **Chunking** | LangChain RecursiveCharacterTextSplitter (1000 chars, 200 overlap) |

---

## Setup

### Prerequisites
- Python 3.9+, Node.js 16+
- Docker (for Neo4j)
- PostgreSQL database
- API Keys: LiveKit, Deepgram, OpenRouter, ElevenLabs, Voyage AI, Pinecone, AWS S3

### Local Development

**1. Infrastructure:**
```bash
docker-compose up -d  # Starts Neo4j
```

**2. Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env with API keys (see config.py)
python -m uvicorn app.main:app --reload
```

**3. Agent (separate terminal):**
```bash
cd backend
source venv/bin/activate
python start_agent.py
```

**4. Frontend (separate terminal):**
```bash
cd frontend
npm install
npm run dev
```

**Access:**
- Frontend: http://localhost:5175
- API: http://localhost:8000
- Neo4j Browser: http://localhost:7474 (user: neo4j, pass: password)

---

## Design Decisions

### Why Graph Database (Neo4j)?
- **Problem**: Vector search is bad at structural queries like "How did our money fights evolve?".
- **Solution**: Neo4j explicitly links conflicts by Topic and Saga.
- **Benefit**: Luna can track the *story* of the relationship, not just isolated events.

### Why Summary-First?
- **Problem**: Loading full transcripts (5k+ tokens) is slow and expensive.
- **Solution**: Use the generated analysis summary (300 tokens) as primary context.
- **Benefit**: Faster response times and better focus on core issues.

### Why These Technologies?
| Choice | Rationale |
|--------|-----------|
| **Voyage-3** | Best semantic search for relationship context vs general embeddings |
| **Voyage-Rerank-2** | Reduces hallucinations by filtering irrelevant secondary chunks |
| **LiveKit Cloud** | Managed infrastructure, no self-hosting complexity |
| **Pinecone** | Serverless, multiple namespaces, no maintenance |
| **GPT-4o-mini** | Cost-effective, fast, sufficient for empathetic responses |
| **ElevenLabs** | Natural emotional voice quality + low latency |

### Limitations
- **No explicit tool calling**: Analysis/repair accessed via API endpoints, not voice commands (future enhancement)
- **Chapter-level queries**: PDFs chunked by size, not structure (future enhancement)
- **Single relationship**: MVP hardcoded for one relationship (future: multi-tenant)

---

## Key Files

- `backend/app/services/neo4j_service.py` - Graph operations
- `backend/app/services/transcript_rag.py` - Vector RAG logic
- `backend/app/agents/mediator_agent.py` - Voice agent with Graph+Summary context
- `backend/app/routes/post_fight.py` - Analysis generation & Graph ingestion
- `backend/app/routes/analytics.py` - Analytics data endpoints
- `frontend/src/pages/PostFightSession.tsx` - Analysis/repair display
- `frontend/src/pages/Calendar.tsx` - Cycle tracking & event management
- `frontend/src/pages/Analytics.tsx` - Conflict trends dashboard
- `frontend/src/components/RelatedConflicts.tsx` - Graph visualization UI

---

## Example Flow

**User asks:** "Why did Elara say she would come but didn't?"

**Luna retrieves:**
- **Primary**: All transcript chunks from current conflict in order
- **Secondary**: 
  - Elara's profile: "tends to give casual responses without firm commitments"
  - Past conflict: "Adrian: I thought you said you'd come"

**Luna responds:** "I understand you're coming from a sports background and passionate about football, so it hurt when Elara didn't attend the game even though she said 'sure'. Based on her profile, she tends to give casual responses without firm commitments, which might explain the miscommunication."

---

## Future Enhancements

1. Voice-triggered conflict analysis ("Luna, analyze this conflict")
2. Chapter-level PDF queries with metadata preservation
3. Multi-tenant support for multiple relationships
4. Advanced pattern detection across conflicts (using Graph Data Science)
5. Partner-specific voice cloning for TTS

---

**Built for couples building understanding through conflict.**
