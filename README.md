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
- ✅ Real-time voice conversations with dual speaker identification
- ✅ RAG system that fetches current conflict as PRIMARY context, profiles/past conflicts as secondary
- ✅ Conflict analysis and repair plan generation
- ✅ Post-fight session reflection with Luna
- ✅ PDF upload for partner profiles

---

## System Architecture

```
User (Browser) → React Frontend → LiveKit Cloud → Python Agent → RAG + LLM → TTS Response
```

**Components:**
- **Frontend**: React 18 + Vite (real-time transcription display, analysis/repair views)
- **Backend**: FastAPI (token generation, transcript storage, analysis endpoints)
- **Agent**: LiveKit voice agent with Deepgram STT → OpenRouter LLM → ElevenLabs TTS
- **RAG**: Pinecone vector DB + Voyage-3 embeddings + Voyage-Rerank-2
- **Storage**: PostgreSQL (metadata) + S3 (documents) + Pinecone (vectors)

---

## RAG Strategy (Critical Design)

**Two-Stage Context Retrieval:**

1. **PRIMARY CONTEXT** (Always Included)
   - ALL chunks from current conflict (via Pinecone filter)
   - Maintained in conversation order
   - NOT reranked (preserves full context)
   - Result: User asking "summarize this" gets ONLY current conversation

2. **SECONDARY CONTEXT** (Supplementary)
   - Profiles: Top-3 relevant profile chunks
   - Past conflicts: Top-5 relevant chunks from other conversations
   - Reranked to top-7 most relevant
   - Result: Luna can reference related patterns but won't confuse conversations

**RAG Flow:**
1. Generate query embedding (Voyage-3) → ~100ms
2. Fetch current conflict chunks (Pinecone filter) → ~150ms
3. Fetch profiles + past conflicts (parallel queries) → ~200ms
4. Rerank secondary context (Voyage-Rerank-2) → ~100ms
5. Format & inject into LLM → LLM response → TTS
6. **Total latency: ~1.2-2.2s per turn**

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
| **Backend** | FastAPI + PostgreSQL + S3 |
| **Frontend** | React 18 + Vite + TailwindCSS |
| **Chunking** | LangChain RecursiveCharacterTextSplitter (1000 chars, 200 overlap) |

---

## Setup

### Prerequisites
- Python 3.9+, Node.js 16+
- PostgreSQL database
- API Keys: LiveKit, Deepgram, OpenRouter, ElevenLabs, Voyage AI, Pinecone, AWS S3

### Local Development

**1. Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env with API keys:
# LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET
# DEEPGRAM_API_KEY, OPENROUTER_API_KEY, ELEVENLABS_API_KEY
# VOYAGE_API_KEY, PINECONE_API_KEY
# AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
# DATABASE_URL, SUPABASE_URL, SUPABASE_KEY

python -m uvicorn app.main:app --reload
```

**2. Agent (separate terminal):**
```bash
cd backend
source venv/bin/activate
python start_agent.py
```

**3. Frontend (separate terminal):**
```bash
cd frontend
npm install
npm run dev
```

**Access:**
- Frontend: http://localhost:5175
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

---

## Design Decisions

### Why Two-Stage RAG?
- **Problem**: If we query entire corpus and rerank, other conflicts can overshadow current one
- **Solution**: Always fetch ENTIRE current conflict (no reranking), then supplementary context separately
- **Benefit**: Users always get accurate summary of "this" conversation without mixing conflicts

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

- `backend/app/services/transcript_rag.py` - RAG lookup logic (primary + secondary)
- `backend/app/agents/mediator_agent.py` - Voice agent with context fetching
- `backend/app/routes/post_fight.py` - Analysis & repair plan generation
- `frontend/src/pages/PostFightSession.tsx` - Analysis/repair display

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
4. Advanced pattern detection across conflicts
5. Partner-specific voice cloning for TTS

---

**Built for couples building understanding through conflict.**
