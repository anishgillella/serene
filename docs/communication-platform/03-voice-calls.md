# Priority 3: Voice Calls

Real-time voice calls between partners with live transcription and optional recording.

## Overview

Voice calls are a major unlock for relationship intelligence:
- **Real-time conflict detection**: Identify escalation as it happens
- **Live intervention**: Luna can suggest de-escalation during the call
- **Full conversation capture**: Record and transcribe for later analysis
- **Natural communication**: Closer to how couples actually talk

## Why Voice Calls Are Critical

| Scenario | Text/Voice Msg | Voice Call |
|----------|----------------|------------|
| Heated argument | They switch to calling anyway | You capture it |
| Making up | Often done verbally | Full context captured |
| Daily check-ins | Fragmented messages | Rich, flowing conversation |
| Luna intervention | After the fact | Real-time |

## Tech Stack Options

### Option A: WebRTC (DIY)
| Pros | Cons |
|------|------|
| Free (no per-minute cost) | Complex to implement |
| Full control | Need STUN/TURN servers |
| Works in browser | NAT traversal issues |

### Option B: Twilio Voice
| Pros | Cons |
|------|------|
| Reliable, production-ready | $0.015/min per participant |
| Recording built-in | Dependency on third-party |
| PSTN support (real phone #s) | Less control |

### Option C: Agora / 100ms
| Pros | Cons |
|------|------|
| Optimized for real-time | Usage-based pricing |
| Good mobile SDKs | Smaller community than Twilio |
| Recording + transcription add-ons | |

### Recommendation

**Start with Agora or 100ms** for faster implementation, then consider WebRTC for cost optimization at scale.

For couples app with moderate usage (~100 couples, 30 min calls/day):
- Agora: ~$500/month
- Twilio: ~$1,350/month
- WebRTC: ~$50/month (TURN server costs)

## Architecture

```
┌─────────────────┐         ┌─────────────────┐
│   Partner A     │         │   Partner B     │
│   (Caller)      │         │   (Receiver)    │
└────────┬────────┘         └────────┬────────┘
         │                           │
         │    WebRTC / Agora SDK     │
         └───────────┬───────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │   Media Server        │
         │   (Agora / TURN)      │
         ├───────────────────────┤
         │   - Audio routing     │
         │   - Recording         │
         │   - Quality adapt     │
         └───────────┬───────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│ Recording       │    │ Live Stream     │
│ (S3)            │    │ (to Transcriber)│
└────────┬────────┘    └────────┬────────┘
         │                      │
         ▼                      ▼
┌─────────────────┐    ┌─────────────────┐
│ Post-call       │    │ Real-time       │
│ Analysis        │    │ Transcription   │
└─────────────────┘    │ + Analysis      │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Luna Intervention│
                       │ Engine           │
                       └─────────────────┘
```

## Database Schema

```sql
-- Calls table
CREATE TABLE calls (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id),
  caller_id UUID REFERENCES users(id),
  receiver_id UUID REFERENCES users(id),

  -- Timing
  initiated_at TIMESTAMPTZ DEFAULT NOW(),
  answered_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  duration_seconds INTEGER,

  -- Status
  status TEXT NOT NULL, -- 'ringing', 'active', 'ended', 'missed', 'declined'
  end_reason TEXT, -- 'completed', 'caller_hangup', 'receiver_hangup', 'failed'

  -- Recording
  recording_enabled BOOLEAN DEFAULT false,
  recording_url TEXT,
  recording_size_bytes INTEGER,

  -- Transcription
  transcript TEXT,
  transcript_segments JSONB,

  -- Analysis (post-call)
  analysis JSONB,
  /*
  {
    overall_sentiment: 0.3,
    escalation_points: [{time: 120, reason: "raised voices"}],
    topics_discussed: ["finances", "work stress"],
    speaking_ratio: {caller: 0.55, receiver: 0.45},
    interruptions: 12,
    luna_interventions: [{time: 180, type: "breathing_prompt"}]
  }
  */

  -- Real-time flags (updated during call)
  escalation_level FLOAT DEFAULT 0,
  luna_intervention_triggered BOOLEAN DEFAULT false
);

-- Call events (for detailed timeline)
CREATE TABLE call_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  call_id UUID REFERENCES calls(id),
  event_type TEXT NOT NULL, -- 'started', 'answered', 'muted', 'unmuted', 'escalation_detected', 'intervention', 'ended'
  event_data JSONB,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);
```

## API Endpoints

```
POST   /api/calls/initiate              Start a call
POST   /api/calls/:id/answer            Answer incoming call
POST   /api/calls/:id/decline           Decline call
POST   /api/calls/:id/end               End active call

GET    /api/calls/:id                   Get call details
GET    /api/calls/:id/recording         Get recording URL
GET    /api/calls/:id/transcript        Get transcript

POST   /api/calls/:id/toggle-recording  Enable/disable recording mid-call

WS     /api/calls/:id/events            Real-time call events
```

## Call Flow

### Initiating a Call

```typescript
// 1. Caller initiates
const call = await api.post('/calls/initiate', {
  receiver_id: partnerId,
  recording_enabled: true
});

// 2. Get Agora/WebRTC credentials
const { channelName, token, uid } = call.credentials;

// 3. Initialize call SDK
agoraClient.join(token, channelName, uid);

// 4. Notify receiver via push + WebSocket
// Backend sends push notification
// Receiver's app shows incoming call screen
```

### Answering a Call

```typescript
// On receiver's device
// 1. Show incoming call UI (triggered by push/websocket)

// 2. User answers
await api.post(`/calls/${callId}/answer`);

// 3. Join the call
const { channelName, token, uid } = callCredentials;
agoraClient.join(token, channelName, uid);

// 4. Both parties now connected
```

## Real-Time Transcription

Stream audio to transcription service during the call:

```python
# Using AssemblyAI or Deepgram for real-time transcription
import websockets
import json

async def stream_to_transcriber(audio_stream, call_id):
    async with websockets.connect(DEEPGRAM_WS_URL) as ws:
        async for audio_chunk in audio_stream:
            await ws.send(audio_chunk)

            # Receive transcription
            result = await ws.recv()
            transcript = json.loads(result)

            # Store segment
            await save_transcript_segment(call_id, transcript)

            # Analyze in real-time
            await analyze_segment(call_id, transcript)
```

## Real-Time Analysis & Intervention

```python
class CallAnalyzer:
    def __init__(self, call_id):
        self.call_id = call_id
        self.escalation_score = 0.0
        self.recent_segments = []

    async def analyze_segment(self, segment):
        self.recent_segments.append(segment)

        # Keep last 30 seconds of context
        self.recent_segments = self.recent_segments[-10:]

        # Analyze for escalation signals
        text = " ".join([s["text"] for s in self.recent_segments])

        signals = {
            "raised_voice": segment.get("volume", 0) > 0.8,
            "interruption": segment.get("is_interruption", False),
            "negative_words": count_negative_words(segment["text"]),
            "accusatory_language": detect_you_statements(segment["text"]),
        }

        # Update escalation score
        self.escalation_score = calculate_escalation(signals, self.escalation_score)

        # Trigger intervention if needed
        if self.escalation_score > 0.7:
            await self.trigger_intervention()

    async def trigger_intervention(self):
        # Options:
        # 1. Audio cue (gentle chime)
        # 2. Push notification to both phones
        # 3. Luna voice interjection (experimental)

        await notify_intervention(self.call_id, {
            "type": "gentle_reminder",
            "message": "Luna senses rising tension. Take a breath.",
            "escalation_level": self.escalation_score
        })
```

## Luna Intervention Types

| Level | Trigger | Intervention |
|-------|---------|--------------|
| Low (0.3-0.5) | Mild frustration detected | Subtle visual indicator |
| Medium (0.5-0.7) | Raised voices, interruptions | Gentle audio cue + notification |
| High (0.7-0.85) | Accusatory language, yelling | "Would you like to take a 2-minute break?" |
| Critical (0.85+) | Continuous escalation | Suggest ending call, offer cool-down resources |

## Recording & Storage

```python
# Post-call processing
async def process_call_recording(call_id, recording_url):
    # 1. Download recording
    audio = await download_recording(recording_url)

    # 2. Full transcription (higher quality than real-time)
    transcript = await transcribe_full(audio)

    # 3. Speaker diarization (who said what)
    diarized = await diarize_speakers(audio, transcript)

    # 4. Comprehensive analysis
    analysis = await analyze_call({
        "transcript": diarized,
        "audio": audio,
        "call_metadata": await get_call(call_id)
    })

    # 5. Store results
    await update_call(call_id, {
        "transcript": transcript,
        "transcript_segments": diarized,
        "analysis": analysis
    })

    # 6. Update relationship analytics
    await update_relationship_from_call(call_id, analysis)
```

## UI Components

### CallScreen

```tsx
<CallScreen
  callId={activeCallId}
  partner={partnerInfo}
  onEnd={handleEndCall}
  onMute={handleMute}
  onSpeaker={handleSpeaker}

  // Luna integration
  showLunaInterventions={true}
  onInterventionDismiss={handleDismissIntervention}
/>
```

### IncomingCallScreen

```tsx
<IncomingCallScreen
  caller={callerInfo}
  onAnswer={handleAnswer}
  onDecline={handleDecline}
/>
```

### CallHistoryItem

```tsx
<CallHistoryItem
  call={call}
  onPlayRecording={() => playRecording(call.recording_url)}
  onViewTranscript={() => viewTranscript(call.id)}
  onViewAnalysis={() => viewAnalysis(call.id)}
/>
```

## Implementation Steps

### Phase 1: Basic Calling
- [ ] Agora/100ms account setup
- [ ] Call initiation flow
- [ ] Push notification for incoming calls
- [ ] Basic call UI (active, incoming)
- [ ] End call / decline

### Phase 2: Recording
- [ ] Recording toggle
- [ ] Store recordings in S3
- [ ] Playback in call history
- [ ] Post-call transcription

### Phase 3: Real-Time Analysis
- [ ] Stream audio to transcriber
- [ ] Real-time escalation detection
- [ ] Intervention triggers
- [ ] Event logging

### Phase 4: Luna Integration
- [ ] Intervention UI (notifications, audio cues)
- [ ] Cool-down prompts
- [ ] Post-call insights in Luna chat

## Cost Estimation

| Component | Cost | Notes |
|-----------|------|-------|
| Agora (audio) | $0.99/1000 min | ~$100/mo for 100K min |
| Deepgram (real-time) | $0.0043/min | ~$430/mo for 100K min |
| Whisper (post-call) | ~$0.006/min | ~$600/mo for 100K min |
| Storage (R2) | ~$0.015/GB | Negligible |

**Total estimate: ~$1,000-1,500/month** for 100 active couples calling 30 min/day

Optimization: Only use real-time transcription, skip Whisper post-call.

## Privacy & Legal

- **Consent**: Both parties must consent to recording (show banner)
- **Notification**: Play tone at start if recording enabled
- **Deletion**: Users can delete call recordings
- **Encryption**: Audio encrypted at rest and in transit
- **Compliance**: GDPR, CCPA considerations for data retention
