# HeartSync Documentation

Comprehensive, non-redundant documentation for the HeartSync relationship mediator.

---

## 📚 Documentation Files

### 1. **QUICK_START.md** ← START HERE!
**Audience:** Developers (all roles)  
**Time:** 5 minutes  
**Contains:**
- The 3 core modes (Fight Capture, Post-Fight, Analytics)
- 7 core tools with specs
- Data model overview
- Privacy rules matrix
- API endpoints
- Frontend state shape
- Common implementation tasks
- Debugging tips

**When to use:** You're new to the project or need a quick reference

---

### 2. **SYSTEM_DESIGN.md**
**Audience:** Technical leads, engineers  
**Time:** 20-30 minutes  
**Contains:**
- Complete system architecture
- User flows (detailed)
- Data model (SQL + Chroma)
- RAG retrieval strategy
- Privacy model
- 7 tool specifications (with schemas)
- Project structure (backend/frontend)
- API endpoints
- Tech stack
- Architecture decisions explained
- Success metrics
- Testing strategy
- Known limitations

**When to use:** You're implementing features or need complete technical context

---

### 3. **DEVELOPMENT_ROADMAP.md**
**Audience:** Project managers, engineers  
**Time:** 15-20 minutes  
**Contains:**
- 8 MVP phases (Phase 0 through Phase 8)
- 1 stretch phase (Live Mediation)
- Per-phase: Goals, deliverables, duration
- Timeline summary (18-32 days total)
- Development best practices
- Pre-launch checklist
- Risk mitigation

**When to use:** Planning sprints, prioritizing features, or tracking progress

---

### 4. **FRAMEWORK_AND_TOOLS.md** ⭐ NEW
**Audience:** Backend & frontend engineers  
**Time:** 20-30 minutes  
**Contains:**
- **Backend Stack:** FastAPI, LiveKit Agents, OpenAI, LangChain, Chroma, PostgreSQL, S3
- **Frontend Stack:** React, Vite, TailwindCSS, LiveKit Client, React Context
- Why each framework was chosen
- Setup instructions for each tool
- Code examples and usage patterns
- Local development setup (complete walkthrough)
- Deployment tools (Docker, AWS)
- Framework documentation links

**When to use:** Setting up development environment, understanding why tools were chosen, integrating frameworks

---

## 🗂️ Navigation by Role

### Backend Engineers
1. Read QUICK_START.md (5 min)
2. Read FRAMEWORK_AND_TOOLS.md section: "Backend Stack" (15 min) — **Setup your environment**
3. Jump to SYSTEM_DESIGN.md section: "Project Structure" → "Backend"
4. Reference QUICK_START.md section: "Core Tools" while implementing
5. Use DEVELOPMENT_ROADMAP.md to see what's needed next

### Frontend Engineers
1. Read QUICK_START.md (5 min)
2. Read FRAMEWORK_AND_TOOLS.md section: "Frontend Stack" (15 min) — **Setup your environment**
3. Jump to SYSTEM_DESIGN.md section: "Project Structure" → "Frontend"
4. Check QUICK_START.md section: "Frontend State Shape"
5. Use DEVELOPMENT_ROADMAP.md for feature priorities

### DevOps / Infrastructure
1. Read FRAMEWORK_AND_TOOLS.md section: "Deployment Tools" (5 min)
2. Reference SYSTEM_DESIGN.md section: "Tech Stack"
3. Use for AWS/Docker setup

### Project Managers
1. Skim QUICK_START.md (5 min)
2. Read DEVELOPMENT_ROADMAP.md (15 min)
3. Reference SYSTEM_DESIGN.md for technical questions

### Technical Leads
1. Read all documents top-to-bottom
2. Start with QUICK_START.md → SYSTEM_DESIGN.md → FRAMEWORK_AND_TOOLS.md → DEVELOPMENT_ROADMAP.md
3. Use as reference during architecture reviews

---

## 🎯 Quick Navigation by Topic

| Question | Answer In |
|----------|-----------|
| What's HeartSync in 30 seconds? | [../../README.md](../README.md) |
| What are the 3 modes? | [QUICK_START.md#-the-3-core-modes](QUICK_START.md) |
| What tools does the agent have? | [QUICK_START.md#-core-tools](QUICK_START.md) |
| What's the data model? | [QUICK_START.md#--data-model](QUICK_START.md) or [SYSTEM_DESIGN.md#3-data-model](SYSTEM_DESIGN.md) |
| What are privacy rules? | [QUICK_START.md#-privacy-rules](QUICK_START.md) |
| What are the API endpoints? | [QUICK_START.md#--api-endpoints](QUICK_START.md) |
| How long is MVP? | [DEVELOPMENT_ROADMAP.md#timeline-summary](DEVELOPMENT_ROADMAP.md) |
| What's Phase 0? | [DEVELOPMENT_ROADMAP.md#phase-0--project-setup-1--2-days](DEVELOPMENT_ROADMAP.md) |
| Why this architecture decision? | [SYSTEM_DESIGN.md#10-architecture-decisions](SYSTEM_DESIGN.md) |

---

## 🚀 Getting Started

**New to the project?**
1. Read [README.md](../README.md) (root) — 2 min overview
2. Read [QUICK_START.md](QUICK_START.md) — 5 min developer guide
3. Skim [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md) — understand phases
4. Read [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) relevant sections — deep dive

**Ready to code?**
1. Check [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md) current phase
2. Find your domain in [QUICK_START.md](QUICK_START.md) "Common Tasks"
3. Reference [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) for complete specs
4. Start coding!

---

## 📊 Document Hierarchy

```
README.md (root)
  └─ High-level project overview
    
docs/
  ├─ QUICK_START.md ← Developer quick reference
  ├─ SYSTEM_DESIGN.md ← Complete technical spec
  ├─ DEVELOPMENT_ROADMAP.md ← Development phases
  └─ README.md ← This file
```

---

## ✅ Key Takeaways

1. **3 Modes:** Fight Capture (silent) | Post-Fight (interactive) | Analytics (dashboard)
2. **7 Tools:** analyze, repair, metrics, summary, simulate, log_cycle, log_intimacy
3. **Privacy-First:** Rants private by default, RAG opt-in only
4. **18-32 Days:** MVP in 8 phases
5. **Tech Stack:** Python + React + LiveKit + LangChain + Chroma + PostgreSQL

---

## 🔗 Cross-References

- **Project Overview:** [../../README.md](../README.md)
- **Original Problem:** [../../Problem.md](../Problem.md)
- **Reference Material:** [../../Voice Agent.pdf](../Voice Agent.pdf)

---

## 💡 Pro Tips

- **Keep QUICK_START.md open** while coding — it's your cheat sheet
- **Reference SYSTEM_DESIGN.md** when implementing complex features
- **Check DEVELOPMENT_ROADMAP.md** before each sprint
- **Update docs after each phase** to keep them current

---

**Ready? Start with [QUICK_START.md](QUICK_START.md)! 🚀**

