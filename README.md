# Luna – RAG-Enabled Voice Mediator Agent

A voice-based relationship mediator that helps couples navigate conflicts through empathetic AI-powered conversations, real-time transcription, and RAG-enabled insights from conversation history and partner profiles.

---

## Project Overview & Story

### Luna: Your Empathetic Relationship Mediator

**Luna** is a friendly AI mediator designed to help couples understand each other during and after conflicts. Luna takes the perspective of Adrian (the boyfriend) while helping him understand Elara's (the girlfriend's) point of view, providing empathetic support and practical guidance.

**Personality:**
- Warm, empathetic, and non-judgmental
- Curious and interested in understanding both perspectives
- Keeps responses brief and natural (2-3 sentences max for voice)
- Uses conversational, human language
- Supportive but honest
- Deeply empathetic towards Adrian's perspective and feelings

**Problem Solved:**
Couples often struggle to communicate effectively during conflicts. Luna provides a neutral, compassionate third party that listens, validates feelings, and helps partners understand each other better through voice-based conversations enhanced with context from past conversations and partner profiles.

**Narrative:**
Luna acts as Adrian's supportive confidant, validating his feelings by connecting them to his background (e.g., passion for sports, values, personality traits) while subtly helping him understand Elara's perspective. Luna uses RAG to access the entire conversation history and partner profiles, enabling deeply contextualized, empathetic responses.

---

## Design Document

### End-to-End System Architecture

**High-Level Flow:**
```
User → React Frontend → LiveKit Cloud → Python Agent → RAG System (Pinecone + Voyage) → LLM → TTS → User
```

**Component Breakdown:**

1. **Frontend (React + Vite)**
   - Chat interface with real-time transcription display
   - "Start Call" / "End Call" buttons
   - PDF upload interface
   - Post-fight analysis and repair plan views
   - Connects to LiveKit Cloud via WebSocket

2. **Backend (FastAPI)**
   - REST API endpoints for tokens, transcript storage, analysis generation
   - Token generation for LiveKit room access
   - Transcript storage (S3 + Pinecone + PostgreSQL)
   - Conflict analysis and repair plan generation endpoints

3. **LiveKit Agent (Python)**
   - Voice agent with STT/LLM/TTS pipeline
   - Real-time audio streaming via LiveKit Cloud
   - Speaker diarization (identifies Adrian vs Elara)
   - RAG integration via `on_user_turn_completed` hook
   - Room filtering (only joins `mediator-*` rooms)

4. **RAG System**
   - **Vector Store**: Pinecone (serverless, managed)
   - **Embeddings**: Voyage-3 (1024 dimensions)
   - **Reranking**: Voyage-Rerank-2
   - **Chunking**: LangChain RecursiveCharacterTextSplitter
   - Queries entire corpus (all transcripts + profiles) for contextualized responses

5. **Storage Layer**
   - **PostgreSQL**: Conflict metadata, analysis results, repair plans
   - **S3**: Raw transcript JSON files, PDFs, analysis/repair plan documents
   - **Pinecone**: Vector embeddings for semantic search

**Architecture Diagram (Text-Based):**
```
┌─────────────┐
│   User      │
│  (Browser)  │
└──────┬──────┘
       │ WebSocket
       ▼
┌─────────────────┐         ┌──────────────┐
│  React Frontend │─────────▶│ LiveKit Cloud│
│  (Vite + React) │         │  (Managed)   │
└─────────────────┘         └──────┬───────┘
                                    │
                                    ▼
                            ┌─────────────────┐
                            │  Python Agent   │
                            │  (LiveKit SDK)  │
                            └──────┬──────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
            ┌───────────┐  ┌──────────┐  ┌─────────────┐
            │  Deepgram │  │ OpenRouter│  │ ElevenLabs │
            │   (STT)   │  │   (LLM)  │  │    (TTS)   │
            └───────────┘  └──────────┘  └─────────────┘
                    │              │
                    │              ▼
                    │      ┌──────────────┐
                    │      │  RAG System │
                    │      └──────┬───────┘
                    │             │
                    │      ┌──────┴───────┐
                    │      │              │
                    ▼      ▼              ▼
            ┌──────────┐ ┌──────────┐ ┌──────────┐
            │ Pinecone │ │  Voyage  │ │  Voyage  │
            │ (Vectors)│ │ (Embed)  │ │(Rerank)  │
            └──────────┘ └──────────┘ └──────────┘
```

### RAG Integration Details

**Vector Store Architecture:**
- **Platform**: Pinecone (serverless, managed vector database)
- **Index**: Single index (`serene`) with multiple namespaces:
  - `transcript_chunks`: Conversation transcripts (chunked)
  - `profiles`: Partner profile PDFs (Adrian/Elara)
  - `analysis`: Conflict analysis results
  - `repair_plans`: Repair plan documents

**Embedding Model: `voyage-3`**
- **Dimensions**: 1024
- **Optimization**: Specifically optimized for semantic search (better RAG performance than general-purpose embeddings)
- **Input Types**: Separate "document" and "query" embeddings for optimal retrieval
  - Documents: `input_type="document"` for transcripts, profiles
  - Queries: `input_type="query"` for user questions
- **Why `voyage-3`?**
  - Superior accuracy for semantic search
  - Better understanding of relationship/emotional context
  - Cost-effective compared to alternatives
  - Optimized for RAG use cases

**Reranking: Voyage-Rerank-2**
- **Purpose**: Improves retrieval quality by filtering irrelevant chunks from SECONDARY context
- **Strategy**: 
  - Primary context (current conflict): NOT reranked - ALL chunks included in conversation order
  - Secondary context (profiles + past conflicts): Reranked to top-7 most relevant
- **Benefits**:
  - Reduces hallucinations by ensuring only relevant supplementary context reaches LLM
  - Context-aware ranking (understands relationship nuance)
  - Current conflict always has full context (not filtered by reranking)

**Chunking Strategy:**

1. **Transcripts** (LangChain RecursiveCharacterTextSplitter):
   - **Chunk Size**: 1000 characters
   - **Overlap**: 200 characters
   - **Separators**: `["\n\n", "\n", " ", ""]` (preserves paragraph structure)
   - **Metadata Preserved**: Speaker labels, conflict_id, relationship_id, timestamp
   - **Rationale**: Balance between context preservation and token efficiency

2. **PDFs** (Simple split):
   - **Chunk Size**: 10,000 characters per chunk
   - **Metadata**: PDF type (boyfriend_profile/girlfriend_profile), relationship_id
   - **Rationale**: Profile PDFs are longer documents; larger chunks preserve context

**RAG Flow (Real-Time):**

1. **User Query** → Extracted from transcribed speech
2. **Embedding Generation** → Voyage-3 query embedding (~100-200ms)
3. **Primary Context** → Pinecone query with `filter={"conflict_id": conflict_id}` to get ALL chunks from CURRENT conflict (up to 20 chunks) (~150-250ms)
4. **Secondary Context** → Parallel queries to `profiles` (top-3) and past `transcript_chunks` excluding current conflict (top-5) (~200-300ms)
5. **Reranking** → Voyage-Rerank-2 reranks ONLY secondary candidates to top-7 (~100-200ms)
6. **Context Formatting** → Primary context (current conflict) comes FIRST, then secondary context (profiles + past conflicts)
7. **LLM Injection** → Injected into chat context via `on_user_turn_completed` hook
8. **LLM Response** → GPT-4o-mini generates empathetic response using context (~500-1000ms)
9. **TTS** → ElevenLabs converts response to speech (~300-500ms)

**Total Latency**: ~1.2-2.2 seconds per turn (acceptable for voice conversation)

**Key Design Decision**: The current conflict's transcript is ALWAYS the PRIMARY context. When users ask "summarize this conversation" or "what happened", Luna uses ONLY the current conflict's transcript. Secondary context (profiles, past conflicts) provides supplementary understanding but never overrides the primary source.

**Real-Time Integration:**
- RAG lookup triggered on every user turn via `on_user_turn_completed` hook
- Context injected before LLM generates response
- Enables Luna to answer questions about past conversations and partner profiles in real-time voice conversation

**Example RAG Query:**
```
User: "Why did Elara say she would come to the game but then didn't?"
→ RAG retrieves:
  PRIMARY CONTEXT (current conflict - always included):
  - All transcript chunks from current conversation in order
  
  SECONDARY CONTEXT (reranked for relevance):
  - Profile chunk: "Elara tends to give casual responses without firm commitments"
  - Past conflict chunk: "Adrian: I thought you said you'd come"
  
→ Luna responds: "I understand you're coming from a sports background and passionate about football, 
   so it hurt when Elara didn't attend the game even though she said 'sure'. Based on her profile, 
   she tends to give casual responses without firm commitments, which might explain the miscommunication."
```

### Tools/Frameworks Used

**Voice Agent Stack:**
- **LiveKit**: Cloud hosting, real-time audio streaming, speaker diarization
- **STT**: Deepgram `nova-3` (speaker diarization enabled, ~200ms latency)
- **LLM**: `openai/gpt-4o-mini` via OpenRouter (cost-effective, fast inference)
- **TTS**: ElevenLabs `eleven_flash_v2_5` (voice ID: ODq5zmih8GrVes37Dizd, ~300-500ms latency)
- **VAD**: Silero VAD (lightweight voice activity detection)

**RAG Framework:**
- **Text Splitting**: LangChain RecursiveCharacterTextSplitter
- **Vector DB**: Pinecone (serverless, managed)
- **Embeddings**: `voyage-3` (1024 dimensions, via Voyage AI API)
- **Reranking**: `rerank-2` (via Voyage AI API)
- **Retrieval**: Custom implementation (direct Pinecone queries for performance)

**Backend:**
- **Framework**: FastAPI (async, WebSocket support)
- **Database**: PostgreSQL (via Supabase + direct connection)
- **Storage**: AWS S3 (transcripts, PDFs, analysis documents)
- **PDF OCR**: Mistral Vision API (extracts text from PDFs)

**Frontend:**
- **Framework**: React 18 + Vite
- **Styling**: TailwindCSS
- **State Management**: React Context
- **LiveKit Client**: Official LiveKit JavaScript SDK

**Development Tools:**
- **Python**: 3.9+
- **Node.js**: 16+
- **Package Managers**: pip (Python), npm (Node.js)

---

## Setup Instructions

### Prerequisites

**Required:**
- Python 3.9+ installed
- Node.js 16+ installed
- PostgreSQL database (or Supabase account)
- Git (for cloning repository)

**API Keys Required:**
- **LiveKit Cloud**: URL, API Key, API Secret (sign up at https://cloud.livekit.io)
- **Deepgram**: API key for STT (sign up at https://deepgram.com)
- **OpenRouter**: API key for LLM access (sign up at https://openrouter.ai)
- **ElevenLabs**: API key for TTS (sign up at https://elevenlabs.io)
- **Voyage AI**: API key for embeddings and reranking (sign up at https://www.voyageai.com)
- **Pinecone**: API key for vector database (sign up at https://www.pinecone.io)
- **AWS**: Access Key ID and Secret Access Key for S3 storage
- **Mistral**: API key for PDF OCR (optional, sign up at https://mistral.ai)

### Local Setup

**1. Clone Repository:**
```bash
git clone <repository-url>
cd serene
```

**2. Backend Setup:**
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (copy from .env.example if available)
# Add all required API keys:
# LIVEKIT_URL=wss://your-project.livekit.cloud
# LIVEKIT_API_KEY=your-api-key
# LIVEKIT_API_SECRET=your-api-secret
# DEEPGRAM_API_KEY=your-deepgram-key
# OPENROUTER_API_KEY=your-openrouter-key
# ELEVENLABS_API_KEY=your-elevenlabs-key
# VOYAGE_API_KEY=your-voyage-key
# PINECONE_API_KEY=your-pinecone-key
# AWS_ACCESS_KEY_ID=your-aws-key
# AWS_SECRET_ACCESS_KEY=your-aws-secret
# DATABASE_URL=postgresql://user:password@localhost:5432/serene
# SUPABASE_URL=your-supabase-url
# SUPABASE_KEY=your-supabase-key
# MISTRAL_API_KEY=your-mistral-key (optional)

# Start backend server
python -m uvicorn app.main:app --reload
```

**3. Agent Setup (Separate Terminal):**
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate

# Start Luna mediator agent
python start_agent.py
```

**4. Frontend Setup (New Terminal):**
```bash
cd frontend

# Install dependencies
npm install

# Create .env file (if needed)
# VITE_API_URL=http://localhost:8000

# Start development server
npm run dev
```

**5. Access Application:**
- Frontend: http://localhost:5175 (or port shown in terminal)
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### LiveKit Cloud Setup

**No Additional Configuration Required:**
- Agent automatically connects to LiveKit Cloud via `LIVEKIT_URL` environment variable
- Frontend connects to LiveKit Cloud via WebSocket (configured in frontend code)
- LiveKit Cloud handles all real-time audio infrastructure

**To Use LiveKit Cloud:**
1. Sign up at https://cloud.livekit.io
2. Create a project
3. Copy your project URL, API Key, and API Secret
4. Add to `.env` file:
   ```
   LIVEKIT_URL=wss://your-project.livekit.cloud
   LIVEKIT_API_KEY=your-api-key
   LIVEKIT_API_SECRET=your-api-secret
   ```

### AWS Deployment (Optional/Bonus)

**Backend Deployment:**
- **Option 1**: EC2 Instance
  - Launch EC2 instance (Ubuntu 22.04)
  - Install Python, Node.js, PostgreSQL
  - Clone repository and follow local setup steps
  - Use systemd or PM2 to run backend and agent as services
  - Configure security groups for HTTP/HTTPS access

- **Option 2**: ECS Fargate (Recommended)
  - Create Dockerfile for backend
  - Build and push to ECR
  - Create ECS task definition
  - Deploy to Fargate cluster
  - Configure load balancer

**Frontend Deployment:**
- Build production bundle: `npm run build`
- Upload `dist/` folder to S3 bucket
- Configure S3 bucket for static website hosting
- Set up CloudFront distribution for CDN
- Configure custom domain (optional)

**Database:**
- Use RDS PostgreSQL (managed database)
- Update `DATABASE_URL` in backend `.env`
- Configure security groups for database access

**Vector Store:**
- Pinecone is already cloud-hosted (no deployment needed)
- Ensure `PINECONE_API_KEY` is set in production environment

**Environment Variables:**
- Store all API keys in AWS Secrets Manager or environment variables
- Never commit `.env` files to version control

---

## Design Decisions & Assumptions

### Trade-offs and Limitations

**1. Real-Time RAG Latency**
- **Trade-off**: RAG lookup adds ~500ms-1s latency per turn
- **Rationale**: Better context vs. faster responses
- **Solution**: 
  - Optimized reranking to top-7 chunks (reduces processing time)
  - Parallel Pinecone queries (transcripts + profiles)
  - Acceptable latency for voice conversation (~1-2 seconds total)

**2. Chunking Strategy**
- **Trade-off**: Fixed-size chunks (1000 chars) may split conversations mid-sentence
- **Rationale**: Simplicity vs. semantic boundaries
- **Solution**: 
  - 200-char overlap preserves context across boundaries
  - RecursiveCharacterTextSplitter uses intelligent separators (`\n\n`, `\n`, ` `)
  - Speaker labels preserved in metadata

**3. No Explicit Tool Calling**
- **Limitation**: Conflict analysis/repair plans available via API endpoints, not voice tool calls
- **Current Implementation**: Users access via frontend buttons ("View Analysis", "View Repair Plan")
- **Rationale**: RAG serves as the primary "tool" mechanism (enables answering questions from PDFs)
- **Future Enhancement**: Could add function calling for voice-triggered analysis (e.g., "Luna, analyze this conflict")

**4. Chapter-Level Queries**
- **Limitation**: PDFs chunked by size, not chapter structure
- **Current Behavior**: Semantic search finds relevant content but doesn't preserve chapter metadata
- **Rationale**: Simpler implementation, sufficient for most queries
- **Future Enhancement**: Add chapter detection and metadata preservation for explicit chapter queries

**5. Single Relationship Focus**
- **Assumption**: MVP focuses on one relationship (hardcoded relationship_id)
- **Rationale**: Simplifies data model and queries
- **Future Enhancement**: Multi-tenant support with proper relationship isolation

### Hosting Assumptions

**LiveKit Cloud (Managed Service)**
- **Assumption**: No need to self-host LiveKit server
- **Rationale**: 
  - Reduced infrastructure complexity
  - Managed scaling and reliability
  - Pay-per-use pricing (cost-effective for MVP)
- **Alternative Considered**: Self-hosted LiveKit server - rejected due to complexity

**Pinecone (Serverless Vector DB)**
- **Assumption**: Cloud-hosted vector store sufficient for MVP
- **Rationale**:
  - No vector DB maintenance required
  - Serverless scaling (handles growth automatically)
  - Free tier available (sufficient for development)
  - Fast query performance
- **Alternative Considered**: Chroma (local) - rejected due to deployment complexity

**Backend Hosting**
- **Current**: Local development
- **Production Assumption**: AWS EC2/ECS Fargate recommended
- **Rationale**: 
  - Scalable infrastructure
  - Easy integration with S3 and RDS
  - Cost-effective for production workloads

### RAG Assumptions

**Vector DB Choice: Pinecone**

**Why Pinecone over Chroma/Local?**
- **Managed Service**: No infrastructure to maintain
- **Serverless Scaling**: Automatically handles growth
- **Multiple Namespaces**: Organizes transcripts, profiles, analysis, repair plans
- **Fast Query Performance**: Optimized for semantic search
- **Free Tier**: Sufficient for MVP development
- **Alternative Considered**: Chroma (local) - rejected due to deployment complexity and maintenance overhead

**Chunking Strategy: RecursiveCharacterTextSplitter**

**Chunk Size: 1000 characters**
- **Rationale**: Balance between context preservation and token efficiency
- **Small enough**: Fits within LLM context windows without token bloat
- **Large enough**: Preserves conversation flow and speaker context
- **Trade-off**: May split mid-sentence, but overlap mitigates this

**Overlap: 200 characters**
- **Rationale**: Prevents context loss at chunk boundaries
- **Benefit**: Preserves speaker continuity across chunks
- **Trade-off**: Slight redundancy, but improves retrieval quality

**Separators: `["\n\n", "\n", " ", ""]`**
- **Rationale**: Preserves paragraph structure
- **Benefit**: Maintains speaker labels ("Speaker: text") intact
- **Result**: Better semantic understanding of conversation flow

**Embedding Model: Voyage-3**

**Why Voyage-3 over OpenAI/text-embedding-3-small?**
- **Optimized for Semantic Search**: Better RAG performance than general-purpose embeddings
- **Relationship Context**: Better understanding of emotional/relationship nuance
- **Dimensions**: 1024 dimensions (vs 1536 for text-embedding-3-small) - sufficient for nuance
- **Cost-Effective**: Competitive pricing for high-quality embeddings
- **Input Types**: Separate "document" and "query" embeddings for optimal retrieval

**Reranking: Voyage-Rerank-2**

**Why Reranking?**
- **Improves Retrieval Quality**: Beats Cohere, BGE, and other rerankers
- **Reduces Hallucinations**: Filters irrelevant chunks before LLM processing
- **Context-Aware**: Understands relationship nuance better than simple similarity

**Strategy: Primary (unranked) + Secondary (reranked to top-7)**
- **Primary Context**: Current conflict chunks NOT reranked (preserves full conversation)
- **Secondary Context**: Profiles (top-3) + past conflicts (top-5) → reranked to top-7
- **Rationale**: Current conversation should never be filtered; supplementary context should be relevant
- **Trade-off**: Slight latency increase (~100-200ms) for significant quality improvement

**Framework: LangChain**

**Why LangChain?**
- **Standard RAG Patterns**: Well-documented text splitting and retrieval patterns
- **Easy Integration**: Works seamlessly with Pinecone
- **Community Support**: Large community and extensive documentation

**Usage: Text Splitting Only**
- **Not Using**: Full LangChain RAG chain
- **Rationale**: Custom retrieval logic provides better control and performance
- **Implementation**: Direct Pinecone queries for faster, more flexible retrieval

### LiveKit Agent Design Decisions

**Agent Pattern: RAGMediator extends voice.Agent**

**Why extend voice.Agent?**
- **Built-in Pipeline**: STT/LLM/TTS pipeline handled automatically
- **Turn Management**: Automatic turn detection and management
- **Hooks**: `on_user_turn_completed` hook enables RAG integration
- **Alternative Considered**: Custom agent implementation - rejected (too complex, unnecessary)

**STT: Deepgram `nova-3`**

**Why Deepgram?**
- **Superior Speaker Diarization**: Best-in-class accuracy for identifying speakers
- **Real-Time Streaming**: Low latency (~200ms) for natural conversation
- **Model**: `nova-3` (best diarization accuracy)
- **Features**: Speaker diarization enabled for identifying Adrian vs Elara

**LLM: GPT-4o-mini via OpenRouter**

**Why GPT-4o-mini?**
- **Cost-Effective**: Significantly cheaper than GPT-4
- **Sufficient Quality**: Adequate for empathetic, contextual responses
- **Fast Inference**: Lower latency than GPT-4

**Why OpenRouter?**
- **Unified API**: Single API for multiple models
- **Easy Model Switching**: Can switch models without code changes
- **Competitive Pricing**: Often cheaper than direct provider APIs

**TTS: ElevenLabs `eleven_flash_v2_5`**

**Why ElevenLabs?**
- **Natural Voice Quality**: Emotional, human-like voice
- **Low Latency Streaming**: ~300-500ms latency
- **Custom Voice Support**: Can use custom voices
- **Model**: `eleven_flash_v2_5` (fast, stable, good quality)
- **Voice ID**: `ODq5zmih8GrVes37Dizd` (friendly, empathetic female voice)

**VAD: Silero VAD**

**Why Silero?**
- **Lightweight**: Fast, low-resource voice activity detection
- **Good Accuracy**: Reliable detection of speech vs. silence
- **Built-in**: Included with LiveKit Agents (no additional setup)

**Room Filtering: mediator-* Pattern**

**Why Filter Rooms?**
- **Prevents Wrong Joins**: Agent only joins mediator rooms, not fight capture rooms
- **Extracts Context**: Room name contains conflict_id (`mediator-{conflict_id}`)
- **Enables Conflict-Specific Context**: Agent can fetch relevant transcript chunks

**Initial Context Fetching**

**Strategy**: Query ONLY current conflict's transcript (using Pinecone filter)
- **Rationale**: Luna should have full context of THIS specific conversation first
- **Query**: `filter={"conflict_id": {"$eq": conflict_id}}` with top_k=20
- **Result**: All chunks from current conflict, sorted by chunk_index (maintains conversation order)
- **Benefit**: Luna can accurately summarize "this conversation" without mixing in other conflicts
- **Secondary**: Profiles and past conflicts available via RAG for deeper context when relevant

---

## Future Enhancements

1. **Explicit Tool Calling**: Add function calling for voice-triggered conflict analysis and repair plan generation
2. **Chapter-Level Queries**: Add chapter detection and metadata preservation for PDF queries
3. **Multi-Tenant Support**: Support multiple relationships with proper data isolation
4. **Advanced Analytics**: Pattern detection across conflicts, relationship health scoring
5. **Voice Cloning**: Use partner-specific voice cloning for more personalized TTS

---

## Submission

**Repository**: [GitHub URL]

**Contact**: [Your Email]

**Submission Date**: [Date]

---

**Built with care for couples building understanding through conflict.**
