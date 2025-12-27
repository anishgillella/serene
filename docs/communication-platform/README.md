# Communication Platform Documentation

Luna's built-in communication platform enables couples to message, call, and share media directly within the app. All communication is analyzed in real-time to provide relationship insights and enable Luna to intervene when needed.

## Priority Order

| Priority | Feature | Status | Doc |
|----------|---------|--------|-----|
| 1 | Text Messaging | Planned | [01-text-messaging.md](./01-text-messaging.md) |
| 2 | Voice Messages | Planned | [02-voice-messages.md](./02-voice-messages.md) |
| 3 | Voice Calls | Planned | [03-voice-calls.md](./03-voice-calls.md) |
| 4 | Video Calls | Planned | [04-video-calls.md](./04-video-calls.md) |
| 5 | Photo/Video Sharing | Planned | [05-media-sharing.md](./05-media-sharing.md) |

## Why Build Native Communication?

Instead of trying to integrate with iMessage, WhatsApp, Instagram, etc., we build communication directly into Luna:

- **Full data access**: Every message, call, and shared moment is captured
- **Real-time analysis**: Detect escalation as it happens
- **Luna can intervene**: "I notice tension rising, want me to help?"
- **Consistent experience**: Same on iOS and Android
- **Privacy**: End-to-end encryption, couples own their data

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Mobile/Web App                        │
├─────────────────────────────────────────────────────────┤
│  Text Chat  │  Voice Msg  │  Calls  │  Video  │  Media  │
└──────┬──────┴──────┬──────┴────┬────┴────┬────┴────┬────┘
       │             │           │         │         │
       ▼             ▼           ▼         ▼         ▼
┌─────────────────────────────────────────────────────────┐
│                   Real-time Layer                        │
│            (Supabase Realtime / WebSocket)              │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   Analysis Pipeline                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ Transcribe  │  │   Analyze   │  │  Store/Index    │  │
│  │  (Whisper)  │→ │  (Claude)   │→ │  (PostgreSQL)   │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                 Relationship Insights                    │
│         (Patterns, Triggers, Health Score)              │
└─────────────────────────────────────────────────────────┘
```

## Data Captured

| Channel | Raw Data | Derived Insights |
|---------|----------|------------------|
| Text | Messages, timestamps, read receipts | Tone, triggers, response time patterns |
| Voice Message | Audio file, transcript | Emotion, frustration, affection in voice |
| Voice Call | Full audio, transcript | Real-time conflict detection, interruptions |
| Video Call | Audio + video stream | Facial expressions, body language |
| Media | Photos, videos shared | Sharing frequency, content categories |
