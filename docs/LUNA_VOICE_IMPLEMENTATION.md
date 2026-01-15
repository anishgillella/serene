# Luna Voice Implementation - VAPI Migration

## Overview

This document covers the migration from LiveKit Agents to VAPI for Luna's voice capabilities, including all code changes, configuration requirements, and setup instructions.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Why VAPI?](#2-why-vapi)
3. [Code Changes](#3-code-changes)
4. [Environment Configuration](#4-environment-configuration)
5. [VAPI Console Setup](#5-vapi-console-setup)
6. [Testing](#6-testing)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Architecture Overview

### Before (LiveKit)
```
Frontend → LiveKit SDK → LiveKit Cloud → LiveKit Agent Server
                                              ↓
                                    Deepgram (STT) + ElevenLabs (TTS)
                                              ↓
                                         OpenRouter (LLM)
                                              ↓
                                      Backend (RAG tools)
```

**Problems:**
- Multiple services to configure (Deepgram, ElevenLabs, LiveKit)
- Agent server deployment and memory management
- Complex VAD (Voice Activity Detection) configuration
- Multiple API keys to manage
- Deepgram 401 authentication errors
- Agent spawning issues

### After (VAPI)
```
Frontend → VAPI Web SDK → VAPI Cloud (handles STT/TTS/LLM)
                              ↓
                    Backend Webhooks (RAG tools)
```

**Benefits:**
- Single SDK and API key
- Managed STT/TTS/LLM pipeline
- Built-in turn-taking and VAD
- No agent server to deploy
- Webhook-based tool execution

---

## 2. Why VAPI?

| Aspect | LiveKit + DIY | VAPI |
|--------|---------------|------|
| Setup Complexity | High (4+ services) | Low (1 service) |
| API Keys | 4+ (LiveKit, Deepgram, ElevenLabs, OpenRouter) | 1 |
| Agent Server | Self-managed | Managed |
| VAD Configuration | Manual tuning | Built-in |
| Debugging | Multiple logs | Single dashboard |
| Cost | ~$0.02-0.05/min + hosting | ~$0.05-0.10/min |

---

## 3. Code Changes

### 3.1 New Files Created

#### `/frontend/src/components/voice/VoiceCallModal.tsx`

Beautiful voice call modal with:
- Animated gradient orb visualization
- Real-time waveform display during speech
- Live transcript panel
- Mute/unmute controls
- Call duration timer
- Connection status indicators

```typescript
// Key features:
type CallStatus = 'idle' | 'connecting' | 'connected' | 'speaking' | 'listening' | 'ended' | 'error';

// VAPI event handling:
vapiRef.current.on('call-start', () => { /* ... */ });
vapiRef.current.on('speech-start', () => { /* ... */ });
vapiRef.current.on('speech-end', () => { /* ... */ });
vapiRef.current.on('message', (message) => { /* transcript handling */ });
vapiRef.current.on('volume-level', (level) => { /* waveform */ });
```

#### `/backend/app/routes/vapi_webhook.py`

Webhook handlers for VAPI events:
- `assistant-request`: Dynamic assistant configuration
- `function-call`: Tool execution
- `transcript`: Message logging
- `end-of-call-report`: Session cleanup

Implemented tools:
- `find_similar_conflicts`: Vector search for past conflicts
- `get_partner_perspective`: LLM-powered partner perspective generation

### 3.2 Files Modified

#### `/backend/app/main.py`
```python
# Added VAPI webhook router
from .routes import vapi_webhook
app.include_router(vapi_webhook.router)
```

#### `/frontend/package.json`
```json
{
  "dependencies": {
    "@vapi-ai/web": "^2.3.0"
  }
}
```

### 3.3 Files to Remove (Deprecated LiveKit Code)

The following LiveKit-related files can be removed after migration is complete:

**Frontend:**
```
/frontend/src/components/MediatorModal.tsx      # Old LiveKit modal (replaced by VoiceCallModal)
/frontend/src/components/MediatorContextPanel.tsx  # LiveKit context panel
```

**Backend - Agent Code (entire directory can be archived/removed):**
```
/backend/app/agents/luna/                       # LiveKit agent implementation
  ├── __init__.py
  ├── agent.py                                  # Main LiveKit agent
  ├── config.py                                 # Agent configuration
  ├── rag.py                                    # RAG functions (now in vapi_webhook.py)
  ├── tools.py                                  # Agent tools
  └── utils.py                                  # Agent utilities
/backend/app/agents/tools/mediator_tools.py    # Agent tools
/backend/start_agent.py                         # Agent launcher
/backend/cleanup_rooms.py                       # Room cleanup script
/backend/kill_zombies.sh                        # Process cleanup script
```

**Backend - Endpoints that can be removed from main.py:**
```python
# These endpoints are no longer needed with VAPI:
# - POST /api/token
# - POST /api/mediator/token
# - POST /api/dispatch-agent
```

**Note:** Keep the LiveKit code for now as reference, but it's no longer active. The VAPI webhook endpoints handle all voice functionality.

---

## 4. Environment Configuration

### Frontend (`.env`)

```env
# VAPI Configuration (Required)
VITE_VAPI_PUBLIC_KEY=your-vapi-public-key
VITE_VAPI_ASSISTANT_ID=your-assistant-id

# Remove or comment out:
# VITE_LIVEKIT_URL=wss://...
```

### Backend (`.env`)

```env
# Keep these for VAPI webhook tools
OPENROUTER_API_KEY=sk-or-v1-...
PINECONE_API_KEY=pcsk_...
VOYAGE_API_KEY=pa-...

# Optional: VAPI server key for API calls
VAPI_API_KEY=your-vapi-api-key
```

---

## 5. VAPI Console Setup

### Step 1: Create Account
Go to https://dashboard.vapi.ai and sign up.

### Step 2: Create Assistant

**Basic Settings:**
| Field | Value |
|-------|-------|
| Name | Luna - Relationship Mediator |
| First Message | Hey! I'm Luna. What's on your mind? |

**System Prompt:**
```
You are Luna, a relationship mediator who helps couples work through conflicts.

## Your Personality:
- Warm, casual, and real - like a close friend they trust
- Keep responses SHORT (2-3 sentences max for voice)
- Use natural phrases: "I hear you", "That's tough", "I get it"
- Validate feelings without being repetitive
- Be honest - gently call out behavior when needed

## Your Approach:
1. Listen and let them vent first
2. Validate their feelings naturally
3. Help them understand their partner's side
4. Suggest practical fixes
5. Be supportive but also help them grow

## Important Rules:
- NEVER use clinical therapy language
- Keep responses conversational and brief
- Be willing to push back gently
```

### Step 3: Configure Voice

| Setting | Value |
|---------|-------|
| Provider | ElevenLabs |
| Voice | Rachel (21m00Tcm4TlvDq8ikWAM) |
| Model | eleven_flash_v2_5 |
| Stability | 0.5 |
| Similarity Boost | 0.75 |

### Step 4: Configure Model

| Setting | Value |
|---------|-------|
| Provider | openai |
| Model | gpt-4o-mini |
| Temperature | 0.7 |
| Max Tokens | 250 |

### Step 5: Add Server URL (Webhook)

```
https://your-backend-url/api/vapi/webhook
```

### Step 6: Add Tools

**Tool 1: find_similar_conflicts**
```json
{
  "type": "function",
  "function": {
    "name": "find_similar_conflicts",
    "description": "Find similar past conflicts to identify patterns.",
    "parameters": {
      "type": "object",
      "properties": {
        "topic_keywords": {
          "type": "string",
          "description": "Keywords describing the conflict topic"
        }
      },
      "required": ["topic_keywords"]
    }
  },
  "server": {
    "url": "https://your-backend-url/api/vapi/tools/find_similar_conflicts"
  }
}
```

**Tool 2: get_partner_perspective**
```json
{
  "type": "function",
  "function": {
    "name": "get_partner_perspective",
    "description": "Get the partner's likely perspective based on their profile.",
    "parameters": {
      "type": "object",
      "properties": {
        "situation_description": {
          "type": "string",
          "description": "Description of the situation to analyze"
        }
      },
      "required": ["situation_description"]
    }
  },
  "server": {
    "url": "https://your-backend-url/api/vapi/tools/get_partner_perspective"
  }
}
```

### Step 7: Copy Keys

After creating the assistant:
1. Copy the **Public Key** → `VITE_VAPI_PUBLIC_KEY`
2. Copy the **Assistant ID** → `VITE_VAPI_ASSISTANT_ID`

---

## 6. Testing

### 6.1 Backend Webhook Test

```bash
# Test webhook endpoint
curl -X POST https://your-backend/api/vapi/webhook \
  -H "Content-Type: application/json" \
  -d '{"message": {"type": "status-update", "status": "started"}}'
```

### 6.2 Frontend Test

1. Add VAPI keys to `.env`
2. Navigate to PostFightSession page
3. Click "Talk to Luna" button
4. Grant microphone permission
5. Verify:
   - Connection establishes
   - Luna speaks first message
   - Transcript appears
   - Your speech is transcribed
   - Call can be ended

### 6.3 Tool Test

During a call, say something that triggers tool use:
- "Has this happened before?" → triggers `find_similar_conflicts`
- "What do you think [partner] is feeling?" → triggers `get_partner_perspective`

---

## 7. Troubleshooting

### "Voice service not initialized"
- Check `VITE_VAPI_PUBLIC_KEY` is set correctly
- Ensure the key is a public key (not private)

### "Assistant not configured"
- Check `VITE_VAPI_ASSISTANT_ID` is set correctly
- Verify assistant exists in VAPI dashboard

### No audio/microphone issues
- Ensure browser has microphone permission
- Check if using HTTPS (required for mic access)
- Try in Chrome (best WebRTC support)

### Tools not executing
- Verify webhook URL is publicly accessible
- Check backend logs for incoming requests
- Ensure tools are properly configured in VAPI console

### Call quality issues
- Check network connection
- VAPI uses WebRTC - ensure ports are not blocked
- Try reducing `max_tokens` for faster responses

---

## Migration Checklist

- [x] Create VAPI account
- [x] Create backend webhook routes
- [x] Create frontend VoiceCallModal component
- [x] Install VAPI Web SDK
- [ ] Configure assistant in VAPI console
- [ ] Add VAPI keys to frontend .env
- [ ] Update PostFightSession to use VoiceCallModal
- [ ] Remove old LiveKit code
- [ ] Test end-to-end voice flow
- [ ] Deploy and verify in production

---

## Related Files

| File | Description |
|------|-------------|
| `/frontend/src/components/voice/VoiceCallModal.tsx` | Voice call UI component |
| `/backend/app/routes/vapi_webhook.py` | Webhook handlers |
| `/docs/VAPI_MIGRATION.md` | Original migration notes |
| `/docs/LUNA_VOICE_IMPLEMENTATION.md` | This document |
