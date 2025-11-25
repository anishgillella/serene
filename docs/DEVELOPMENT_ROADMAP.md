# HeartSync – Development Roadmap

8-phase incremental development plan to MVP (18-32 days).

---

## Phase 0 — Project Setup (1–2 days)

**Goals:** Prepare environment, init skeletons, connect LiveKit end-to-end

**Deliverables:**
- Backend (FastAPI) + Frontend (React) boilerplate
- Token generation endpoint
- Agent that connects to LiveKit and speaks "Hello world"

---

## Phase 1 — Fight Capture (2–4 days)

**Goals:** Silent recording, real-time transcription, speaker diarization

**Deliverables:**
- Full-fight transcript stored in database with speaker attribution
- Conflict entry with metadata
- Minimal UI for fight capture

---

## Phase 2 — Post-Fight Session (2–3 days)

**Goals:** Voice interaction, private rants, basic analysis

**Deliverables:**
- End-to-end: fight → post-fight → summary
- Rants stored privately per partner
- Agent can speak analysis via TTS

---

## Phase 3 — RAG Foundation (3–5 days)

**Goals:** PDF uploading, OCR, vector indexing, on-demand queries

**Deliverables:**
- PDF → OCR → Chroma pipeline working
- Voice queries hitting PDFs
- Handbook, notes, psychoeducation collections

---

## Phase 4 — Conflict Analysis Tools (2–4 days)

**Goals:** Implement 7 core tools, AI-powered analysis

**Deliverables:**
- `analyze_conflict_transcript` — root causes, triggers, escalation
- `generate_repair_plan` — personalized apologies, repair steps
- Natural, contextual agent responses

---

## Phase 5 — Manual Tracking (1–2 days)

**Goals:** Cycle & intimacy logging via UI

**Deliverables:**
- Calendar UI for data entry
- Database storage for events
- Data available for metrics

---

## Phase 6 — Analytics Dashboard (3–5 days)

**Goals:** Visualize trends, generate summaries

**Deliverables:**
- Charts: conflict frequency, intimacy trends, optional cycle correlation
- Weekly summary tool
- Voice-triggered analytics queries

---

## Phase 7 — Advanced Interactions (2–4 days)

**Goals:** Simulations, patterns, growth suggestions

**Deliverables:**
- `simulate_partner_reaction` tool
- Pattern recognition across fights
- Personal growth suggestions

---

## Phase 8 — Polish & Deployment (2–3 days)

**Goals:** UI theme, error handling, production readiness

**Deliverables:**
- Cozy, soft pastel UI
- Graceful error handling
- AWS deployment setup
- Final documentation

---

## Stretch Phase — Live Mediation (2–5 days)

**Goals:** Real-time intervention during fights

**Deliverables:**
- Wake phrase detection
- De-escalation coaching mid-fight

---

## Timeline Summary

| Phase | Duration | Cumulative |
|-------|----------|-----------|
| 0 | 1–2d | 1–2d |
| 1 | 2–4d | 3–6d |
| 2 | 2–3d | 5–9d |
| 3 | 3–5d | 8–14d |
| 4 | 2–4d | 10–18d |
| 5 | 1–2d | 11–20d |
| 6 | 3–5d | 14–25d |
| 7 | 2–4d | 16–29d |
| 8 | 2–3d | 18–32d |

**MVP Ready:** 18–32 days

---

## Development Best Practices

### Testing
- Unit test all tool functions
- Integration test capture → storage → retrieval
- E2E test with two browser tabs
- Test privacy (A can't see B's rant)

### Code Quality
- Use type hints (Pydantic models)
- Add inline comments for complex logic
- Keep functions focused and reusable
- Create components that compose

### Git Workflow
- Feature branches per phase
- Frequent, descriptive commits
- Keep main deployable

### Documentation
- Update README after each phase
- Document new tools as added
- Keep architecture in sync
- Add code comments

---

## Pre-Launch Checklist

- [ ] Fight capture end-to-end working
- [ ] Post-fight rants private and retrievable
- [ ] Repair plans personalized
- [ ] Analytics dashboard shows trends
- [ ] PDFs uploadable and queryable
- [ ] No console errors
- [ ] Database properly schemed
- [ ] README complete
- [ ] Code organized and commented
- [ ] Git history clean

---

## Risk Mitigation

| Issue | Risk | Mitigation |
|-------|------|-----------|
| LiveKit delays | High | Mock audio in Phase 0 |
| OCR accuracy | Medium | Test Mistral early Phase 3 |
| Vector search perf | Medium | Paginate and filter |
| TTS latency | Medium | Cache responses, test early |
| DB scaling | Low (MVP) | Index key columns |

---

## Deliverables by Phase

**Phase 0:** Hello world agent  
**Phase 1:** Recorded fight transcript  
**Phase 2:** Private rants + summaries  
**Phase 3:** PDF queries via voice  
**Phase 4:** Repair plans + analysis  
**Phase 5:** Calendar UI working  
**Phase 6:** Analytics charts + trends  
**Phase 7:** Simulations + patterns  
**Phase 8:** Production MVP ready









