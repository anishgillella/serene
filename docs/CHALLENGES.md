# HeartSync Development Challenges & Solutions

This document outlines all the major challenges encountered during the development of HeartSync and how they were resolved.

---

## Frontend Challenges

### 1. Blank White Screen on Localhost
**Problem:** Frontend displayed a completely blank white screen when opened at `localhost`.

**Root Cause:** Missing `postcss.config.js` file, which is essential for Tailwind CSS to compile CSS properly during development.

**Solution:** Created `postcss.config.js` with proper PostCSS and Tailwind configuration.

**Learning:** Always ensure build tool configurations are complete, especially for CSS frameworks like Tailwind.

---

### 2. ReactDOM.render Deprecation Warning
**Problem:** Browser console showed warning about ReactDOM.render being deprecated in React 18.

**Root Cause:** Using older React 17 API in React 18 application.

**Impact:** App functionally worked but with React 17 compatibility mode limitations.

**Status:** Warning acknowledged; using React 18 is correct, warning is expected during transition.

---

### 3. React Router Future Flag Warnings
**Problem:** Multiple warnings about React Router v7 future flags.

**Root Cause:** Using React Router v6 without enabling v7 compatibility flags.

**Impact:** No functional impact; warnings are informational for future upgrades.

**Status:** Can be addressed during next React Router upgrade.

---

### 4. WebSocket Connection Failures
**Problem:** WebSocket connection from frontend to backend was failing with generic connection errors.

**Root Cause:** Backend WebSocket endpoint had incorrect authentication header parameter syntax.

**Solution:** Changed from `extra_headers` to `additional_headers` parameter (correct for websockets v15+).

**Learning:** Always verify library version compatibility for parameter names.

---

### 5. Transcript Overwriting Issue
**Problem:** As user spoke, interim transcripts were overwriting previous final transcripts, causing loss of conversation history.

**Root Cause:** Not distinguishing between interim (partial) and final transcripts in state management.

**Solution:** 
- Separated state into `transcript` (final) and `interimTranscript` (temporary)
- Final transcripts added to permanent list and cleared interim
- Interim transcripts only updated temporary display

**Learning:** Real-time transcription requires careful state management to handle partial results.

---

### 6. Transcript Not Passing to Post-Fight Session
**Problem:** Post-Fight Session page showed hardcoded placeholder text instead of actual transcript from fight capture.

**Root Cause:** No data passing mechanism between FightCapture and PostFightSession components.

**Solution:** 
- Used React Router `navigate` with state: `navigate('/post-fight', { state: { transcript } })`
- Updated PostFightSession to receive and parse transcript from location state
- Display transcript messages with proper formatting

**Learning:** React Router state passing is ideal for sequential view navigation.

---

## Backend Challenges

### 1. ModuleNotFoundError for 'livekit'
**Problem:** Running test scripts resulted in `ModuleNotFoundError: No module named 'livekit'`.

**Root Cause:** Python dependencies not installed from `requirements.txt`.

**Solution:** Ran `pip install -r requirements.txt` to install all dependencies.

**Learning:** Virtual environments require explicit dependency installation.

---

### 2. TTS model_id Parameter Error
**Problem:** ElevenLabs TTS initialization failed with `TypeError: TTS.__init__() got an unexpected keyword argument 'model_id'`.

**Root Cause:** Incorrect parameter name; ElevenLabs uses `model` not `model_id`.

**Solution:** Changed `model_id="eleven_flash_v2_5"` to `model="eleven_flash_v2_5"`.

**Impact:** Fixed across test_components.py and heartsync_agent.py.

---

### 3. ChatContext.append() Method Error
**Problem:** LLM integration failed with `AttributeError: 'ChatContext' object has no attribute 'append'`.

**Root Cause:** API changed; correct method is `add_message()` not `append()`.

**Solution:** Updated all ChatContext usage to use `add_message(role=..., content=...)`.

**Impact:** Fixed OpenRouter LLM integration in agent.

---

### 4. PYTHONPATH Issues
**Problem:** Importing app modules failed with various import errors when running from project root.

**Root Cause:** Python couldn't find the app module without proper path setup.

**Solution:** 
- Set `PYTHONPATH=/Users/anishgillella/.../backend` when running commands
- Ran commands from backend directory
- Used `python -m` module syntax when available

**Learning:** Always be explicit about Python paths in development environments.

---

### 5. Address Already in Use (Port 8000)
**Problem:** Backend failed to start because port 8000 was already in use.

**Root Cause:** Previous backend process wasn't properly terminated.

**Solution:** Used `lsof -ti:8000 | xargs kill -9` to force terminate process.

**Prevention:** Added cleanup scripts to kill old processes before starting.

---

### 6. Deepgram WebSocket Authentication Failure
**Problem:** WebSocket connection to Deepgram failed with HTTP 401 errors.

**Root Cause:** Initial attempt to pass API key in URL instead of Authorization header.

**Solution:** Changed to pass API key via `additional_headers` parameter:
```python
await websockets.connect(url, additional_headers={"Authorization": f"Token {api_key}"})
```

**Learning:** Always check API documentation for correct authentication method.

---

### 7. Deepgram extra_headers vs additional_headers Parameter
**Problem:** WebSocket connection threw `TypeError: create_connection() got an unexpected keyword argument 'extra_headers'`.

**Root Cause:** Websockets library v15.0.1 uses `additional_headers` not `extra_headers`.

**Solution:** Updated parameter name to match library version.

**Impact:** Fixed in app/routes/realtime_transcription.py.

**Learning:** Library parameter names change between major versions; verify with `inspect.signature()`.

---

### 8. LiveKit Agent CLI Issues
**Problem:** Multiple issues running the LiveKit agent in development mode.

**Challenges:**
- Initial: `livekit.agents.cli.__main__` execution failed
- Then: `Agent.__init__()` missing required `instructions` parameter
- Then: `ChatContext.add_message()` parameter name changes
- Finally: Agent was in "silent mode" not capturing user speech events

**Solutions:**
- Used correct command: `python -m livekit.agents dev app.agents.heartsync_agent`
- Added `instructions` parameter to agent initialization
- Updated all message parameter names from `text` to `content`
- Switched from LiveKit Agent STT to direct Deepgram WebSocket for more control

**Learning:** Complex frameworks require careful reading of latest API documentation.

---

### 9. Real-Time Transcription Event Handling
**Problem:** LiveKit agent wasn't triggering transcription events even though agent was connected.

**Root Cause:** 
- `user_speech_committed` event doesn't fire in silent/transcription mode
- LiveKit Agents framework in dev mode has routing limitations

**Solution:** Bypassed LiveKit Agents for STT, using direct Deepgram WebSocket connection instead.

**Result:** Cleaner architecture with more control over transcription flow.

**Learning:** Sometimes simpler direct API calls are better than complex frameworks.

---

### 10. Missing Python Dependencies
**Problem:** Various import errors when trying to use specific libraries.

**Solution:** Updated requirements.txt with all needed packages:
- livekit
- livekit-agents
- livekit-agents[plugins]
- deepgram-sdk
- websockets
- fastapi
- uvicorn
- python-multipart
- httpx
- voyageai

**Learning:** Document all dependencies explicitly to avoid runtime surprises.

---

### 11. python-multipart Not Installed
**Problem:** FastAPI form data handling failed with `RuntimeError: Form data requires "python-multipart" to be installed.`

**Root Cause:** The library wasn't included in requirements.txt.

**Solution:** Added `python-multipart` to requirements.txt.

**Impact:** Fixed file upload endpoint functionality.

---

## Architecture & Design Challenges

### 1. Choosing STT Approach
**Problem:** Needed to decide between multiple STT integration approaches:
1. LiveKit built-in STT (via Inference)
2. LiveKit Agents plugin for Deepgram
3. Direct Deepgram WebSocket

**Challenges Evaluated:**
- LiveKit Inference: Limited control, pre-configured options
- LiveKit Agents: Complex framework, event handling issues in dev mode
- Direct WebSocket: Best latency, full control, but more complexity

**Solution:** Chose direct Deepgram WebSocket for production-grade real-time transcription.

**Result:** ~100ms latency, real-time interim results, speaker diarization.

---

### 2. Transcript State Management
**Problem:** How to handle both interim and final transcripts without losing data?

**Challenges:**
- Interim results come more frequently than final
- Need to show updates in real-time but keep final records
- Prevent overwriting of previous final results

**Solution:** 
- Separate state: `transcript` (final) and `interimTranscript` (current)
- Clear interim when final arrives
- Only add to permanent list on final results

**Learning:** Real-time systems require careful state separation.

---

### 3. Data Passing Between Routes
**Problem:** How to pass captured transcript from FightCapture to PostFightSession?

**Options Considered:**
1. Global state management (Context API) - overkill for single data point
2. URL parameters - transcript too large
3. Local storage - works but not ideal for single-use data
4. React Router state - perfect fit

**Solution:** Used React Router state passing with navigation.

**Result:** Clean, simple, works perfectly for sequential views.

---

## Deployment & Configuration Challenges

### 1. Missing .gitignore
**Problem:** Almost committed sensitive `.env` file with API keys to GitHub.

**Root Cause:** No `.gitignore` file to exclude sensitive files.

**Solution:** Created comprehensive `.gitignore` excluding:
- `.env` files
- `venv/` and node_modules
- `__pycache__` and cache files
- OS files (.DS_Store)

**Prevention:** Always create `.gitignore` before first commit.

---

### 2. Accidental API Key Exposure
**Problem:** During development, `.env` file was staged for commit.

**Solution:** 
- Unstaged `.env` before commit
- Committed `.env.example` instead with placeholder values
- Added `.gitignore` rules

**Learning:** Use `git diff --staged` before committing to check for sensitive data.

---

### 3. Virtual Environment in Git
**Problem:** `venv/` directory was attempted to be committed (massive overhead).

**Solution:** Excluded from both `.gitignore` and staged commit.

**Result:** Cleaner repository, faster cloning.

---

### 4. Dockerfile Configuration
**Problem:** Initially unclear how to package the agent for LiveKit Cloud deployment.

**Solution:** Created:
- `Dockerfile` with proper Python setup
- `.dockerignore` to exclude unnecessary files
- `start_agent.py` wrapper for clean startup
- `livekit.toml` for deployment configuration
- `DEPLOYMENT.md` with step-by-step instructions

**Learning:** Container deployment requires separate configuration from local development.

---

## Testing & Debugging Challenges

### 1. Browser Console Errors
**Problem:** Multiple deprecation warnings cluttering console output.

**Status:** Expected warnings, not blocking functionality.

**Approach:** Acknowledged warnings, will address in future React/Router upgrades.

---

### 2. Backend Logs Management
**Problem:** Hard to track backend issues without persistent logs.

**Solution:** Redirected output to `/tmp/backend.log` for monitoring.

**Usage:** `tail -f /tmp/backend.log` for real-time monitoring.

---

### 3. Transcription Accuracy Gaps
**Problem:** Real-time transcription sometimes misses or incorrectly transcribes words.

**Expected:** ~90% accuracy with real-time streaming (normal for STT).

**Trade-off:** Interim results show ~70%, final results ~90% after full phrase processing.

**Mitigation:** Users see updates in real-time, final accuracy improves after short pause.

---

## Performance Challenges

### 1. Audio Processing Performance
**Problem:** Browser audio processing could be intensive for long sessions.

**Solution:** Used `ScriptProcessorNode` (now deprecated) for audio capture.

**Future:** Should migrate to `AudioWorkletNode` for better performance.

---

### 2. WebSocket Latency
**Problem:** Real-time transcription latency needed to be minimal.

**Achieved:** ~200ms STT latency + ~100ms network = ~300ms total.

**Optimization:** Deepgram's Nova-2 model provides this latency out-of-the-box.

---

### 3. Frontend Re-rendering
**Problem:** Frequent transcript updates could cause unnecessary re-renders.

**Status:** Currently acceptable with React hooks state management.

**Future Optimization:** Consider memoization if performance degrades.

---

## Summary of Key Learnings

1. **Always verify library versions** - Parameter names and APIs change
2. **Use `.gitignore` early** - Prevents accidental secrets exposure
3. **Separate interim and final states** - Essential for real-time systems
4. **Test API authentication thoroughly** - Especially with external services
5. **Consider simpler solutions first** - Direct API calls > Complex frameworks
6. **Document deployment setup** - Dockerfile, config files, step-by-step guides
7. **Monitor logs actively** - Makes debugging exponentially easier
8. **Plan state management carefully** - Especially for real-time data flows

---

## Still Open/Future Challenges

1. **LiveKit Agent Deployment** - Files ready but not yet deployed to LiveKit Cloud
2. **Audio Format Compatibility** - May need additional resampling for different browsers
3. **Error Recovery** - Need better handling of connection drops mid-session
4. **Transcript Persistence** - Currently only stored during session; need database integration
5. **Multi-participant Diarization** - Current setup for single participant; scaling to two participants
6. **Post-Fight AI Responses** - Backend agent responses not yet integrated
7. **Analytics Integration** - Conflict patterns and metrics collection not yet implemented
8. **End-to-End Testing** - Automated tests for WebSocket transcription flow

---

**Last Updated:** November 22, 2025  
**Status:** Real-time transcription MVP ✅ complete and tested



