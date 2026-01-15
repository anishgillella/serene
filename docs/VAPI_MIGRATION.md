# Luna VAPI Migration Guide

## Overview

This document provides the complete configuration needed to migrate Luna from LiveKit Agents to VAPI.

---

## 1. VAPI Console Configuration

### Create Assistant

Go to https://dashboard.vapi.ai and create a new assistant with the following settings:

### Basic Settings

| Field | Value |
|-------|-------|
| **Name** | Luna - Relationship Mediator |
| **First Message** | Hey! I'm Luna, your relationship mediator. What's on your mind? |
| **Voice** | ElevenLabs - Rachel (or similar warm female voice) |
| **Model** | Google Gemini 2.5 Flash (or GPT-4o-mini for lower cost) |

### System Prompt

```
You are Luna, a relationship mediator who helps couples work through conflicts. You talk like a close friend, not a therapist.

## Your Personality:
- Warm, casual, and real - like a close friend they trust
- Keep responses SHORT (2-3 sentences max for voice)
- Use natural phrases: "I hear you", "That's tough", "I get it"
- Validate their feelings without being repetitive
- Be honest - gently call out behavior when needed
- Help them see their partner's perspective without making them feel wrong

## Your Approach:
1. Listen and let them vent first
2. Validate their feelings naturally (vary your language)
3. Help them understand their partner's side
4. Suggest practical, real-world fixes
5. Be supportive but also help them grow

## Important Rules:
- NEVER use clinical therapy language
- Keep responses conversational and brief (this is voice, not text)
- Don't overuse filler words like "man", "bro", "dude"
- When they share something hard, acknowledge it simply: "That's really tough" or "I get why that hurt"
- Be willing to push back gently: "I hear you, but have you thought about how [partner] might see this?"

## Context Awareness:
When you have context about their relationship patterns, reference it naturally:
- "You mentioned this came up before..."
- "Based on what you've shared about [partner]..."
```

### Voice Settings

| Setting | Value |
|---------|-------|
| **Provider** | ElevenLabs |
| **Voice** | Rachel (21m00Tcm4TlvDq8ikWAM) |
| **Model** | eleven_flash_v2_5 |
| **Stability** | 0.5 |
| **Similarity Boost** | 0.75 |

### Transcriber Settings

| Setting | Value |
|---------|-------|
| **Provider** | Deepgram |
| **Model** | nova-2 |
| **Language** | en-US |
| **Smart Format** | true |

### Model Settings

| Setting | Value |
|---------|-------|
| **Provider** | openai (or google for Gemini) |
| **Model** | gpt-4o-mini or gemini-2.5-flash |
| **Temperature** | 0.7 |
| **Max Tokens** | 250 |

---

## 2. Server URL (Webhook) Configuration

Set your Server URL to receive tool calls:

```
https://your-backend-url/api/vapi/webhook
```

This endpoint will handle:
- Tool calls (find_similar_conflicts, get_partner_perspective)
- Conversation context injection
- Message logging

---

## 3. Tools Configuration

Add these tools in the VAPI dashboard:

### Tool 1: find_similar_conflicts

```json
{
  "type": "function",
  "function": {
    "name": "find_similar_conflicts",
    "description": "Find similar past conflicts to identify patterns. Use this when the user mentions a recurring issue or you want to show them this has happened before.",
    "parameters": {
      "type": "object",
      "properties": {
        "topic_keywords": {
          "type": "string",
          "description": "Keywords describing the current conflict topic (e.g., 'communication household chores feeling unheard')"
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

### Tool 2: get_partner_perspective

```json
{
  "type": "function",
  "function": {
    "name": "get_partner_perspective",
    "description": "Get the partner's likely perspective based on their personality profile. Use this to help the user understand how their partner might be feeling.",
    "parameters": {
      "type": "object",
      "properties": {
        "situation_description": {
          "type": "string",
          "description": "Description of the specific situation or behavior to analyze from the partner's perspective"
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

### Tool 3: get_context (for RAG injection)

```json
{
  "type": "function",
  "function": {
    "name": "get_context",
    "description": "INTERNAL: Automatically called at start to load relationship context. Do not call manually.",
    "parameters": {
      "type": "object",
      "properties": {},
      "required": []
    }
  },
  "server": {
    "url": "https://your-backend-url/api/vapi/tools/get_context"
  }
}
```

---

## 4. Assistant Overrides (Dynamic Configuration)

When starting a call from your frontend, pass these overrides to customize Luna for each session:

```javascript
const assistantOverrides = {
  // Dynamic first message with partner's name
  firstMessage: `Hey ${partnerAName}! I'm Luna. What's on your mind?`,

  // Pass conflict context via metadata
  metadata: {
    conflict_id: "38bd3199-79c9-4f98-92b0-4a1c08cf6c6b",
    relationship_id: "00000000-0000-0000-0000-000000000000",
    partner_a_name: "Adrian",
    partner_b_name: "Elara",
    session_id: "generated-session-id"
  },

  // Dynamic system prompt with partner names
  model: {
    messages: [
      {
        role: "system",
        content: `You are Luna, ${partnerAName}'s buddy who helps them think through relationship stuff with ${partnerBName}.

[Rest of system prompt with names injected...]`
      }
    ]
  }
};
```

---

## 5. Backend Webhook Implementation

Create a new route file: `/backend/app/routes/vapi_webhook.py`

### Required Endpoints:

1. **POST /api/vapi/webhook** - Main webhook for all VAPI events
2. **POST /api/vapi/tools/find_similar_conflicts** - Tool execution
3. **POST /api/vapi/tools/get_partner_perspective** - Tool execution
4. **POST /api/vapi/tools/get_context** - Context injection

### Webhook Event Types to Handle:

| Event | Action |
|-------|--------|
| `assistant-request` | Return dynamic assistant config with context |
| `function-call` | Execute tool and return result |
| `transcript` | Log messages to database |
| `end-of-call-report` | Save session summary |

---

## 6. Frontend Integration

Replace LiveKit SDK with VAPI Web SDK:

### Install

```bash
npm install @vapi-ai/web
```

### Usage

```typescript
import Vapi from '@vapi-ai/web';

const vapi = new Vapi('your-public-key');

// Start call with dynamic overrides
const startCall = async (conflictId: string, partnerAName: string, partnerBName: string) => {
  const call = await vapi.start('your-assistant-id', {
    firstMessage: `Hey ${partnerAName}! I'm Luna. What's on your mind?`,
    metadata: {
      conflict_id: conflictId,
      relationship_id: relationshipId,
      partner_a_name: partnerAName,
      partner_b_name: partnerBName
    }
  });

  return call;
};

// Event listeners
vapi.on('speech-start', () => {
  console.log('Assistant started speaking');
});

vapi.on('speech-end', () => {
  console.log('Assistant stopped speaking');
});

vapi.on('call-end', () => {
  console.log('Call ended');
});

vapi.on('error', (error) => {
  console.error('VAPI error:', error);
});

// End call
const endCall = () => {
  vapi.stop();
};
```

---

## 7. Environment Variables

Add to your `.env`:

```env
# VAPI Configuration
VAPI_API_KEY=your-vapi-api-key
VAPI_ASSISTANT_ID=your-assistant-id
VAPI_PUBLIC_KEY=your-public-key

# Keep existing keys for tools
OPENROUTER_API_KEY=sk-or-v1-...
PINECONE_API_KEY=pcsk_...
VOYAGE_API_KEY=pa-...
```

---

## 8. Migration Checklist

- [ ] Create VAPI account at https://vapi.ai
- [ ] Create Luna assistant with system prompt
- [ ] Configure voice (ElevenLabs Rachel)
- [ ] Configure transcriber (Deepgram)
- [ ] Add tools (find_similar_conflicts, get_partner_perspective)
- [ ] Implement backend webhook endpoints
- [ ] Update frontend to use VAPI SDK
- [ ] Test with dynamic partner names
- [ ] Test tool execution
- [ ] Test message logging
- [ ] Remove LiveKit code

---

## 9. Cost Comparison

| Service | LiveKit + DIY | VAPI |
|---------|---------------|------|
| Voice Minutes | Deepgram ($0.0043/min) + ElevenLabs ($0.11/1k chars) | ~$0.05-0.10/min (all-in) |
| Infrastructure | LiveKit Cloud ($0.004/min) + Agent hosting | Included |
| LLM | OpenRouter (Gemini) ~$0.001/1k tokens | Can use same or VAPI's LLM |
| Total | ~$0.02-0.05/min + hosting | ~$0.05-0.10/min |

VAPI is simpler but slightly more expensive. Worth it for reduced complexity.

---

## 10. Benefits of Migration

1. **No agent server to maintain** - Fully managed
2. **Simpler debugging** - VAPI dashboard with call logs
3. **Built-in turn-taking** - No VAD configuration needed
4. **Easier scaling** - No memory management
5. **Single SDK** - Instead of LiveKit + Deepgram + ElevenLabs
6. **Webhook-based tools** - Your existing backend works with minor changes
