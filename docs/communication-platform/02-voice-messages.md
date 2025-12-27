# Priority 2: Voice Messages

Tap-to-record audio messages with automatic transcription and emotional analysis.

## Overview

Voice messages add a richer communication layer:
- Captures tone, emotion, and nuance that text misses
- Lower friction than typing for longer thoughts
- Automatically transcribed for searchability and analysis
- Waveform visualization for playback

## Why Voice Messages Matter

| Aspect | Text | Voice |
|--------|------|-------|
| Emotion detection | Words only | Tone, pitch, pace, pauses |
| Sarcasm/irony | Often missed | Usually detectable |
| Frustration level | Explicit words needed | Audible in voice |
| Affection | Emojis, words | Warmth in voice |
| Effort | Low | Higher (feels more personal) |

## Tech Stack

| Component | Technology | Why |
|-----------|------------|-----|
| Recording | Web Audio API / MediaRecorder | Native browser/mobile support |
| Audio format | WebM (Opus) or M4A (AAC) | Good compression, wide support |
| Storage | S3 / Cloudflare R2 | Scalable, cheap, CDN delivery |
| Transcription | OpenAI Whisper | Best accuracy, handles accents |
| Emotion analysis | Custom model or API | Analyze audio features |

## User Flow

```
1. User holds "record" button
        │
        ▼
2. Audio captured via MediaRecorder
        │
        ▼
3. On release, audio uploaded to S3
        │
        ▼
4. Message record created with audio_url
        │
        ▼
5. Recipient receives message, can play audio
        │
        ▼
6. Background: Whisper transcribes audio
        │
        ▼
7. Background: Emotion analysis on audio
        │
        ▼
8. Message updated with transcript + analysis
```

## Database Schema

```sql
-- Extends messages table
ALTER TABLE messages ADD COLUMN audio_url TEXT;
ALTER TABLE messages ADD COLUMN audio_duration_seconds FLOAT;
ALTER TABLE messages ADD COLUMN transcript TEXT;
ALTER TABLE messages ADD COLUMN transcript_confidence FLOAT;
ALTER TABLE messages ADD COLUMN audio_emotion JSONB;
-- audio_emotion: {angry: 0.1, sad: 0.05, happy: 0.3, neutral: 0.55}

-- Or separate table for audio metadata
CREATE TABLE voice_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id UUID REFERENCES messages(id) UNIQUE,
  audio_url TEXT NOT NULL,
  duration_seconds FLOAT NOT NULL,
  file_size_bytes INTEGER,
  format TEXT, -- 'webm', 'm4a', 'wav'

  -- Transcription
  transcript TEXT,
  transcript_segments JSONB, -- [{start: 0.0, end: 1.5, text: "Hello"}, ...]
  transcript_language TEXT,
  transcript_confidence FLOAT,

  -- Audio analysis
  average_pitch FLOAT,
  pitch_variance FLOAT,
  speaking_rate FLOAT, -- words per minute
  pause_ratio FLOAT,   -- ratio of silence to speech
  volume_level FLOAT,

  -- Emotion from audio
  emotion_scores JSONB,
  dominant_emotion TEXT,

  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## API Endpoints

```
POST   /api/messages/voice              Upload voice message
GET    /api/messages/:id/audio          Get audio file URL (signed)
GET    /api/messages/:id/transcript     Get transcript

POST   /api/voice/transcribe            Manual transcription trigger
```

## Recording Implementation

### Web (React)

```typescript
const useVoiceRecorder = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mediaRecorder = new MediaRecorder(stream, {
      mimeType: 'audio/webm;codecs=opus'
    });

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    mediaRecorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
      setAudioBlob(blob);
      chunksRef.current = [];
      stream.getTracks().forEach(track => track.stop());
    };

    mediaRecorderRef.current = mediaRecorder;
    mediaRecorder.start();
    setIsRecording(true);
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  };

  return { isRecording, audioBlob, startRecording, stopRecording };
};
```

### Mobile (React Native)

```typescript
// Using expo-av or react-native-audio-recorder-player
import { Audio } from 'expo-av';

const startRecording = async () => {
  await Audio.requestPermissionsAsync();
  await Audio.setAudioModeAsync({
    allowsRecordingIOS: true,
    playsInSilentModeIOS: true,
  });

  const { recording } = await Audio.Recording.createAsync(
    Audio.RecordingOptionsPresets.HIGH_QUALITY
  );
  setRecording(recording);
};

const stopRecording = async () => {
  await recording.stopAndUnloadAsync();
  const uri = recording.getURI();
  // Upload uri to backend
};
```

## Transcription Pipeline

```python
import openai
from pathlib import Path

async def transcribe_voice_message(message_id: str, audio_url: str):
    # 1. Download audio file
    audio_path = await download_audio(audio_url)

    # 2. Transcribe with Whisper
    with open(audio_path, "rb") as audio_file:
        response = await openai.Audio.atranscribe(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",  # Includes timestamps
            language="en"  # Or detect automatically
        )

    # 3. Extract results
    transcript = response["text"]
    segments = response["segments"]  # Word-level timestamps
    language = response["language"]

    # 4. Update database
    await update_voice_message(message_id, {
        "transcript": transcript,
        "transcript_segments": segments,
        "transcript_language": language,
        "transcript_confidence": calculate_confidence(segments)
    })

    # 5. Trigger text analysis on transcript
    await analyze_message_content(message_id, transcript)

    return transcript
```

## Audio Emotion Analysis

Analyze the audio signal itself (not just words):

```python
import librosa
import numpy as np

async def analyze_audio_emotion(audio_path: str):
    # Load audio
    y, sr = librosa.load(audio_path)

    # Extract features
    features = {
        # Pitch analysis
        "pitch_mean": extract_pitch_mean(y, sr),
        "pitch_variance": extract_pitch_variance(y, sr),

        # Energy/volume
        "rms_energy": np.mean(librosa.feature.rms(y=y)),

        # Speaking rate (from transcript timing)
        "speaking_rate": calculate_speaking_rate(transcript_segments),

        # Pause analysis
        "pause_ratio": calculate_pause_ratio(y, sr),

        # Spectral features (timbre)
        "spectral_centroid": np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)),
        "mfcc": np.mean(librosa.feature.mfcc(y=y, sr=sr), axis=1).tolist()
    }

    # Classify emotion (using trained model or heuristics)
    emotion_scores = classify_emotion(features)

    return {
        "features": features,
        "emotion_scores": emotion_scores,
        "dominant_emotion": max(emotion_scores, key=emotion_scores.get)
    }

def classify_emotion(features):
    """
    Simple heuristic-based classification.
    For production, use a trained model (e.g., speech emotion recognition model).
    """
    scores = {"neutral": 0.5, "happy": 0.0, "sad": 0.0, "angry": 0.0, "anxious": 0.0}

    # High pitch variance + high energy = excited/angry
    if features["pitch_variance"] > threshold and features["rms_energy"] > threshold:
        scores["angry"] += 0.3
        scores["neutral"] -= 0.2

    # Slow speaking rate + low energy = sad
    if features["speaking_rate"] < threshold and features["rms_energy"] < threshold:
        scores["sad"] += 0.3
        scores["neutral"] -= 0.2

    # Many pauses + varying pitch = anxious
    if features["pause_ratio"] > threshold:
        scores["anxious"] += 0.2

    # Normalize
    total = sum(scores.values())
    return {k: v/total for k, v in scores.items()}
```

## UI Components

### VoiceRecordButton

```tsx
// Hold-to-record button with waveform visualization
<VoiceRecordButton
  onRecordingComplete={(audioBlob, duration) => {
    sendVoiceMessage(audioBlob, duration);
  }}
  maxDuration={120} // 2 minutes max
/>
```

### VoiceMessageBubble

```tsx
// Playback component
<VoiceMessageBubble
  audioUrl={message.audio_url}
  duration={message.audio_duration_seconds}
  transcript={message.transcript}
  isPlaying={currentlyPlaying === message.id}
  onPlay={() => playAudio(message.id)}
  onPause={() => pauseAudio()}
  waveformData={message.waveform} // Pre-computed or generated
/>
```

### Waveform Visualization

```tsx
// Show audio waveform during recording and playback
import { AudioVisualizer } from './AudioVisualizer';

// During recording: real-time waveform
// During playback: static waveform with progress indicator
```

## Storage Considerations

| Duration | Approx Size (Opus) | Monthly Cost (R2) |
|----------|-------------------|-------------------|
| 10 sec | ~20 KB | $0.00001 |
| 1 min | ~120 KB | $0.00006 |
| 5 min | ~600 KB | $0.0003 |

With 1000 voice messages/day avg 30 sec each:
- Storage: ~1.8 GB/month
- Cost: < $0.03/month (R2 free tier covers this)

## Implementation Steps

### Phase 1: Basic Voice Messages
- [ ] Audio recording component (web + mobile)
- [ ] Upload to S3/R2
- [ ] Playback component
- [ ] Duration display

### Phase 2: Transcription
- [ ] Whisper integration
- [ ] Async transcription pipeline
- [ ] Display transcript below audio
- [ ] Searchable transcripts

### Phase 3: Audio Analysis
- [ ] Extract audio features (librosa)
- [ ] Emotion classification
- [ ] Speaking pattern analysis
- [ ] Store analysis results

### Phase 4: Insights
- [ ] "Voice message sentiment over time"
- [ ] "Tone changes during conversations"
- [ ] Luna insights from voice patterns

## Privacy Considerations

- Audio files should be encrypted at rest
- Transcription happens server-side (or on-device for privacy)
- Users can delete voice messages (cascades to audio file deletion)
- Clear data retention policy (e.g., audio deleted after X days, transcript kept)
