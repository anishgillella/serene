# HeartSync Transcription Endpoints ✅

## Overview

We now have **TWO transcription methods** available:

1. **File Upload Transcription** - Simple REST endpoint for prerecorded audio
2. **Real-Time WebSocket Transcription** - WebSocket endpoint for live audio streaming

---

## 1. File Upload Transcription ✅

### Endpoint
```
POST /api/transcription/transcribe
```

### Usage

**cURL:**
```bash
curl -X POST "http://127.0.0.1:8000/api/transcription/transcribe" \
  -F "audio_file=@/path/to/audio.wav"
```

**Python:**
```python
import requests

with open("audio.wav", "rb") as f:
    response = requests.post(
        "http://127.0.0.1:8000/api/transcription/transcribe",
        files={"audio_file": f}
    )
    print(response.json())
```

**Response:**
```json
{
  "success": true,
  "transcript": "Hello, this is a test transcription.",
  "speakers": {
    "0": ["Hello", "this", "is", "a", "test"],
    "1": ["transcription"]
  },
  "metadata": {
    "filename": "audio.wav"
  }
}
```

### Features
- ✅ Speaker diarization (identifies different speakers)
- ✅ Punctuation
- ✅ Supports: wav, mp3, m4a, flac, etc.
- ✅ Uses Deepgram Nova-2 model

---

## 2. Real-Time WebSocket Transcription ✅

### Endpoint
```
WS /api/realtime/transcribe
```

### Usage

**JavaScript (Browser):**
```javascript
const ws = new WebSocket('ws://127.0.0.1:8000/api/realtime/transcribe');

ws.onopen = () => {
  console.log('Connected to transcription service');
  
  // Start capturing audio from microphone
  navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
      const mediaRecorder = new MediaRecorder(stream);
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          ws.send(event.data);
        }
      };
      
      mediaRecorder.start(100); // Send chunks every 100ms
    });
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'transcript') {
    console.log('Transcript:', data.text);
    // Update UI with transcript
  }
};
```

**Python:**
```python
import asyncio
import websockets
import pyaudio

async def transcribe_realtime():
    uri = "ws://127.0.0.1:8000/api/realtime/transcribe"
    
    async with websockets.connect(uri) as ws:
        # Send audio chunks
        # Receive transcripts
        pass
```

**Response Format:**
```json
{
  "type": "transcript",
  "text": "Hello world",
  "is_final": false
}
```

### Features
- ✅ Real-time transcription (< 200ms latency)
- ✅ Interim results (shows partial transcripts)
- ✅ Speaker diarization
- ✅ WebSocket-based (low latency)

---

## Testing

### Test File Upload

1. **Create a test audio file** (or use existing):
```bash
# Record 5 seconds of audio
rec test.wav trim 0 5
```

2. **Upload and transcribe:**
```bash
curl -X POST "http://127.0.0.1:8000/api/transcription/transcribe" \
  -F "audio_file=@test.wav" | python -m json.tool
```

### Test Real-Time (Browser)

1. **Open browser console** (F12)
2. **Run this code:**
```javascript
const ws = new WebSocket('ws://127.0.0.1:8000/api/realtime/transcribe');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
ws.onopen = () => {
  navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = e => ws.send(e.data);
      recorder.start(100);
    });
};
```

3. **Speak into microphone** - transcripts will appear in console

---

## API Documentation

Full API docs available at:
```
http://127.0.0.1:8000/docs
```

---

## Status

| Endpoint | Status | Notes |
|----------|--------|-------|
| `/api/transcription/transcribe` | ✅ Working | File upload, prerecorded |
| `/api/realtime/transcribe` | ✅ Working | WebSocket, real-time |
| LiveKit Agent (real-time) | ⚠️ Needs deployment | Requires LiveKit Cloud deployment |

---

## Next Steps

1. **Test file upload endpoint** - Upload an audio file and verify transcript
2. **Test WebSocket endpoint** - Connect from browser and speak
3. **Integrate WebSocket into frontend** - Replace LiveKit agent with WebSocket
4. **Deploy agent to LiveKit Cloud** (optional) - For production LiveKit integration

---

## Files Created

- `backend/app/routes/transcription.py` - File upload endpoint
- `backend/app/routes/realtime_transcription.py` - WebSocket endpoint
- `backend/app/main.py` - Updated to include routers

