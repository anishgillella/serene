# HeartSync – Relationship Mediator

A voice-based relationship mediator that helps couples understand each other during and after conflicts using AI-powered analysis, RAG-enabled insights, and compassionate coaching.

---

## 🎯 Overview

**HeartSync** is an emotionally intelligent mediator that:

- **Listens silently** during fights and captures real-time transcripts
- **Enables post-fight reflection** with private rants, conflict analysis, and repair coaching
- **Tracks relationship data** like cycle events, intimacy, and conflict patterns
- **Provides personalized insights** using RAG over relationship handbooks, notes, and past conflicts
- **Generates repair plans** with apology scripts and timing recommendations
- **Shows trends** through an analytics dashboard

**Key Principle:** HeartSync is a neutral, compassionate third party that helps both partners understand their relationship with honesty, curiosity, and care.

---

## ✨ Core Features

### 1. Silent Fight Capture
Both partners join a voice room; agent listens and transcribes with speaker diarization.

### 2. Post-Fight Voice Sessions
- Rant privately (stored encrypted & private to speaker)
- Get neutral conflict analysis
- Receive personalized repair coaching
- Explore patterns and growth

### 3. Manual Data Tracking
Log cycle events, intimacy moments, and custom relationship notes.

### 4. RAG-Enhanced Retrieval
Upload PDFs and query them by voice. All retrieval is opt-in (never automatic).

### 5. Analytics Dashboard
Visualize conflict trends, intimacy frequency, and optional cycle correlations.

### 6. Advanced Interactions
Simulate partner reactions and identify behavioral patterns.

---

## 📖 Documentation

All detailed documentation is in the `docs/` folder:

- **[docs/QUICK_START.md](docs/QUICK_START.md)** ← Start here! 5-min overview for developers
- **[docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md)** ← Complete technical architecture
- **[docs/DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md)** ← 8-phase development plan (18–32 days)

---

## 🔒 Privacy & Security

**Data Privacy:**
- **Fight transcripts:** Shared between partners
- **Individual rants:** Private to speaker (encrypted)
- **PDFs/Handbook:** Shared between partners
- **Cycle data:** Private to owner
- **Metrics:** Shared (aggregate only)

**Key Principles:**
- Rants are **private by default** — Never auto-referenced to other partner
- RAG retrieval is **opt-in only** — Historical data never injected automatically
- All sharing requires **explicit permission**

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+ | Node.js 16+ | PostgreSQL 12+
- LiveKit Cloud account | OpenAI API key | AWS account (optional for S3)

### Local Setup (5 min)

```bash
# Backend
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export LIVEKIT_URL="wss://..." OPENAI_API_KEY="sk-..."
python -m uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend && npm install && npm run dev
```

Visit `http://localhost:5173`

---

## 🏗️ Tech Stack

**Backend:** Python + FastAPI + LiveKit Agents + LangChain + Chroma + PostgreSQL + S3  
**Frontend:** React + Vite + LiveKit Client + TailwindCSS  
**Deployment:** AWS (EC2/ECS Fargate + CloudFront + RDS)

---

## 🎯 MVP Success Criteria

✅ Two partners can silently capture a fight  
✅ Post-fight sessions allow private reflection  
✅ Repair plans are personalized & actionable  
✅ Analytics show meaningful trends  
✅ PDFs uploadable and queryable  
✅ All rants are private by default  
✅ No critical bugs or console errors  

---

## 📅 Development Timeline

**MVP Ready in:** 18–32 days (8 phases)

See [docs/DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md) for phase breakdown.

---

## 🤝 Contributing

1. Review [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) for architecture
2. See [docs/DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md) for priorities
3. Keep tests + documentation updated

---

## 📧 Support

Questions? Start with [docs/QUICK_START.md](docs/QUICK_START.md) or check the full docs.

---

**Built with ❤️ for couples building understanding through conflict.**  
*Start here: [docs/QUICK_START.md](docs/QUICK_START.md)*
