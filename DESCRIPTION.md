# Serene - User Guide

Welcome to **Serene**, your AI-powered relationship companion designed to help you navigate conflicts, understand patterns, and build stronger connections.

---

##  What is Serene?

Serene uses AI to help couples communicate better during disagreements. Think of it as having a smart, empathetic mediator available 24/7 to help you:
- **Capture and analyze conflicts** in real-time
- **Talk to Luna**, your AI relationship coach who remembers your history
- **Track patterns** with menstrual cycle awareness
- **Get personalized repair plans** to resolve disagreements
- **Build deeper understanding** of each other over time

---

##  Application Components

### 1. **Home Dashboard** 
*Your starting point*

- **Quick Actions**: Start a new session, check calendar, or view history
- **Recent Conflicts**: See your last 3 conflicts at a glance
- **Personalized Greeting**: Time-aware welcome message
- **Navigation Hub**: Access all features from one place

**How to use:**
- Click **"Start Session"** to capture a new conflict
- Browse recent conflicts to review past discussions
- Use quick links to navigate to Calendar or History

---

### 2. **Fight Capture** 
*Real-time conflict recording*

Capture disagreements as they happen with our intelligent recording interface.

**Features:**
- **Live Audio Recording**: Capture the conversation in real-time
- **Automatic Transcription**: Speech-to-text powered by Deepgram
- **Speaker Diarization**: Automatically identifies who's speaking
- **Duration Tracking**: See how long the discussion has been
- **One-Click Start/Stop**: Simple controls for stress-free recording

**How to use:**
1. Click **"Start Recording"** when a disagreement begins
2. The app automatically transcripts and identifies speakers (Partner A / Partner B)
3. Click **"Stop & Analyze"** when you're done
4. You'll be redirected to see insights and repair suggestions

**Pro Tip:** The longer the recording, the better Luna can understand the context!

---

### 3. **Post-Fight Session** 
*AI-powered insights & repair plans*

After capturing a conflict, this page shows you what went wrong and how to fix it.

**Features:**
- **Conflict Analysis**: 
  - Fight summary and root cause
  - Key topics and emotional triggers
  - What went well and what didn't
  - Communication patterns identified
  
- **Personalized Repair Plans**:
  - Step-by-step apology scripts
  - Timing suggestions (considers menstrual cycles!)
  - Action items for reconciliation
  - Conversation starters

- **Luna Voice Chat**:
  - Talk to Luna about the conflict
  - Ask questions like "Why is she upset?" or "What should I say?"
  - Luna remembers ALL your past conversations and profiles
  - Voice-to-voice conversation powered by ElevenLabs

**How to use:**
1. **Review the Analysis**: Read through the AI-generated insights
2. **Check Your Repair Plan**: Follow Luna's step-by-step guidance
3. **Talk to Luna**: Click the voice button to discuss the conflict
   - Luna has context about:
     - All past conflicts and conversations
     - Both partners' personalities (from uploaded profiles)
     - Elara's menstrual cycle phase
     - Relationship patterns over time
4. **Act on It**: Use the repair plan to make amends

**Example Luna Questions:**
- "Can you summarize what happened in this fight?"
- "Why did Elara get upset about the game?"
- "What similar fights have we had before?"
- "When's the best time to apologize based on her cycle?"

---

### 4. **History** 
*Your conflict timeline*

Browse all past conflicts with filtering and search capabilities.

**Features:**
- **Timeline View**: See all conflicts in chronological order
- **Search**: Find specific conflicts by title or topic
- **Filter by Status**: Active, Resolved, or All
- **Conflict Cards**: Shows title, date, status, topics, and summary
- **Quick Navigation**: Click any conflict to see full details

**How to use:**
1. Browse the timeline to see your relationship journey
2. Use the **search bar** to find specific conflicts
3. **Filter** by status to focus on unresolved issues
4. Click any conflict card to review analysis and repair plans

---

### 5. **Calendar** 
*Relationship timeline with cycle tracking*

Track important events and understand patterns with menstrual cycle awareness.

**Features:**
- **Cycle Phase Shading**: 
  - See Elara's current cycle phase (Menstrual, Follicular, Ovulation, Luteal)
  - Background colors indicate hormonal phases
  - High-risk phases highlighted (PMS/Menstruation)

- **Event Logging**: Click any date to log:
  - **Intimacy** events
  - **Arguments** / conflicts
  - **Period Start** dates
  - **Date Nights** and memorable moments

- **Conflict Markers**: Red dots show when fights occurred
- **Today Indicator**: Circle around current date
- **Month Navigation**: Browse past and future months

**How to use:**
1. **View Cycle Phases**: Background colors show hormonal phases
2. **Log Events**: Click any date → select event type → add notes
3. **Spot Patterns**: Notice if conflicts cluster around certain cycle phases
4. **Plan Timing**: Use cycle info to time important conversations

**Pro Tip:** Conflicts during PMS/menstruation may need extra empathy and patience!

---

### 6. **Analytics** 
*Relationship health dashboard*

See the big picture with data-driven insights about your relationship.

**Features:**
- **Health Score**: Overall relationship health (0-100)
- **Conflict Trends**: Weekly conflict frequency charts
- **Cycle Correlation**: How conflicts align with menstrual phases
- **Tension Forecast**: Predict higher-risk periods
- **Topic Analysis**: Most common conflict themes
- **Communication Patterns**: Identify recurring issues

**How to use:**
1. Review your **health score** to gauge overall relationship wellness
2. Check **conflict trends** to see if things are improving
3. Use **cycle correlation** data to understand hormonal patterns
4. Plan ahead with the **tension forecast**

---

### 7. **Upload** 
*Partner profiles for personalized AI*

Upload personality profiles to help Luna understand each partner better.

**Features:**
- **Boyfriend Profile**: Upload Adrian's personality description
- **Girlfriend Profile**: Upload Elara's personality description
- **RAG Integration**: Profiles are embedded and used for contextual AI responses
- **File Management**: View uploaded profiles and their status

**How to use:**
1. Prepare PDF documents describing each partner:
   - Personality traits
   - Communication style
   - Values and priorities
   - Background and upbringing
   - Hobbies and interests
   
2. Select **profile type** (Boyfriend/Girlfriend)
3. Upload the PDF
4. Luna will use this context in all future conversations!

**Example Profile Content:**
> "Adrian is a 28-year-old software engineer who values honesty and direct communication. He's a big sports fan, especially football, and feels disconnected when plans are canceled. He grew up in a household where conflicts were addressed head-on..."

---

##  Luna - Your AI Mediator

Luna is an advanced voice AI agent (powered by LiveKit, Deepgram, and ElevenLabs) who:

### What Luna Remembers:
 **All past conversations** (across all conflicts)  
 **Both partners' profiles** (uploaded PDFs)  
 **Menstrual cycle patterns** (for timing awareness)  
 **Relationship history** (patterns, recurring themes)  
 **Current conflict context** (what just happened)  

### How to Talk to Luna:
1. Click the **voice button** on Post-Fight Session page
2. Speak naturally - Luna listens and responds in real-time
3. Ask about current or past conflicts
4. Get advice on timing, communication, and repair strategies

### Luna's Personality:
- Friendly and casual (like talking to a buddy)
- Empathetic but honest
- Remembers your context
- Gives practical, actionable advice
- Won't judge, just helps you grow

---

##  Key Technologies

- **Voice AI**: Deepgram (STT) + ElevenLabs (TTS) + LiveKit (Real-time)
- **LLM**: OpenAI GPT-4o-mini via OpenRouter
- **RAG System**: Pinecone (vector DB) for contextual memory
- **Database**: Supabase (PostgreSQL)
- **Frontend**: React + TypeScript + Vite
- **Backend**: FastAPI (Python)

---

##  Tips for Best Results

1. **Upload Profiles First**: The more Luna knows about you both, the better her advice
2. **Record Longer Conflicts**: More context = better analysis
3. **Talk to Luna Often**: She gets smarter as she learns your patterns
4. **Log Cycle Events**: Helps predict high-tension periods
5. **Review Past Conflicts**: See how you've grown over time
6. **Use Repair Plans**: Don't just read them - actually follow the steps!
7. **Be Honest**: Luna's analysis is only as good as the input

---

##  Quick Start Workflow

**For a new conflict:**
1. Go to **Fight Capture** → Start Recording
2. Have your discussion (Luna captures it)
3. Stop Recording → View **Post-Fight Session**
4. Read the **Analysis** and **Repair Plan**
5. **Talk to Luna** if you have questions
6. **Act** on the repair plan
7. Log the outcome in **Calendar**

**For ongoing tracking:**
1. Check **Analytics** weekly to see trends
2. Use **Calendar** to log intimacy and dates
3. Review **History** to see growth over time

---

##  Navigation Guide

- **Home** (`/`) - Dashboard and quick actions
- **Fight Capture** (`/fight-capture`) - Record new conflicts
- **Post-Fight** (`/post-fight`) - View analysis & talk to Luna
- **History** (`/history`) - Browse past conflicts
- **Calendar** (`/calendar`) - Track events and cycles
- **Analytics** (`/analytics`) - Relationship health data
- **Upload** (`/upload`) - Manage partner profiles

---

##  About the Name "Serene"

Serene represents the calm, peace, and understanding we hope to bring to your relationship. Even in moments of conflict, the goal is to find serenity through communication, empathy, and growth.

---


