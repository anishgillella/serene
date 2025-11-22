# HeartSync – Quick Start for Developers

One-page guide to understand the system and start coding.

---

## 🎯 The 3 Core Modes

### 1. Fight Capture
- Agent silently records both partners arguing
- Real-time STT → speaker diarization → transcript storage
- No agent response; just listening

### 2. Post-Fight Session
- Partner enters voice conversation with agent
- Agent can analyze, coach, or just listen (rant)
- Tools used: analyze conflict, generate repair plans, log events
- Rants stored private to speaker

### 3. Analytics
- Dashboard shows conflict trends, intimacy frequency, cycles
- User can request weekly summary via voice
- All metrics on-demand (never auto-pushed)

---

## 🔧 Core Tools (7 Total)

Agent calls these mid-conversation:

1. **analyze_conflict_transcript** — Extract root causes, triggers, escalation
2. **generate_repair_plan** — Personalized apology + repair steps
3. **update_relationship_metrics** — Compute fight frequency, trends
4. **weekly_summary** — Generate weekly insights
5. **simulate_partner_reaction** — Test message, get risk score
6. **log_cycle_event** — Record period/ovulation data
7. **log_intimacy_event** — Record intimacy events

---

## 🗄️ Data Model (5-Min Overview)

```
relationships
  ├─ partners A & B (profiles)
  ├─ conflicts (transcripts, metadata)
  ├─ rants (private per partner)
  ├─ cycle_events (period, ovulation)
  ├─ intimacy_events (timestamps)
  └─ pdfs (handbooks, notes)

Chroma (Vector Store):
  ├─ handbook_docs
  ├─ conflict_docs
  ├─ partner_profile_docs
  └─ notes_docs
```

---

## 🔐 Privacy Rules (Important!)

| Data | Who Sees | Automatic? |
|------|----------|-----------|
| Fight transcript | Both partners | Shared |
| Individual rant | Only speaker | Private |
| PDFs/handbook | Both partners | Shared |
| Cycle data | Only owner | Private |
| Metrics | Both partners | Aggregate |
| Historical conflicts | Only if asked | Opt-in |

**Key:** RAG retrieval is **opt-in only**. Agent never auto-injects history/PDFs.

---

## 🛠️ Tech Stack (Quick Reference)

**Speech-to-Text:** Deepgram (real-time, speaker diarization, emotional tone)  
**Text-to-Speech:** ElevenLabs (natural, emotional voices, low latency)  
**Embeddings:** Voyage-3 (RAG-optimized semantic search)  
**Reranking:** Voyage-Rerank-2 (improves retrieval quality, reduces hallucination)  
**LLM:** OpenAI GPT-4 (relationship coaching, emotional nuance)  
**Backend:** FastAPI + LiveKit Agents + LangChain + Chroma  
**Database:** PostgreSQL + S3  
**Frontend:** React + Vite + TailwindCSS  

**See [FRAMEWORK_AND_TOOLS.md](FRAMEWORK_AND_TOOLS.md) for complete setup details.**

---

## 📋 API Endpoints

```
POST /api/token → Get LiveKit token
GET /api/conflicts/{conflict_id} → Get transcript
POST /api/conflicts/{conflict_id}/rant → Store rant
POST /api/pdfs/upload → Upload PDF
GET /api/analytics/{relationship_id} → Fetch metrics
POST /api/events/cycle → Log cycle event
POST /api/events/intimacy → Log intimacy event
```

---

## 🏗️ Project Structure

```
backend/
  ├─ app/main.py                # FastAPI routes
  ├─ agents/heartsync_agent.py  # LiveKit integration
  ├─ tools/                     # 7 core tools
  ├─ rag/                       # PDF OCR + retrieval
  ├─ models/                    # Pydantic schemas
  └─ services/                  # Business logic

frontend/
  ├─ components/
  │   ├─ FightCaptureView.tsx
  │   ├─ PostFightSession.tsx
  │   └─ AnalyticsDashboard.tsx
  ├─ livekit/                   # LiveKit setup
  └─ api/                       # Backend calls
```

---

## 🚀 Local Setup (5 Min)

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export LIVEKIT_URL="wss://..."
export OPENAI_API_KEY="sk-..."
python -m uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`

---

## 🎮 Frontend State

```typescript
interface AppState {
  userId: string
  relationshipId: string
  mode: "idle" | "fight_capture" | "post_fight" | "analytics"
  roomActive: boolean
  currentConflict: Conflict | null
  rants: Rant[]
}
```

---

## 🔍 Key Code Locations

| Task | File |
|------|------|
| Add a tool | `app/tools/{domain}.py` |
| Add RAG collection | `app/rag/ingest.py` |
| Add API endpoint | `app/main.py` |
| Add component | `src/components/{name}.tsx` |
| Update schema | `app/models/schemas.py` |

---

## 📊 Database (Quick)

```sql
-- Core tables
relationships(id, partner_a_id, partner_b_id)
conflicts(id, relationship_id, transcript, vector_ref)
rants(id, partner_id, conflict_id, is_shared)
cycle_events(id, partner_id, type, timestamp)
intimacy_events(id, relationship_id, timestamp)
pdfs(id, relationship_id, name, type, vector_ref)
```

---

## ⚡ Common Tasks

### Record a Fight
1. Both join LiveKit room
2. Agent listens silently
3. User clicks "End Conflict"
4. Transcript stored

### Get Repair Plan
1. Partner enters post-fight mode
2. Says: "Help me repair this"
3. Agent calls `generate_repair_plan`
4. Personalized apology script returned

### Query PDFs
1. User uploads handbook
2. During post-fight: "What does the handbook say about yelling?"
3. Agent queries `handbook_docs` via RAG
4. Relevant excerpts returned

### View Analytics
1. Navigate to Analytics page
2. See charts (conflicts/week, intimacy/week)
3. Ask: "Weekly summary"
4. Agent calls `weekly_summary` tool

---

## 🐛 Debugging Tips

| Issue | Check |
|-------|-------|
| STT not working | Mic permissions, LiveKit connection |
| RAG not retrieving | PDF OCR status, Chroma collection exists |
| Agent not responding | LLM API key, tool definitions, room connection |
| Privacy issue | `partner_id` checks, RAG access control |

---

## ✅ MVP Success Criteria

- ✅ Two partners capture a fight silently
- ✅ Post-fight session allows reflection
- ✅ Repair plans are personalized
- ✅ Analytics show trends
- ✅ PDFs uploadable and queryable
- ✅ All rants are private
- ✅ No critical bugs

---

## 📚 Full Documentation

- **SYSTEM_DESIGN.md** — Complete architecture
- **DEVELOPMENT_ROADMAP.md** — Phase breakdown
- **README.md** (root) — Project overview

---

## 🎓 Development Order

**Day 1:** Phase 0 (LiveKit setup)  
**Days 2-3:** Phase 1 (Fight capture)  
**Days 4-5:** Phase 2 (Post-fight)  
**Days 6-8:** Phase 3 (RAG)  
**Days 9-10:** Phase 4 (Tools)  
**Days 11+:** Phases 5-8  

---

**Questions?** See [../../docs/SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) or [../../README.md](../README.md)

