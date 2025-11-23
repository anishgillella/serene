# HeartSync AI Agents Guide

This document provides instructions for AI coding assistants (like Claude, Cursor, or other MCP-enabled tools) to work effectively with the HeartSync project.

---

## Quick Reference

**Project:** HeartSync - Voice-based Relationship Mediator  
**Stack:** Python (FastAPI) + React (Vite) + LiveKit + LangChain + Chroma  
**Tech Choices:** Deepgram (STT) + ElevenLabs (TTS) + Voyage-3 (Embeddings) + Voyage-Rerank-2  

---

## Documentation Structure

All HeartSync documentation is organized in the `docs/` folder:

### Core Documentation

1. **docs/README.md** - Documentation index and navigation guide
2. **docs/QUICK_START.md** - 5-minute developer reference (start here!)
3. **docs/SYSTEM_DESIGN.md** - Complete technical architecture
4. **docs/FRAMEWORK_AND_TOOLS.md** - All frameworks, libraries, and setup instructions
5. **docs/DEVELOPMENT_ROADMAP.md** - 8-phase development plan (18-32 days)
6. **docs/FRONTEND_DESIGN.md** - Frontend UI/UX design specifications
7. **docs/FRONTEND_COMPONENTS.md** - Reusable React component library with code

### Project Files

- **README.md** - High-level project overview
- **Problem.md** - Original problem statement
- **AGENTS.md** - This file
- **frontend/** - React application
- **backend/** - FastAPI backend
- **docs/** - All documentation

---

## Before You Start

Always consult the documentation in this order:

1. **For quick context:** Read `docs/README.md` (2 min)
2. **For implementation:** Read `docs/QUICK_START.md` (5 min)
3. **For deep understanding:** Read relevant `docs/*.md` files (15-30 min)
4. **For code examples:** Check `docs/FRAMEWORK_AND_TOOLS.md` or `docs/FRONTEND_COMPONENTS.md`

---

## Key Concepts

### The 3 Core Modes

1. **Fight Capture** - Silent recording of conflicts
   - Real-time STT via Deepgram
   - Speaker diarization
   - Transcript storage
   - No agent response

2. **Post-Fight Session** - Interactive voice reflection
   - Rant Mode (private venting)
   - Debrief Mode (guided reflection)
   - Repair Coaching (apology scripts)
   - Pattern Analysis (insights)

3. **Analytics** - Relationship trends & metrics
   - Conflict frequency charts
   - Intimacy trends
   - Cycle correlations
   - AI-generated summaries

### Privacy Model (IMPORTANT!)

- **Rants:** Private by default, only speaker can access
- **Transcripts:** Shared between partners
- **Analytics:** Shared, aggregate metrics only
- **RAG Retrieval:** Opt-in only (never automatic)

**Agent must always respect:** Private data access controls, encryption at rest, no auto-injection of historical data

---

## Tech Stack Details

### Backend

- **Framework:** FastAPI + LiveKit Agents
- **LLM:** OpenAI GPT-4 (for coaching & analysis)
- **STT:** Deepgram Nova-2 (real-time, speaker diarization)
- **TTS:** ElevenLabs (natural, emotional voices)
- **RAG:** LangChain + Chroma (Voyage-3 embeddings, Voyage-Rerank-2)
- **Database:** PostgreSQL (metadata) + S3 (PDFs)
- **Voice:** LiveKit Cloud (managed infrastructure)

### Frontend

- **Framework:** React 18 + Vite (fast dev server)
- **Styling:** TailwindCSS (cozy pink/blue theme)
- **State:** React Context (simple global state)
- **Components:** Custom reusable component library
- **Voice Client:** LiveKit Client library

---

## Common Development Tasks

### Setting Up

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export DEEPGRAM_API_KEY="..."
export ELEVENLABS_API_KEY="..."
export VOYAGE_API_KEY="..."
python -m uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
# Visit http://localhost:5175
```

### Adding a New Tool

1. Create function in `backend/app/tools/{domain}.py`
2. Add Pydantic schema in `backend/app/models/schemas.py`
3. Register in `backend/app/agents/heartsync_agent.py`
4. Document in `docs/SYSTEM_DESIGN.md` section 6

### Creating a Frontend View

1. Create component in `frontend/src/views/{ViewName}.tsx`
2. Use components from `docs/FRONTEND_COMPONENTS.md`
3. Follow color palette from `docs/FRONTEND_DESIGN.md`
4. Update navigation in `frontend/src/App.tsx`
5. Test at `http://localhost:5175`

### Implementing RAG Retrieval

1. Upload PDFs via `backend/app/main.py` POST `/api/pdfs/upload`
2. OCR via Mistral in `backend/app/rag/ocr_mistral.py`
3. Embed with Voyage-3 in `backend/app/rag/embeddings.py`
4. Rerank with Voyage-Rerank-2 in `backend/app/rag/reranking.py`
5. Query via LangChain in `backend/app/rag/retriever.py`

---

## API Reference

### Core Endpoints

```
POST /api/token                           # Get LiveKit token
GET /api/conflicts/{conflict_id}          # Get conflict transcript
POST /api/conflicts/{conflict_id}/rant    # Store private rant
POST /api/pdfs/upload                     # Upload PDF
GET /api/analytics/{relationship_id}      # Fetch metrics
POST /api/events/cycle                    # Log cycle event
POST /api/events/intimacy                 # Log intimacy event
```

### Tool Functions (Backend)

1. `analyze_conflict_transcript(conflict_id, partner_id?)` → root causes, triggers, escalation
2. `generate_repair_plan(conflict_id, partner_id)` → apology scripts, repair steps
3. `update_relationship_metrics(conflict_id)` → fight frequency, trends
4. `weekly_summary(relationship_id)` → insights, stats, recommendations
5. `simulate_partner_reaction(relationship_id, target_partner_id, message)` → likely reaction, risk score
6. `log_cycle_event(partner_id, event_type, timestamp?, notes?)` → status
7. `log_intimacy_event(relationship_id, timestamp?, initiator_id?)` → status

---

## Data Model

### Key Tables

```
relationships(id, partner_a_id, partner_b_id)
partners(id, relationship_id, profile_json)
conflicts(id, relationship_id, transcript, vector_ref)
rants(id, partner_id, conflict_id, is_shared)
cycle_events(id, partner_id, type, timestamp, notes)
intimacy_events(id, relationship_id, timestamp)
pdfs(id, relationship_id, name, type, vector_ref)
```

### Vector Collections (Chroma)

- `handbook_docs` - Shared relationship PDFs
- `conflict_docs` - Past conflict transcripts
- `psychoeducation_docs` - Educational materials
- `partnerA_profile_docs` - Partner A preferences
- `partnerB_profile_docs` - Partner B preferences
- `notes_docs` - Custom notes

---

## Color Palette & Theme

### Colors

```
Primary Pink:  #ec4899 (main actions)
Secondary Blue: #3b82f6 (secondary actions)
Light Pink:    #fdf2f8 (backgrounds)
Light Blue:    #eff6ff (backgrounds)
Gray (text):   #1f2937 (headings), #4b5563 (body)
Status Green:  #16a34a
Status Red:    #dc2626
```

### Typography

- **Headings:** Inter/System UI, Semi-bold (600), 1.2 line height
- **Body:** Regular (400), 14-16px, 1.5-1.6 line height

---

## Frontend Component Patterns

All reusable components are documented in `docs/FRONTEND_COMPONENTS.md` with:
- Props interface
- Full implementation code
- Usage examples
- Styling guidelines

Key components:
- `Button` (variants: primary, secondary, danger, ghost)
- `Card` (with title, subtitle, footer)
- `Badge` (variants: success, error, warning, info)
- `MessageBubble` (for transcripts)
- `TranscriptPane` (scrolling message list)
- `Modal` (dialog component)
- `ChartContainer` (for analytics)

---

## Development Phases

The project is built in 8 phases (18-32 days total):

- **Phase 0 (1-2d):** Setup, LiveKit integration
- **Phase 1 (2-4d):** Fight capture with transcription
- **Phase 2 (2-3d):** Post-fight sessions & rants
- **Phase 3 (3-5d):** RAG foundation (PDFs, OCR, embedding)
- **Phase 4 (2-4d):** Conflict analysis tools
- **Phase 5 (1-2d):** Cycle & intimacy tracking
- **Phase 6 (3-5d):** Analytics dashboard
- **Phase 7 (2-4d):** Advanced interactions (simulation, patterns)
- **Phase 8 (2-3d):** Polish & deployment

See `docs/DEVELOPMENT_ROADMAP.md` for detailed phase breakdown.

---

## Important Constraints

### Privacy-First

- Always check `partner_id` for rant access
- Never auto-inject historical data
- Respect `is_shared` flag
- Encrypt sensitive data at rest

### Voice-First Design

- Minimal text input
- Voice queries preferred
- Clear visual feedback
- Large touch targets (48px min on mobile)

### Real-Time Requirements

- STT latency < 200ms (Deepgram)
- TTS latency < 300ms (ElevenLabs)
- Live transcript updates
- Responsive UI during recording

### Accessibility

- WCAG 2.1 AA compliance
- Keyboard navigation
- Screen reader support
- Color contrast 4.5:1 minimum
- Clear focus indicators

---

## Debugging Guide

| Issue | Check |
|-------|-------|
| Blank frontend screen | Check `postcss.config.js` exists, run `npm install` |
| Backend won't start | Check API keys in `.env`, PostgreSQL running |
| No transcription | Verify Deepgram API key, check LiveKit connection |
| TTS not playing | Check ElevenLabs API key, browser audio permissions |
| RAG not retrieving | Verify PDFs uploaded, check Voyage API key, test embeddings |

---

## Resources

### Documentation

- **Project Overview:** `README.md` (root)
- **Tech Stack Details:** `docs/FRAMEWORK_AND_TOOLS.md`
- **System Architecture:** `docs/SYSTEM_DESIGN.md`
- **Frontend Design:** `docs/FRONTEND_DESIGN.md`
- **Components Library:** `docs/FRONTEND_COMPONENTS.md`

### External Links

- **Deepgram Docs:** https://developers.deepgram.com/reference/
- **ElevenLabs Docs:** https://elevenlabs.io/docs/
- **Voyage AI Docs:** https://docs.voyageai.com/
- **LiveKit Docs:** https://docs.livekit.io/
- **LangChain Docs:** https://python.langchain.com/
- **React Docs:** https://react.dev/

### Example Projects

- **LiveKit Examples:** https://github.com/livekit-examples/
- **LangChain Examples:** https://python.langchain.com/docs/modules/
- **Vite Examples:** https://vitejs.dev/

---

## When to Consult Documentation

**Before implementing:**
- Always read relevant `docs/*.md` section first
- Check `SYSTEM_DESIGN.md` for architecture decisions
- Review component examples in `FRONTEND_COMPONENTS.md`

**When stuck:**
- Check `DEVELOPMENT_ROADMAP.md` for phase requirements
- Review error handling patterns in `FRONTEND_DESIGN.md`
- Consult tool specs in `SYSTEM_DESIGN.md` section 6

**For best practices:**
- Read "Best Practices" section in `DEVELOPMENT_ROADMAP.md`
- Review accessibility guidelines in `FRONTEND_DESIGN.md`
- Check performance tips in `FRAMEWORK_AND_TOOLS.md`

---

## Summary

HeartSync is a compassionate AI mediator for couples. Always remember:

✅ **Privacy-first** - Respect data boundaries  
✅ **Voice-first** - Minimal text, maximum voice  
✅ **Real-time** - Fast responses matter  
✅ **Accessible** - Works for everyone  
✅ **Well-documented** - Check docs first!

---

**Always start with `docs/README.md` for navigation guidance.**

For the latest documentation, see the `docs/` folder in this repository.



