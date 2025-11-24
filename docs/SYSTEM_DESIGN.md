# HeartSync – System Design & Architecture

Complete technical specification for HeartSync implementation.

---

## 1. System Overview

**HeartSync** is a voice-enabled, RAG-powered relationship mediator that captures fights, analyzes conflicts, and coaches couples through repair.

**Core Stack:** Python FastAPI + LiveKit Agents + LangChain + Chroma + PostgreSQL

---

## 2. User Flows

### Fight Capture Flow

```
1. User clicks "Start Fight Capture" → joins LiveKit room
2. Partner joins from separate device
3. Agent auto-joins in silent record mode
4. Both partners argue; agent transcribes with speaker diarization
5. One partner clicks "End Conflict Capture"
6. Transcript stored, ready for post-fight analysis
```

### Post-Fight Session Flow

```
1. Partner enters "Post-Fight Session" mode
2. Selects mode (Rant, Summary, Repair, Patterns)
3. Agent responds via voice + optional text
4. Rant/debrief stored (private to speaker)
5. Session ends
```

### Analytics Flow

```
1. User navigates to Analytics dashboard
2. Views charts: conflicts/week, intimacy trends, optional cycle correlation
3. Can request voice-based weekly summary
4. Agent provides insights and recommendations
```

---

## 3. Data Model

### Core Tables

```sql
relationships(id, partner_a_id, partner_b_id, created_at)
partners(id, relationship_id, profile_json)
conflicts(id, relationship_id, start_time, end_time, transcript_raw, vector_ref)
rants(id, partner_id, conflict_id, content, is_shared, created_at)
cycle_events(id, partner_id, type, timestamp, notes)
intimacy_events(id, relationship_id, timestamp, initiator_partner_id)
pdfs(id, relationship_id, name, type, ocr_status, vector_ref)
```

### Vector Collections (Chroma)

Per relationship:
- `handbook_docs` — Relationship guidelines
- `conflict_docs` — Past fight transcripts
- `psychoeducation_docs` — Educational materials
- `notes_docs` — Custom notes
- `partnerA_profile_docs` — Partner preferences
- `partnerB_profile_docs` — Partner preferences

---

## 4. RAG Retrieval Strategy

### Default Behavior
- Uses **only current conflict transcript** unless explicitly asked
- Agent does NOT auto-inject history or profiles

### On-Demand Historical Access
- User asks: "Compare this to last week's fight" → queries `conflict_docs`
- User asks: "What does the handbook say about yelling?" → queries `handbook_docs`
- User asks: "What are her triggers?" → queries partner profiles

**Principle:** All historical RAG usage is **opt-in via user query**.

---

## 5. Privacy Model

| Data | Visibility | Rules |
|------|-----------|-------|
| Fight transcripts | Shared | Both partners |
| Individual rants | Private | Only speaker (unless marked shareable) |
| PDFs/Handbook | Shared | Both partners |
| Cycle data | Private | Only owner |
| Intimacy events | Shared | Both (aggregate metrics only) |

**Key Rules:**
- Rants are private by default
- Agent NEVER auto-reference one partner's rant to the other
- Sharing only with explicit permission

---

## 6. Tool Specifications

### 6.1 `analyze_conflict_transcript`
```python
Inputs:
  - conflict_id: str
  - partner_id: str (optional)

Outputs:
  - root_causes: List[str]
  - escalation_points: List[{timestamp, reason}]
  - unmet_needs_A: List[str]
  - unmet_needs_B: List[str]
  - communication_breakdowns: List[str]
```

### 6.2 `generate_repair_plan`
```python
Inputs:
  - conflict_id: str
  - partner_requesting_id: str

Outputs:
  - steps: List[str]
  - apology_script: str
  - timing_suggestion: str
  - risk_factors: List[str]
```

### 6.3 `update_relationship_metrics`
```python
Inputs:
  - conflict_id: str

Outputs:
  - fight_count_30d: int
  - avg_duration: float
  - intimacy_count_30d: int
  - last_conflict_date: date
```

### 6.4 `weekly_summary`
```python
Inputs:
  - relationship_id: str

Outputs:
  - summary_text: str
  - fight_count: int
  - trends: str
  - recommendations: List[str]
```

### 6.5 `simulate_partner_reaction`
```python
Inputs:
  - relationship_id: str
  - target_partner_id: str
  - proposed_message: str

Outputs:
  - likely_reaction: str
  - risk_score: 0.0-1.0
  - suggested_rephrase: str
```

### 6.6 `log_cycle_event`
```python
Inputs:
  - partner_id: str
  - event_type: "period_start" | "note"
  - timestamp: datetime (optional)
  - notes: str (optional)

Outputs:
  - status: "ok" | "error"
```

### 6.7 `log_intimacy_event`
```python
Inputs:
  - relationship_id: str
  - timestamp: datetime (optional)
  - initiator_partner_id: str (optional)

Outputs:
  - status: "ok" | "error"
  - intimacy_count_30d: int
```

---

## 7. Project Structure

### Backend

```bash
backend/
  ├─ app/
  │   ├─ main.py                 # FastAPI app & routes
  │   ├─ config.py               # Environment & settings
  │   ├─ agents/
  │   │   └─ heartsync_agent.py  # LiveKit Agents integration
  │   ├─ rag/
  │   │   ├─ ocr_mistral.py      # PDF OCR extraction
  │   │   ├─ ingest.py           # Chunking & indexing
  │   │   └─ retriever.py        # RAG retrieval interface
  │   ├─ tools/
  │   │   ├─ conflict_analysis.py
  │   │   ├─ metrics.py
  │   │   ├─ simulation.py
  │   │   └─ events.py
  │   ├─ models/
  │   │   ├─ schemas.py          # Pydantic models
  │   │   └─ db.py               # Database helpers
  │   └─ services/
  │       ├─ stt_tts.py
  │       ├─ conflicts.py
  │       └─ analytics.py
  ├─ requirements.txt
  └─ README.md
```

### Frontend

```bash
frontend/
  ├─ src/
  │   ├─ App.tsx
  │   ├─ components/
  │   │   ├─ FightCaptureView.tsx
  │   │   ├─ PostFightSession.tsx
  │   │   ├─ AnalyticsDashboard.tsx
  │   │   └─ PdfManager.tsx
  │   ├─ livekit/
  │   │   ├─ client.ts
  │   │   └─ hooks.ts
  │   ├─ api/
  │   │   ├─ token.ts
  │   │   ├─ analytics.ts
  │   │   └─ pdf.ts
  │   ├─ styles/theme.css
  │   └─ types/index.ts
  ├─ package.json
  └─ README.md
```

---

## 8. API Endpoints

```
POST /api/token
  → Get LiveKit token for room join

GET /api/conflicts/{conflict_id}
  → Retrieve conflict transcript and metadata

POST /api/conflicts/{conflict_id}/rant
  → Store private rant

POST /api/pdfs/upload
  → Upload and OCR a PDF

GET /api/analytics/{relationship_id}
  → Fetch metrics (fights, intimacy, cycles)

POST /api/events/cycle
  → Log cycle event

POST /api/events/intimacy
  → Log intimacy event
```

---

## 9. Tech Stack

### Backend
- Python 3.9+ + FastAPI
- LiveKit Agents (real-time voice)
- OpenAI GPT-4 / GPT-4o-mini (LLM)
- OpenAI Whisper (STT)
- OpenAI TTS
- LangChain + Chroma (RAG)
- Mistral Vision (PDF OCR)
- PostgreSQL (metadata)
- S3 (PDF storage)

### Frontend
- React + Vite
- LiveKit Client library
- TailwindCSS
- React Context (state)

### Deployment
- Backend: AWS EC2 or ECS Fargate
- Frontend: S3 + CloudFront
- Vector Store: Chroma (local)
- LiveKit: LiveKit Cloud

---

## 10. Architecture Decisions

### Real-Time Transcript Handling
- Transcripts embedded during fights (acceptable lag)
- Stored for on-demand retrieval after conflict ends

### Rant Privacy
- Private by default; not auto-referenced to other partner
- Sharing requires explicit permission

### Fight Ending Signal
- UI button ("End Conflict Capture") not voice command
- Simpler & clearer state transition

### RAG Opt-In Strategy
- Default: current transcript only
- Historical data/PDFs queried only when explicitly requested
- Maintains trust and transparency

---

## 11. Success Metrics

**Technical:**
- Transcription accuracy: WER < 15%
- Real-time latency: < 2 seconds
- RAG retrieval quality: relevant docs in top-3
- Tool call success rate: > 95%

**User-Facing:**
- Fights captured per week
- Post-fight engagement rate (% → debrief)
- Repair plan follow-through
- User satisfaction with insights

---

## 12. Testing Strategy

**Unit Tests:** Tool functions, RAG logic, privacy checks  
**Integration Tests:** Capture → storage, RAG retrieval, tool calls  
**E2E Tests:** Two-browser simulation, full fight → post-fight → analytics flow  
**Manual Tests:** Sample fights, rant privacy, PDF queries, error handling

---

## 13. Known Limitations (MVP)

- Single couple per backend (no multi-tenant)
- Manual tracking only (no wearables)
- Audio-only (no video)
- No live mediation (agent stays silent)
- No real-time alerts

---

## 14. Future Enhancements

- Real-time intervention / live mediation
- Multi-tenant support
- Google Calendar integration
- Wearable data integration
- Video support
- ML-based conflict prediction
- Therapist dashboard
- Mobile app







