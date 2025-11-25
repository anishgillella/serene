# Voice Agent Integration Challenges

This document outlines the major challenges encountered while integrating the LiveKit voice agent ("Luna") with the Serene application, and how each was resolved.

---

## Challenge 1: Agent Identity Issues

### Problem
The voice agent was appearing in LiveKit with a generic ID like `agent-AJ_Agv8NC4ysLtt` instead of the friendly name "Luna". This made it confusing for users and difficult to identify the agent in logs and the UI.

### Root Cause
The `WorkerOptions` in `start_agent.py` did not include the `agent_name` parameter, so LiveKit was auto-generating a default identity.

### Solution
Added `agent_name="Luna"` to the `WorkerOptions` in `start_agent.py`:
```python
cli.run_app(WorkerOptions(entrypoint_fnc=router_entrypoint, agent_name="Luna"))
```

**Files Modified:**
- `backend/start_agent.py`

---

## Challenge 2: Agent Connection but No Speech

### Problem
The agent would successfully connect to the LiveKit room but would not speak. The connection appeared successful, but no audio output was produced.

### Root Cause
The agent's `mediator_entrypoint` function was blocking on slow database/Pinecone operations during initialization. Specifically, it was trying to fetch conflict context (transcript, analysis, repair plans) **before** connecting to the room, which could take 10+ seconds. This caused the agent to timeout or fail to initialize properly.

### Solution
Refactored the entrypoint to:
1. **Connect to the room first** using `session.start()`
2. **Fetch context asynchronously** after connection
3. **Update agent instructions dynamically** with the retrieved context
4. Added a **10-second timeout** for context retrieval to prevent indefinite blocking
5. Added comprehensive logging to trace execution flow

**Files Modified:**
- `backend/app/agents/mediator_agent.py` (lines 456-499)

**Key Code Change:**
```python
# Start session FIRST
await session.start(room=ctx.room, agent=agent, ...)

# THEN fetch context asynchronously
try:
    context = await asyncio.wait_for(
        retrieve_conflict_context(conflict_id),
        timeout=10.0
    )
    # Update instructions dynamically
    agent.instructions = f"{agent.instructions}\n\n{context}"
except asyncio.TimeoutError:
    logger.warning("⚠️ Context retrieval timed out")
```

---

## Challenge 3: Missing LiveKit Plugin Dependencies

### Problem
When attempting to restart the agent, it crashed with:
```
ModuleNotFoundError: No module named 'livekit.plugins'
```

### Root Cause
The LiveKit agent requires additional plugin packages for STT (Deepgram), LLM (OpenAI), TTS (ElevenLabs), and noise cancellation, which were not installed.

### Solution
Installed the required LiveKit plugins:
```bash
pip install livekit-plugins-openai livekit-plugins-elevenlabs livekit-plugins-silero livekit-plugins-noise-cancellation
```

**Files Modified:**
- None (dependency installation only)

---

## Challenge 4: Service Initialization Crashes

### Problem
If Pinecone or the database failed to connect during agent startup, the entire agent would crash, preventing it from running at all.

### Root Cause
The `PineconeService` and `DatabaseService` were initialized at the module level without error handling. Any connection failure would raise an exception and crash the import.

### Solution
Wrapped service initialization in `try-except` blocks:

**Pinecone Service:**
```python
try:
    self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    self.index = self.pc.Index(self.index_name)
except Exception as e:
    logger.error(f"❌ Failed to connect to Pinecone: {e}")
    self.index = None
```

Added safety checks before using services:
```python
if not self.index:
    logger.warning("⚠️ Pinecone index not initialized")
    return None
```

**Files Modified:**
- `backend/app/services/pinecone_service.py`
- `backend/app/services/db_service.py`

---

## Challenge 5: Agent Dispatch Configuration

### Problem
The agent was running and registered with LiveKit Cloud, but it would not join rooms automatically. Users had to manually dispatch the agent using the CLI command:
```bash
lk dispatch create --room mediator-CONFLICT_ID --agent-name Luna
```

### Root Cause
LiveKit Cloud requires a **Dispatch Rule** to be configured in the dashboard to automatically assign agents to rooms matching a specific pattern (e.g., `mediator-*`). This configuration was missing.

### Solution (Attempt 1 - Manual Configuration)
Attempted to configure the dispatch rule in the LiveKit Cloud dashboard, but the user could not locate the setting.

### Solution (Attempt 2 - Programmatic Dispatch)
Implemented a programmatic solution that bypasses the need for dashboard configuration:

1. **Backend:** Added `/api/dispatch-agent` endpoint that explicitly dispatches the agent to a room using the LiveKit Server SDK
2. **Frontend:** Updated `MediatorModal.tsx` to call this endpoint immediately after connecting to the room

**Backend Implementation:**
```python
@app.post("/api/dispatch-agent")
async def dispatch_agent(request: dict = Body(...)):
    room_name = request.get("room_name")
    agent_name = request.get("agent_name", "Luna")
    
    lkapi = api.LiveKitAPI(
        settings.LIVEKIT_URL,
        settings.LIVEKIT_API_KEY,
        settings.LIVEKIT_API_SECRET
    )
    
    try:
        req = api.CreateAgentDispatchRequest(
            room=room_name,
            agent_name=agent_name
        )
        dispatch = await lkapi.agent_dispatch.create_dispatch(req)
        return {"success": True, "dispatch_id": dispatch.id}
    finally:
        await lkapi.aclose()
```

**Frontend Implementation:**
```typescript
// After connecting to room
await fetch(`${API_BASE_URL}/api/dispatch-agent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        room_name: `mediator-${conflictId}`,
        agent_name: 'Luna'
    })
});
```

**Files Modified:**
- `backend/app/main.py` (added `/api/dispatch-agent` endpoint)
- `frontend/src/components/MediatorModal.tsx` (added dispatch call)
- `backend/livekit.toml` (updated agent ID to `A_aPV984RTQvBw`)

---

## Challenge 6: SDK Import Errors

### Problem
The initial implementation of the dispatch endpoint failed with:
```
ImportError: cannot import name 'AgentDispatchService' from 'livekit.api'
```

### Root Cause
The LiveKit Python SDK does not expose `AgentDispatchService` as a standalone class. Instead, it's accessed through the `LiveKitAPI` client's `agent_dispatch` property.

### Solution
Changed from attempting to import a non-existent class to using the correct API pattern:

**Before (Incorrect):**
```python
from livekit.api import AgentDispatchService
service = AgentDispatchService(url, key, secret)
```

**After (Correct):**
```python
from livekit import api
lkapi = api.LiveKitAPI(url, key, secret)
dispatch = await lkapi.agent_dispatch.create_dispatch(req)
```

**Files Modified:**
- `backend/app/main.py`

---

## Challenge 7: Poor User Experience During Agent Join

### Problem
There was an 11-second delay between the user connecting to the room and the agent joining. During this time, the UI showed no feedback, making it appear as if nothing was happening.

### Root Cause
The dispatch process takes time (network request + agent startup), but the UI provided no visual indication that the agent was being summoned.

### Solution
Added UX improvements to the frontend:

1. **Status Indicator:** Added a pulsing "✨ Summoning Luna..." badge that appears while waiting for the agent
2. **Friendly Logs:** Changed participant join messages from `agent-AJ_Agv8NC4ysLtt joined` to `Luna joined`

**Implementation:**
```typescript
const [isAgentJoining, setIsAgentJoining] = useState(false);

// Set to true when dispatching
setIsAgentJoining(true);

// Set to false when agent joins
room.on(RoomEvent.ParticipantConnected, (participant) => {
    const isAgent = participant.identity.startsWith('agent-') || 
                    participant.name === 'Luna';
    const displayName = isAgent ? 'Luna' : participant.identity;
    
    if (isAgent) {
        setIsAgentJoining(false);
    }
    
    addTranscriptEntry('system', `${displayName} joined`);
});
```

**Files Modified:**
- `frontend/src/components/MediatorModal.tsx`

---

## Challenge 8: ElevenLabs TTS Connection Errors

### Problem
TTS was failing with "connection closed" errors. Agent couldn't speak.

### Root Cause
ElevenLabs plugin expects `ELEVEN_API_KEY` environment variable, but code was using `ELEVENLABS_API_KEY`.

### Solution
Set `ELEVEN_API_KEY` from `ELEVENLABS_API_KEY` at module level before TTS initialization.

**Files Modified:**
- `backend/app/agents/mediator_agent.py`

---

## Challenge 9: Multiple Agent Processes

### Problem
Two agents were responding simultaneously, causing confusion.

### Root Cause
Both AgentServer auto-join and explicit dispatch endpoint were triggering agent joins.

### Solution
Removed explicit dispatch call, relying solely on AgentServer auto-join pattern. Added deduplication logic to prevent duplicate joins.

**Files Modified:**
- `frontend/src/components/MediatorModal.tsx`

---

## Challenge 10: Agent Not Receiving Transcript Context

### Problem
Agent said "I don't have access to transcript details" for historical conflicts.

### Root Cause
Transcript chunks weren't stored in Pinecone for older conflicts. Only full transcripts existed.

### Solution
Added fallback: if chunks not found, fetch full transcript, chunk on-the-fly, store chunks in Pinecone, then use for context.

**Files Modified:**
- `backend/app/agents/mediator_agent.py`

---

## Challenge 11: Agent Still Responding After Disconnect

### Problem
Agent continued responding after user closed modal or ended call.

### Root Cause
Frontend wasn't properly disconnecting from LiveKit room, and agent session wasn't closing.

### Solution
Added explicit `room.disconnect()` and `session.aclose()` in cleanup. Ensured local tracks are stopped before disconnect.

**Files Modified:**
- `frontend/src/components/MediatorModal.tsx`
- `backend/app/agents/mediator_agent.py`

---

## Challenge 12: View Analysis/Repair Plan Buttons Not Working

### Problem
Buttons showed no results when clicked.

### Root Cause
Field name mismatch (`action_steps` vs `steps`) and missing structured output configuration.

### Solution
Fixed field names, ensured Pydantic structured output with GPT-4o-mini via OpenRouter.

**Files Modified:**
- `backend/app/routes/post_fight.py`
- `backend/app/services/llm_service.py`

---

## Challenge 13: Backend Hanging on Conflict History

### Problem
API endpoint hung indefinitely when loading conflict history.

### Root Cause
PostgreSQL connection blocking event loop with no timeout.

### Solution
Added `connect_timeout=5` to database connection, wrapped queries in `run_in_threadpool`, added `asyncio.wait_for` with 10s timeout.

**Files Modified:**
- `backend/app/services/db_service.py`
- `backend/app/main.py`

---

## Challenge 14: Analysis Generation Too Slow

### Problem
Analysis generation took 15+ seconds, blocking UI.

### Root Cause
Sending full transcript to LLM, large RAG context, synchronous storage operations.

### Solution
Used RAG context instead of full transcript, reduced chunk counts (top-7), parallelized storage with BackgroundTasks, reduced `max_tokens` to 1500.

**Files Modified:**
- `backend/app/routes/post_fight.py`
- `backend/app/services/transcript_rag.py`
- `backend/app/services/llm_service.py`

---

## Challenge 15: RAG Context Too Small

### Problem
RAG context was only 62 characters instead of expected ~3000.

### Root Cause
After reranking, code was reading text from Pinecone metadata (truncated) instead of full candidate text.

### Solution
Use full text from `candidate['text']` dictionary instead of `chunk.metadata.get("text")`.

**Files Modified:**
- `backend/app/services/transcript_rag.py`

---

## Challenge 16: Speaker Labels Wrong

### Problem
Real-time transcription showed "Boyfriend/Girlfriend" instead of "Adrian Malhotra/Elara Voss".

### Root Cause
Speaker name mapping functions used generic labels.

### Solution
Updated `get_speaker_name` to map to "Adrian Malhotra" and "Elara Voss". Updated frontend ParticipantBadge components.

**Files Modified:**
- `backend/app/routes/realtime_transcription.py`
- `frontend/src/pages/FightCapture.tsx`

---

## Challenge 17: Transcript Not Found Errors

### Problem
404 errors when generating analysis for conflicts stored in database but not Pinecone.

### Root Cause
Supabase RLS blocking access, no db_service fallback.

### Solution
Added db_service fallback (direct PostgreSQL connection bypasses RLS) before Supabase fallback.

**Files Modified:**
- `backend/app/routes/post_fight.py`

---

## Challenge 18: Analysis/Repair Plans Not Cached

### Problem
Clicking "View Analysis" regenerated analysis instead of retrieving cached version.

### Root Cause
No retrieval logic - endpoints always generated new analysis.

### Solution
Added `get_conflict_analysis()` and `get_repair_plans()` methods. Endpoints now check for existing results first, retrieve from S3 if found, generate only if missing.

**Files Modified:**
- `backend/app/services/db_service.py`
- `backend/app/routes/post_fight.py`

---

## Challenge 19: Duplicate Analysis Storage

### Problem
Attempting to store analysis twice caused database errors.

### Root Cause
No upsert logic - inserts failed on duplicates.

### Solution
Added `ON CONFLICT DO UPDATE` logic to `create_conflict_analysis()` and `create_repair_plan()` methods.

**Files Modified:**
- `backend/app/services/db_service.py`

---

## Summary

The voice agent integration faced several interconnected challenges across multiple sessions:

### Session 1: Initial Setup & Identity
1. **Identity & Branding:** Fixed by configuring `agent_name="Luna"` in `WorkerOptions`
2. **Connection & Speech:** Resolved by refactoring async initialization to connect before fetching context
3. **Dependencies:** Installed missing LiveKit plugin packages (`livekit-plugins-openai`, `livekit-plugins-elevenlabs`, `livekit-plugins-silero`, `livekit-plugins-noise-cancellation`)

### Session 2: Reliability & Dispatch
4. **Resilience:** Added error handling for Pinecone and database service failures
5. **Dispatch Configuration:** Discovered LiveKit Cloud requires dispatch rules that were difficult to configure via dashboard
6. **Programmatic Dispatch:** Implemented `/api/dispatch-agent` endpoint to bypass dashboard configuration
7. **SDK Usage:** Corrected API usage to use `LiveKitAPI.agent_dispatch.create_dispatch()` instead of non-existent `AgentDispatchService` class

### Session 3: User Experience
8. **UX Feedback:** Added "✨ Summoning Luna..." status indicator during the 11-second agent join delay
9. **Friendly Logs:** Changed participant join messages from raw agent IDs to "Luna joined"

### Session 4: TTS & Agent Reliability
10. **TTS Errors:** Fixed ElevenLabs API key configuration
11. **Multiple Agents:** Removed duplicate dispatch calls, added deduplication
12. **Transcript Context:** Added fallback to chunk transcripts on-the-fly
13. **Agent Disconnect:** Fixed cleanup to properly close sessions

### Session 5: Analysis & Repair Plans
14. **Button Functionality:** Fixed field names and structured output
15. **Backend Hanging:** Added timeouts and thread pool execution
16. **Slow Generation:** Optimized with RAG context and BackgroundTasks
17. **Small Context:** Fixed text extraction from candidates

### Session 6: Data & Storage
18. **Speaker Labels:** Updated to use "Adrian Malhotra" and "Elara Voss"
19. **Transcript Retrieval:** Added db_service fallback for RLS bypass
20. **Caching:** Implemented retrieval before generation
21. **Duplicates:** Added upsert logic for analysis/repair plans

### Key Learnings

1. **Async Operations:** External service calls (Pinecone, database) should never block the agent's connection to LiveKit
2. **Graceful Degradation:** Services should fail gracefully with logging rather than crashing the entire agent
3. **Programmatic Control:** When cloud dashboard configuration is unclear or unavailable, programmatic API calls provide a reliable alternative
4. **User Feedback:** Even short delays (10-15 seconds) need visual feedback to prevent user confusion
5. **SDK Documentation:** Always verify class/method names in the actual SDK rather than assuming based on naming patterns

### Final Architecture

The final solution ensures that Luna:
- ✅ Reliably joins rooms via programmatic dispatch
- ✅ Speaks immediately upon connection (context loaded asynchronously)
- ✅ Provides clear visual feedback during connection
- ✅ Gracefully handles service failures
- ✅ Appears with a friendly name ("Luna") instead of a generated ID

### Files Modified (Complete List)

**Backend:**
- `backend/start_agent.py` - Added agent name configuration
- `backend/app/agents/mediator_agent.py` - Refactored async initialization, TTS config, transcript fallback, session cleanup
- `backend/app/services/pinecone_service.py` - Added error handling
- `backend/app/services/db_service.py` - Added error handling, retrieval methods, upsert logic
- `backend/app/services/transcript_rag.py` - Fixed text extraction, optimized chunk counts
- `backend/app/services/llm_service.py` - Structured output, reduced max_tokens
- `backend/app/routes/post_fight.py` - Fixed field names, added caching, BackgroundTasks, db_service fallback
- `backend/app/routes/realtime_transcription.py` - Updated speaker names
- `backend/app/main.py` - Added `/api/dispatch-agent` endpoint, timeouts
- `backend/livekit.toml` - Updated agent ID to `A_aPV984RTQvBw`

**Frontend:**
- `frontend/src/components/MediatorModal.tsx` - Added dispatch call, UX improvements, proper disconnect
- `frontend/src/pages/FightCapture.tsx` - Updated speaker labels

**Documentation:**
- `docs/CHALLENGES.md` - This document
- `.gemini/antigravity/brain/.../walkthrough.md` - Testing and verification guide




