# HeartSync – Framework & Tools Guide

Complete guide to all frameworks, libraries, and tools used in HeartSync.

---

## 🏗️ Backend Stack

### Framework: FastAPI

**Why FastAPI?**
- Modern, fast, and easy to learn
- Built-in async support (great for real-time)
- Automatic OpenAPI docs
- Great for WebSocket support

**Key Features:**
- REST API for tokens, analytics, PDFs
- WebSocket for real-time data
- Middleware for auth/logging
- Pydantic validation

**Setup:**
```bash
pip install fastapi uvicorn
python -m uvicorn app.main:app --reload
```

**Structure:**
```python
app/
├── main.py          # FastAPI app instance, routes
├── config.py        # Environment variables, settings
└── models/schemas.py # Pydantic request/response models
```

---

### Voice Agent: LiveKit Agents

**What it is:**
- Framework for building real-time audio agents
- Connects to LiveKit rooms
- Handles audio streaming, speaker diarization
- Integrates with LLMs and external STT/TTS

**Why LiveKit?**
- Managed service (no infrastructure headache)
- Flexible integration with third-party STT/TTS
- Speaker diarization support
- Scalable for production
- Real-time audio routing

**Setup:**
```bash
pip install livekit-agents livekit-agents-openai
```

**Integration with Deepgram + ElevenLabs:**
```python
app/agents/heartsync_agent.py
├── Agent initialization
├── Room connection
├── Deepgram transcription pipeline (real-time)
├── LLM processing + tool calls
├── ElevenLabs TTS response
└── Audio streaming back to room
```

**Architecture:**
```
LiveKit Room
    ↓
Audio Streams (in)
    ↓
Deepgram STT (real-time)
    ↓
Transcript + Speaker ID
    ↓
LLM + Tools
    ↓
Response Text
    ↓
ElevenLabs TTS
    ↓
Audio Stream (out) → LiveKit Room
```

**Key Modes:**
- **Silent Recording:** Deepgram transcribes, no LLM response
- **Interactive:** Deepgram → LLM → ElevenLabs → Response
- **Analytics:** Summarization mode with cached responses

---

### LLM: OpenAI

**Models Used:**
- **GPT-4 or GPT-4o-mini** — Main reasoning engine
- Strong tool/function calling support
- Best for relationship coaching nuance and emotion understanding

**Setup:**
```bash
export OPENAI_API_KEY="sk-..."
pip install openai
```

**Usage:**
```python
from openai import OpenAI

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4",
    messages=[...],
    tools=[...]  # Our 7 tools
)
```

---

### Speech-to-Text: Deepgram

**Why Deepgram?** ✅ EXCELLENT CHOICE
- **Superior accuracy** for conversational speech (which fights are!)
- **Real-time streaming** with low latency (<200ms)
- **Speaker diarization** built-in
- **Emotional tone detection** (bonus for relationship context!)
- **Cost-effective** (~60% cheaper than Whisper at scale)
- **No rate limiting** issues like OpenAI's Whisper

**Advantages over Whisper:**
- Better at handling overlapping speech (both partners talking)
- Faster real-time transcription
- More accurate with accents and casual speech
- Built-in speaker identification

**Setup:**
```bash
pip install deepgram-sdk
export DEEPGRAM_API_KEY="..."
```

**Usage:**
```python
from deepgram import Deepgram

dg_client = Deepgram(DEEPGRAM_API_KEY)

# Real-time streaming
options = {
    "model": "nova-2",  # Latest model, very accurate
    "tier": "nova",
    "language": "en",
    "smart_format": True,
    "diarize": True,  # Speaker identification
}

ws = await dg_client.transcription.live(options)
await ws.send(audio_chunk)
```

**Integration with LiveKit:**
- Use Deepgram's LiveKit plugin for seamless integration
- Or stream audio from LiveKit → Deepgram
- Recommended: LiveKit plugin for lower latency

---

### Text-to-Speech: ElevenLabs

**Why ElevenLabs?** ✅ EXCELLENT CHOICE
- **Most natural-sounding voices** on the market
- **Emotional variety** (can sound compassionate, understanding)
- **Voice cloning** available (future: let agent sound familiar)
- **Low latency** streaming (~300ms)
- **Multilingual** support
- **Stability** and consistency across calls

**Advantages over OpenAI TTS:**
- Dramatically better voice quality
- Better emotional tone delivery (critical for relationship mediator!)
- Lower latency streaming
- More natural pauses and prosody
- Better handling of names/proper nouns

**Setup:**
```bash
pip install elevenlabs
export ELEVENLABS_API_KEY="..."
```

**Usage:**
```python
from elevenlabs.client import ElevenLabs

client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Streaming response
audio = client.generate(
    text="I understand you're feeling unheard. Tell me more.",
    voice="Rachel",  # Choose from pre-built voices
    stream=True,
    model="eleven_turbo_v2_5",
)

# Or use voice_id for custom voices
```

**Voice Selection for Heartsync:**
- **"Rachel"** or **"Aria"** — Warm, compassionate (for coaching)
- **"Juniper"** — Neutral, balanced (for analysis)
- Consistency: Use same voice throughout session

---

### Embeddings: Voyage-3

**Why Voyage-3?** ✅ EXCELLENT CHOICE
- **Superior accuracy** for semantic search
- **Optimized for RAG** (better than OpenAI embeddings for retrieval)
- **Larger dimensions** (better for nuanced meaning)
- **Domain-specific** versions available
- **Cost-effective** compared to alternatives
- **Better understanding** of relationship/emotional context

**Advantages over text-embedding-3-small:**
- Specifically optimized for semantic search (vs. general purpose)
- Better performance on relationship/therapeutic domain
- Higher quality embeddings = better RAG results
- More efficient for long documents (handbooks)

**Setup:**
```bash
pip install voyageai
export VOYAGE_API_KEY="..."
```

**Usage:**
```python
import voyageai

client = voyageai.Client(api_key=VOYAGE_API_KEY)

# Embed documents (e.g., handbook chunks)
result = client.embed(
    texts=[
        "When a partner feels unheard...",
        "The cycle of escalation typically...",
    ],
    model="voyage-3",
    input_type="document"
)

# Query embeddings (search)
query_result = client.embed(
    texts=["What should I do when he raises his voice?"],
    model="voyage-3",
    input_type="query"
)
```

**Integration with Chroma:**
```python
# Use Voyage embeddings with Chroma
from chromadb.utils import embedding_functions

voyage_ef = embedding_functions.VoyageEmbeddingFunction(
    api_key=VOYAGE_API_KEY,
    model_name="voyage-3"
)

collection = client.get_or_create_collection(
    name="handbook_docs",
    embedding_function=voyage_ef
)
```

---

### Reranking: Voyage-Rerank-2

**Why Voyage-Rerank-2?** ✅ EXCELLENT CHOICE
- **Superior reranking** accuracy (beats Cohere, BGE, etc.)
- **Context-aware** ranking
- **Handles relationship nuance** well
- **Fast** (minimal latency added)
- **Reduces hallucinations** by improving retrieval quality

**When Reranking Helps:**
1. User asks: "What should I do about the yelling?"
2. Retrieve top-10 docs from Chroma
3. **Rerank to top-3** with Voyage-Rerank
4. Use only top-3 for LLM context (better quality, less hallucination)

**Setup:**
```bash
pip install voyageai
# Same API key as embeddings
```

**Usage:**
```python
import voyageai

client = voyageai.Client(api_key=VOYAGE_API_KEY)

# After Chroma retrieval
documents = [
    "When volume increases, try to lower your tone...",
    "Yelling often indicates feeling unheard...",
    "The handbook mentions de-escalation techniques...",
]

query = "What should I do when my partner starts yelling?"

# Rerank to get best matches
results = client.rerank(
    query=query,
    documents=documents,
    model="rerank-2-lite",
    top_k=3
)

# Use only results[0:3] for LLM
best_docs = [documents[result.index] for result in results[:3]]
```

---

---

### RAG: LangChain

**What it does:**
- Orchestrates RAG pipeline
- Chains tools, retrievers, prompts
- Memory management
- Vector store integration

**Why LangChain?**
- Industry standard for RAG
- Great integration with LLMs
- Handles complex chains easily
- Active community

**Setup:**
```bash
pip install langchain langchain-openai langchain-chroma
```

**In HeartSync:**
```python
app/rag/
├── retriever.py     # LangChain retriever interface
├── ingest.py        # Document chunking & embedding
└── ocr_mistral.py   # PDF extraction
```

**Key Components:**
- Prompt templates (for different contexts)
- Retrieval chains (query → embedding → Chroma search)
- Tool integration (attach to agent)

---

### Vector Store: Chroma

**What it is:**
- Lightweight vector database
- Stores embeddings + metadata
- Local (no external service for MVP)

**Why Chroma?**
- Easy to set up (no Docker needed)
- Great for MVP
- Can migrate to cloud later
- Excellent for testing

**Setup:**
```bash
pip install chromadb
```

**In HeartSync:**
```python
from chromadb import Client

client = Client()
collection = client.get_or_create_collection(
    name="handbook_docs",
    metadata={"hnsw:space": "cosine"}
)

# Add documents
collection.add(
    documents=[...],
    metadatas=[...],
    embeddings=[...],
    ids=[...]
)

# Query
results = collection.query(
    query_embeddings=[...],
    n_results=5
)
```

**Collections per Relationship:**
- `handbook_docs` — PDFs
- `conflict_docs` — Past transcripts
- `psychoeducation_docs` — Educational materials
- `partnerA_profile_docs` — Partner profiles
- `partnerB_profile_docs` — Partner profiles
- `notes_docs` — Custom notes

---

### Database: PostgreSQL

**Why PostgreSQL?**
- Reliable, production-grade
- JSON columns for flexible data
- Great for relational data
- Full-text search support
- Indexing for performance

**Setup:**
```bash
# Local development
brew install postgresql
brew services start postgresql

# Connection
export DATABASE_URL="postgresql://user:password@localhost/heartsync"
pip install sqlalchemy psycopg2-binary
```

**Models:**
```python
app/models/db.py
├── Relationship
├── Partner
├── Conflict
├── Rant
├── CycleEvent
├── IntimacyEvent
└── PDF
```

**Key Tables:**
- `relationships` — Couples
- `conflicts` — Fights with transcripts
- `rants` — Private post-fight recordings
- `cycle_events` — Period/ovulation tracking
- `intimacy_events` — Intimacy timestamps
- `pdfs` — Uploaded documents

---

### Storage: AWS S3

**Why S3?**
- Scalable file storage
- Can serve PDFs directly
- Integrates with Lambda for processing
- Cost-effective

**Setup:**
```bash
pip install boto3

export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export S3_BUCKET="heartsync-pdfs"
```

**In HeartSync:**
```python
# Upload PDF
s3_client.put_object(
    Bucket="heartsync-pdfs",
    Key=f"{relationship_id}/{pdf_id}",
    Body=file_content
)

# Retrieve for OCR
obj = s3_client.get_object(Bucket="...", Key="...")
```

---

### OCR: Mistral Vision

**What it does:**
- Extracts text from PDFs
- Handles scanned documents
- Returns structured text

**Why Mistral?**
- High accuracy
- Fast processing
- Good for relationship handbooks
- More cost-effective than some alternatives

**Setup:**
```bash
pip install mistralai
```

**Usage:**
```python
from mistralai.client import MistralClient

client = MistralClient()
response = client.vision(
    model="pixtral-12b-2409",
    messages=[...],  # Image messages
)
```

---

## 🎨 Frontend Stack

### Framework: React + Vite

**Why React?**
- Component-based architecture
- Excellent for real-time updates
- Large ecosystem
- TypeScript support

**Why Vite?**
- Fast dev server
- Instant HMR (hot module reload)
- Optimized builds
- Much faster than Webpack

**Setup:**
```bash
npm create vite@latest frontend -- --template react
cd frontend && npm install
npm run dev  # http://localhost:5173
```

**Structure:**
```
src/
├── App.tsx                 # Main app component
├── components/
│   ├── FightCaptureView.tsx
│   ├── PostFightSession.tsx
│   ├── AnalyticsDashboard.tsx
│   └── PdfManager.tsx
├── livekit/
│   ├── client.ts           # LiveKit client setup
│   └── hooks.ts            # useRoom, useParticipants, etc.
├── api/
│   ├── token.ts            # Get LiveKit token
│   ├── analytics.ts        # Fetch metrics
│   └── pdf.ts              # Upload PDFs
├── styles/theme.css
└── types/index.ts
```

---

### LiveKit Client

**What it does:**
- Connect to LiveKit rooms
- Handle audio/video tracks
- Manage room state
- Emit/receive data

**Setup:**
```bash
npm install livekit-client livekit-react
```

**Usage:**
```typescript
import { LiveKitRoom, VideoConference } from 'livekit-react';

export function FightCapture() {
  return (
    <LiveKitRoom
      url="wss://your-livekit-server"
      token={token}
      data-lk-theme="light"
    >
      <VideoConference />
    </LiveKitRoom>
  );
}
```

**Key Hooks:**
- `useRoom()` — Room state
- `useParticipants()` — Connected participants
- `useLocalParticipant()` — Your own tracks
- `useDataChannel()` — Real-time data

---

### Styling: TailwindCSS

**Why Tailwind?**
- Utility-first CSS
- Fast prototyping
- Consistent design
- Small bundle size

**Setup:**
```bash
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

**Configuration:**
```css
/* src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;
```

**Usage:**
```tsx
<div className="flex gap-4 p-6 bg-gradient-to-r from-pink-50 to-blue-50 rounded-lg">
  <button className="bg-pink-500 text-white px-4 py-2 rounded hover:bg-pink-600">
    Start Fight Capture
  </button>
</div>
```

**Cozy Theme Colors:**
```
Primary: Pink-500 (#ec4899)
Secondary: Blue-500 (#3b82f6)
Background: Soft pastels (50 variants)
Text: Gray-800
```

---

### State Management: React Context

**Why Context (not Redux)?**
- MVP doesn't need Redux complexity
- Simple global state
- Built into React
- Easy to understand

**Setup:**
```typescript
// src/context/AppContext.tsx
const AppContext = createContext();

export function AppProvider({ children }) {
  const [state, setState] = useState({
    userId: null,
    relationshipId: null,
    mode: 'idle',
    roomActive: false,
  });

  return (
    <AppContext.Provider value={{ state, setState }}>
      {children}
    </AppContext.Provider>
  );
}
```

**Usage:**
```typescript
const { state, setState } = useContext(AppContext);
```

---

### HTTP Client: Fetch API

**Why Fetch?**
- Built into browser
- Modern and Promise-based
- No additional dependencies

**Setup:**
```typescript
// src/api/token.ts
export async function getLiveKitToken(roomId: string) {
  const response = await fetch('/api/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ roomId }),
  });
  return response.json();
}
```

---

### Charts: Recharts (Optional)

**For Analytics Dashboard:**
```bash
npm install recharts
```

**Usage:**
```tsx
import { LineChart, Line, XAxis, YAxis } from 'recharts';

export function ConflictTrend({ data }) {
  return (
    <LineChart width={800} height={400} data={data}>
      <XAxis dataKey="date" />
      <YAxis />
      <Line type="monotone" dataKey="conflicts" stroke="#ec4899" />
    </LineChart>
  );
}
```

---

## 🔧 Development Tools

### Environment Variables

**Backend (.env):**
```bash
LIVEKIT_URL=wss://your-livekit-server
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://user:password@localhost/heartsync
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET=heartsync-pdfs
```

**Frontend (.env.local):**
```bash
VITE_API_URL=http://localhost:8000
VITE_LIVEKIT_URL=wss://your-livekit-server
```

---

### Version Control: Git

**Branching Strategy:**
```bash
main (always deployable)
├── feature/fight-capture
├── feature/post-fight-session
├── feature/rag-foundation
└── feature/analytics-dashboard
```

**Commits:**
```bash
git commit -m "feat: implement silent fight capture"
git commit -m "fix: privacy check on rant access"
git commit -m "refactor: extract tool definitions"
```

---

### Testing: pytest (Backend) + Vitest (Frontend)

**Backend:**
```bash
pip install pytest pytest-asyncio

# Run tests
pytest tests/ -v
```

**Frontend:**
```bash
npm install -D vitest

# Run tests
npm run test
```

---

### Linting & Formatting

**Backend:**
```bash
pip install black flake8
black app/
flake8 app/
```

**Frontend:**
```bash
npm install -D eslint prettier
npx eslint src/
npx prettier --write src/
```

---

## 📦 Dependencies Summary

### Backend (requirements.txt)
```
# Framework
fastapi==0.104.0
uvicorn==0.24.0

# Voice Agent & LiveKit
livekit==0.8.0
livekit-agents==0.8.0
livekit-agents-openai==0.8.0

# Speech-to-Text & Text-to-Speech
deepgram-sdk==3.0.0
elevenlabs==0.2.0

# LLM
openai==1.3.0

# RAG & Embeddings
langchain==0.1.0
langchain-openai==0.0.1
langchain-chroma==0.1.0
chromadb==0.4.0
voyageai==0.2.0

# Database & ORM
sqlalchemy==2.0.0
psycopg2-binary==2.9.0
alembic==1.12.0

# File Processing & Storage
mistralai==0.0.0
boto3==1.28.0
pdf-reader==0.5.0

# Utilities
pydantic==2.0.0
python-dotenv==1.0.0
requests==2.31.0
```

### Frontend (package.json)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "livekit-client": "^1.10.0",
    "livekit-react": "^0.5.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.1.0",
    "tailwindcss": "^3.3.0",
    "typescript": "^5.2.0"
  }
}
```

---

## 🚀 Local Development Setup (Complete)

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export LIVEKIT_URL="wss://your-livekit-url"
export LIVEKIT_API_KEY="your-key"
export LIVEKIT_API_SECRET="your-secret"
export OPENAI_API_KEY="sk-..."
export DATABASE_URL="postgresql://localhost/heartsync"

# Start PostgreSQL
brew services start postgresql  # or systemctl start postgresql

# Run migrations (if using Alembic)
alembic upgrade head

# Start backend
python -m uvicorn app.main:app --reload
```

Backend available at: `http://localhost:8000`  
API docs at: `http://localhost:8000/docs`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend available at: `http://localhost:5173`

### 3. Verify

- Open `http://localhost:5173` in browser
- Should see HeartSync UI
- Try "Start Fight Capture"
- Should show loading spinner (waiting for LiveKit connection)

---

## 📚 Framework Documentation

| Tool | Docs | Purpose |
|------|------|---------|
| FastAPI | https://fastapi.tiangolo.com | Backend framework |
| LiveKit Agents | https://docs.livekit.io/agents | Voice agent framework |
| LangChain | https://python.langchain.com | RAG orchestration |
| Chroma | https://docs.trychroma.com | Vector store |
| React | https://react.dev | Frontend framework |
| Vite | https://vitejs.dev | Build tool |
| TailwindCSS | https://tailwindcss.com | Styling |
| LiveKit Client | https://docs.livekit.io/sdk/js | Real-time client |

---

## 🔄 Deployment Tools (Optional)

### Docker (Backend)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### AWS Deployment

- **Backend:** ECS Fargate + RDS PostgreSQL
- **Frontend:** S3 + CloudFront
- **Storage:** S3 (for PDFs)
- **Vector Store:** Chroma (in container)

---

**All frameworks and tools are production-ready and well-documented. Start with Phase 0 to begin integration!**

