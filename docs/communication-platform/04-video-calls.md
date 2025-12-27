# Priority 4: Video Calls

Face-to-face video calls with optional facial expression and body language analysis.

## Overview

Video calls provide the richest communication data:
- Everything from voice calls PLUS
- Facial expressions (micro-expressions, eye contact)
- Body language cues
- Visual context (environment, activity)

## Why Video Calls (Lower Priority)

Video calls are powerful but:
- More complex to implement
- Higher bandwidth requirements
- Privacy concerns with video recording/analysis
- Many couples default to voice for quick calls

**Recommendation**: Build voice calls first, add video as an upgrade.

## Tech Stack

| Component | Technology | Why |
|-----------|------------|-----|
| Video streaming | Agora / 100ms / Daily.co | Same providers as voice, add video track |
| Recording | Provider's recording API | Easier than DIY |
| Facial analysis | MediaPipe / TensorFlow.js | On-device, privacy-preserving |
| Emotion detection | Custom model or API | From facial landmarks |

## Architecture

Same as voice calls, with added video track:

```
┌─────────────────────────────────────────────────────────┐
│                    Video Call                            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   ┌─────────────┐              ┌─────────────┐          │
│   │  Partner A  │              │  Partner B  │          │
│   │  ┌───────┐  │   WebRTC     │  ┌───────┐  │          │
│   │  │ Video │◄─┼──────────────┼─►│ Video │  │          │
│   │  └───────┘  │              │  └───────┘  │          │
│   │  ┌───────┐  │              │  ┌───────┐  │          │
│   │  │ Audio │◄─┼──────────────┼─►│ Audio │  │          │
│   │  └───────┘  │              │  └───────┘  │          │
│   └─────────────┘              └─────────────┘          │
│                                                          │
│   On-device analysis:                                    │
│   ┌──────────────────────────────────────────┐          │
│   │  MediaPipe Face Detection                 │          │
│   │  - Facial landmarks (468 points)          │          │
│   │  - Expression classification              │          │
│   │  - Eye gaze direction                     │          │
│   └──────────────────────────────────────────┘          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Facial Expression Analysis

### On-Device with MediaPipe

```typescript
import { FaceMesh } from '@mediapipe/face_mesh';
import { Camera } from '@mediapipe/camera_utils';

const faceMesh = new FaceMesh({
  locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`
});

faceMesh.setOptions({
  maxNumFaces: 1,
  refineLandmarks: true,
  minDetectionConfidence: 0.5,
  minTrackingConfidence: 0.5
});

faceMesh.onResults((results) => {
  if (results.multiFaceLandmarks) {
    const landmarks = results.multiFaceLandmarks[0];

    // Extract features
    const expression = analyzeExpression(landmarks);
    const eyeGaze = analyzeEyeGaze(landmarks);
    const headPose = analyzeHeadPose(landmarks);

    // Send summary to backend (not raw video)
    sendExpressionData({
      timestamp: Date.now(),
      expression,  // {happy: 0.7, neutral: 0.2, sad: 0.1}
      eyeContact: eyeGaze.lookingAtScreen,
      headPose    // {pitch, yaw, roll}
    });
  }
});
```

### Expression Classification

From facial landmarks, classify:

| Expression | Key Indicators |
|------------|----------------|
| Happy | Raised mouth corners, crow's feet near eyes |
| Sad | Lowered mouth corners, inner brow raise |
| Angry | Lowered brows, tightened lips, flared nostrils |
| Surprised | Raised brows, open mouth |
| Disgusted | Wrinkled nose, raised upper lip |
| Fearful | Raised brows, widened eyes, open mouth |
| Neutral | Relaxed facial muscles |

```typescript
function analyzeExpression(landmarks: NormalizedLandmark[]): ExpressionScores {
  // Key landmark indices for expression analysis
  const leftMouthCorner = landmarks[61];
  const rightMouthCorner = landmarks[291];
  const upperLip = landmarks[13];
  const lowerLip = landmarks[14];
  const leftEyebrow = landmarks[66];
  const rightEyebrow = landmarks[296];

  // Calculate features
  const mouthOpenness = distance(upperLip, lowerLip);
  const mouthWidth = distance(leftMouthCorner, rightMouthCorner);
  const browHeight = (leftEyebrow.y + rightEyebrow.y) / 2;

  // Simple heuristic classification (replace with trained model)
  const scores = {
    happy: mouthWidth > threshold && mouthCornersRaised(landmarks) ? 0.8 : 0.1,
    sad: mouthCornersLowered(landmarks) ? 0.7 : 0.1,
    angry: browsLowered(landmarks) && lipsTightened(landmarks) ? 0.7 : 0.1,
    neutral: 0.3  // default
  };

  return normalize(scores);
}
```

## Privacy-Preserving Design

Video is sensitive. Design choices:

| Approach | Privacy | Insight Quality |
|----------|---------|-----------------|
| No video analysis | High | None |
| On-device only, send summaries | High | Good |
| Record video, analyze server-side | Low | Excellent |
| Real-time server analysis, no storage | Medium | Excellent |

**Recommendation**: On-device analysis, send only expression summaries (not video frames).

## Database Schema

```sql
-- Extends calls table
ALTER TABLE calls ADD COLUMN is_video BOOLEAN DEFAULT false;
ALTER TABLE calls ADD COLUMN video_recording_url TEXT;

-- Expression data (sampled, not continuous)
CREATE TABLE call_expression_samples (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  call_id UUID REFERENCES calls(id),
  user_id UUID REFERENCES users(id),
  timestamp_ms INTEGER NOT NULL, -- ms from call start

  -- Expression scores
  expression_happy FLOAT,
  expression_sad FLOAT,
  expression_angry FLOAT,
  expression_surprised FLOAT,
  expression_neutral FLOAT,
  dominant_expression TEXT,

  -- Engagement indicators
  eye_contact BOOLEAN,
  looking_away_duration_ms INTEGER,

  -- Head pose
  head_pitch FLOAT,
  head_yaw FLOAT,
  head_roll FLOAT
);

-- Aggregated per call
ALTER TABLE calls ADD COLUMN expression_summary JSONB;
/*
{
  partner_a: {
    dominant_expression: "neutral",
    expression_distribution: {happy: 0.3, neutral: 0.5, sad: 0.1, angry: 0.1},
    eye_contact_ratio: 0.75,
    expression_changes: 12
  },
  partner_b: { ... },
  synchrony: 0.65  // how often expressions match
}
*/
```

## Insights from Video

| Metric | What It Tells You |
|--------|-------------------|
| Expression synchrony | Are they emotionally in sync? |
| Eye contact ratio | Engagement and attention |
| Smile frequency | Positive sentiment in conversation |
| Expression volatility | Emotional stability during call |
| Looking away | Distraction, avoidance, thinking |

```python
def analyze_video_call(call_id):
    samples = get_expression_samples(call_id)

    # Group by user
    partner_a_samples = [s for s in samples if s.user_id == partner_a_id]
    partner_b_samples = [s for s in samples if s.user_id == partner_b_id]

    return {
        "partner_a": {
            "dominant_expression": mode([s.dominant_expression for s in partner_a_samples]),
            "expression_distribution": average_expression_scores(partner_a_samples),
            "eye_contact_ratio": sum(s.eye_contact for s in partner_a_samples) / len(partner_a_samples),
            "expression_changes": count_expression_changes(partner_a_samples)
        },
        "partner_b": { ... },
        "synchrony": calculate_expression_synchrony(partner_a_samples, partner_b_samples)
    }
```

## UI Components

### VideoCallScreen

```tsx
<VideoCallScreen
  callId={callId}
  localStream={localVideoStream}
  remoteStream={remoteVideoStream}

  // Controls
  onToggleCamera={handleToggleCamera}
  onToggleMic={handleToggleMic}
  onSwitchCamera={handleSwitchCamera} // front/back
  onEnd={handleEndCall}

  // Layout
  layout="pip" // 'pip' | 'split' | 'focus'
  pipPosition="bottom-right"

  // Luna
  showExpressionIndicator={true} // subtle indicator of detected emotion
/>
```

### CameraPreview

```tsx
<CameraPreview
  stream={localVideoStream}
  mirrored={true}
  showFaceOverlay={false} // optional: show face mesh for debugging
/>
```

## Bandwidth Considerations

| Quality | Resolution | Bitrate | Data/min |
|---------|------------|---------|----------|
| Low | 320x240 | 150 kbps | ~1.1 MB |
| Medium | 640x480 | 400 kbps | ~3 MB |
| High | 1280x720 | 1.5 Mbps | ~11 MB |

Adaptive bitrate based on network conditions is standard in Agora/100ms.

## Implementation Steps

### Phase 1: Basic Video Calling
- [ ] Add video track to existing call infrastructure
- [ ] Camera toggle, flip camera
- [ ] Video UI (PIP, split view)
- [ ] Bandwidth adaptation

### Phase 2: Expression Analysis (On-Device)
- [ ] Integrate MediaPipe
- [ ] Expression classification
- [ ] Eye gaze detection
- [ ] Send summary data to backend

### Phase 3: Insights
- [ ] Store expression samples
- [ ] Calculate call-level summaries
- [ ] Display in call history
- [ ] Luna insights from video

### Phase 4: Advanced (Optional)
- [ ] Video recording (with consent)
- [ ] Thumbnail generation from key moments
- [ ] Expression timeline visualization

## Cost Estimation

| Component | Additional Cost |
|-----------|-----------------|
| Video streaming | ~2x voice cost |
| On-device analysis | Free (runs on device) |
| Server-side analysis | Avoided by on-device approach |
| Storage (if recording) | ~10x audio storage |

For 100 couples, 30 min video/day at medium quality:
- Video streaming: ~$200/month (additional to voice)
- Storage (if recording): ~$50/month

## When to Build Video

**Build video calls when**:
- Voice calls are stable and adopted
- Users request video
- You want richer emotion data

**Skip video initially because**:
- Voice gives 80% of the insight
- Video is more complex
- Privacy concerns are higher
- Users may not want face analysis
