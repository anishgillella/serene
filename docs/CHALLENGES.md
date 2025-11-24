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
- `backend/app/agents/mediator_agent.py` - Refactored async initialization
- `backend/app/services/pinecone_service.py` - Added error handling
- `backend/app/services/db_service.py` - Added error handling
- `backend/app/main.py` - Added `/api/dispatch-agent` endpoint
- `backend/livekit.toml` - Updated agent ID to `A_aPV984RTQvBw`

**Frontend:**
- `frontend/src/components/MediatorModal.tsx` - Added dispatch call and UX improvements

**Documentation:**
- `docs/CHALLENGES.md` - This document
- `.gemini/antigravity/brain/.../walkthrough.md` - Testing and verification guide



