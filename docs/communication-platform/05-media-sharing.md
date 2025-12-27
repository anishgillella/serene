# Priority 5: Photo/Video Sharing

Share personal photos, videos, and media within conversations.

## Overview

Media sharing completes the messaging experience:
- Personal photos (selfies, moments together)
- Videos (short clips, memories)
- Screenshots (sharing content from elsewhere)
- Camera integration for in-the-moment capture

## Why Media Sharing Matters

| Content Type | Relationship Signal |
|--------------|---------------------|
| Selfies | "Thinking of you" bids for connection |
| Couple photos | Celebrating the relationship |
| Daily moments | Sharing life, staying connected |
| Screenshots | Shared interests, humor |
| Throwback photos | Nostalgia, reinforcing bond |

**Key insight**: The *act* of sharing matters as much as *what* is shared.

## Tech Stack

| Component | Technology | Why |
|-----------|------------|-----|
| Storage | Cloudflare R2 / AWS S3 | Cheap, scalable, CDN |
| CDN | Cloudflare / CloudFront | Fast global delivery |
| Image processing | Sharp (Node) / Pillow (Python) | Resize, compress, thumbnails |
| Video processing | FFmpeg | Thumbnails, compression, format conversion |
| Upload | Direct to S3 with presigned URLs | Offload from server |

## User Flow

```
1. User taps attachment button
        │
        ├─► Camera: Take photo/video
        │
        ├─► Gallery: Pick existing media
        │
        └─► (Future) GIF picker
                │
                ▼
2. Preview & confirm
        │
        ▼
3. Get presigned upload URL from backend
        │
        ▼
4. Upload directly to S3/R2
        │
        ▼
5. Send message with media reference
        │
        ▼
6. Backend processes async:
   - Generate thumbnail
   - Compress for delivery
   - Extract metadata
   - Classify content (optional)
        │
        ▼
7. Recipient receives message with media
```

## Database Schema

```sql
-- Media table
CREATE TABLE media (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  uploader_id UUID REFERENCES users(id),
  conversation_id UUID REFERENCES conversations(id),

  -- Original file
  original_url TEXT NOT NULL,
  original_filename TEXT,
  mime_type TEXT NOT NULL,
  file_size_bytes INTEGER,

  -- Processed versions
  thumbnail_url TEXT,
  compressed_url TEXT, -- For videos

  -- Dimensions
  width INTEGER,
  height INTEGER,
  duration_seconds FLOAT, -- For videos

  -- Metadata
  captured_at TIMESTAMPTZ, -- EXIF date if available
  location_lat FLOAT,      -- EXIF location (if permitted)
  location_lng FLOAT,

  -- Classification (optional)
  content_labels JSONB,    -- {selfie: true, people: 2, outdoor: true}

  -- Status
  processing_status TEXT DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Messages reference media
ALTER TABLE messages ADD COLUMN media_id UUID REFERENCES media(id);
ALTER TABLE messages ADD COLUMN media_ids UUID[]; -- For multiple attachments
```

## API Endpoints

```
POST   /api/media/upload-url            Get presigned URL for upload
POST   /api/media/complete              Mark upload complete, trigger processing
GET    /api/media/:id                   Get media metadata + URLs
DELETE /api/media/:id                   Delete media

GET    /api/conversations/:id/media     Get all media in conversation (gallery view)
```

## Upload Flow

### Frontend (React Native example)

```typescript
async function uploadMedia(file: File | Asset) {
  // 1. Get presigned URL
  const { uploadUrl, mediaId, fields } = await api.post('/media/upload-url', {
    filename: file.name,
    mimeType: file.type,
    fileSize: file.size
  });

  // 2. Upload directly to S3
  const formData = new FormData();
  Object.entries(fields).forEach(([key, value]) => {
    formData.append(key, value);
  });
  formData.append('file', file);

  await fetch(uploadUrl, {
    method: 'POST',
    body: formData
  });

  // 3. Notify backend upload is complete
  await api.post('/media/complete', { mediaId });

  return mediaId;
}

async function sendMediaMessage(conversationId: string, mediaId: string, caption?: string) {
  await api.post('/messages', {
    conversationId,
    contentType: 'image', // or 'video'
    mediaId,
    content: caption || ''
  });
}
```

### Backend Processing

```python
async def process_media(media_id: str):
    media = await get_media(media_id)

    await update_media(media_id, {"processing_status": "processing"})

    try:
        if media.mime_type.startswith('image/'):
            await process_image(media)
        elif media.mime_type.startswith('video/'):
            await process_video(media)

        await update_media(media_id, {"processing_status": "completed"})
    except Exception as e:
        await update_media(media_id, {"processing_status": "failed"})
        raise

async def process_image(media):
    original = await download(media.original_url)

    # Generate thumbnail (150x150, crop center)
    thumbnail = resize_and_crop(original, 150, 150)
    thumbnail_url = await upload(thumbnail, f"thumbnails/{media.id}.jpg")

    # Extract EXIF metadata
    exif = extract_exif(original)

    # Get dimensions
    width, height = get_dimensions(original)

    await update_media(media.id, {
        "thumbnail_url": thumbnail_url,
        "width": width,
        "height": height,
        "captured_at": exif.get("DateTimeOriginal"),
        "location_lat": exif.get("GPSLatitude"),
        "location_lng": exif.get("GPSLongitude")
    })

async def process_video(media):
    original = await download(media.original_url)

    # Generate thumbnail from first frame
    thumbnail = extract_frame(original, 0)
    thumbnail_url = await upload(thumbnail, f"thumbnails/{media.id}.jpg")

    # Get video metadata
    probe = ffprobe(original)
    duration = probe.duration
    width = probe.width
    height = probe.height

    # Compress video if needed
    if probe.bitrate > MAX_BITRATE:
        compressed = compress_video(original, target_bitrate=MAX_BITRATE)
        compressed_url = await upload(compressed, f"compressed/{media.id}.mp4")
    else:
        compressed_url = media.original_url

    await update_media(media.id, {
        "thumbnail_url": thumbnail_url,
        "compressed_url": compressed_url,
        "width": width,
        "height": height,
        "duration_seconds": duration
    })
```

## Content Classification (Optional)

Classify images to understand sharing patterns:

```python
async def classify_image(media_id: str, image_path: str):
    # Use Claude vision or dedicated classification model
    labels = await vision_model.classify(image_path)

    # Example labels:
    # {
    #   "selfie": true,
    #   "people_count": 2,
    #   "setting": "outdoor",
    #   "mood": "happy",
    #   "contains_text": false,
    #   "is_screenshot": false,
    #   "categories": ["personal", "couple", "travel"]
    # }

    await update_media(media_id, {"content_labels": labels})
```

## Insights from Media Sharing

| Metric | Insight |
|--------|---------|
| Sharing frequency | Overall engagement level |
| Selfie ratio | Personal investment in connection |
| Response time to media | Engagement with partner's shares |
| Screenshot ratio | Sharing external content vs personal |
| Location diversity | Adventures together |
| Time of day | When they think of each other |

```python
def analyze_media_sharing(relationship_id, period_days=30):
    media = get_media_for_relationship(relationship_id, days=period_days)

    return {
        "total_shared": len(media),
        "by_partner": {
            partner_a: count_by_uploader(media, partner_a),
            partner_b: count_by_uploader(media, partner_b)
        },
        "selfie_ratio": count_selfies(media) / len(media),
        "screenshot_ratio": count_screenshots(media) / len(media),
        "avg_response_time_minutes": calculate_avg_response_time(media),
        "sharing_trend": calculate_trend(media),  # increasing/stable/decreasing
        "most_active_time": most_common_hour(media)
    }
```

## UI Components

### MediaAttachmentButton

```tsx
<MediaAttachmentButton
  onPickFromGallery={handleGalleryPick}
  onOpenCamera={handleCamera}
  onPickGif={handleGifPicker} // future
/>
```

### ImageMessage

```tsx
<ImageMessage
  thumbnailUrl={message.media.thumbnail_url}
  fullUrl={message.media.original_url}
  width={message.media.width}
  height={message.media.height}
  caption={message.content}
  onPress={() => openFullscreen(message.media)}
/>
```

### VideoMessage

```tsx
<VideoMessage
  thumbnailUrl={message.media.thumbnail_url}
  videoUrl={message.media.compressed_url}
  duration={message.media.duration_seconds}
  onPress={() => playVideo(message.media)}
/>
```

### MediaGallery

```tsx
// Grid view of all shared media in conversation
<MediaGallery
  conversationId={conversationId}
  onMediaPress={(media) => openFullscreen(media)}
/>
```

## Storage Costs

| Size | Files/Month | Storage | R2 Cost |
|------|-------------|---------|---------|
| 2 MB avg | 1,000 | 2 GB | $0.03 |
| 2 MB avg | 10,000 | 20 GB | $0.30 |
| 2 MB avg | 100,000 | 200 GB | $3.00 |

Egress is free on Cloudflare R2, making it very cost-effective.

## Implementation Steps

### Phase 1: Basic Sharing
- [ ] Presigned upload URLs
- [ ] Image upload flow
- [ ] Image display in messages
- [ ] Full-screen viewer

### Phase 2: Video Support
- [ ] Video upload
- [ ] FFmpeg processing pipeline
- [ ] Video player component
- [ ] Compressed delivery

### Phase 3: Polish
- [ ] Thumbnail generation
- [ ] Loading states / progressive loading
- [ ] Multi-image messages
- [ ] Retry failed uploads

### Phase 4: Insights
- [ ] Content classification
- [ ] Media gallery view
- [ ] Sharing pattern analytics

## Security Considerations

- Presigned URLs expire quickly (15 min)
- Validate file types server-side
- Size limits (e.g., 50 MB for images, 500 MB for videos)
- Virus scanning on upload (optional)
- Media URLs should not be guessable (use UUIDs)
- Only conversation participants can access media
