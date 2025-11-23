# HeartSync Agent Deployment Guide

## Prerequisites

1. **Install LiveKit CLI**
   ```bash
   # Install via npm (if available)
   npm install -g @livekit/cli
   
   # OR download binary from:
   # https://github.com/livekit/livekit-cli/releases
   ```

2. **Authenticate with LiveKit Cloud**
   ```bash
   lk cloud auth
   ```
   This will open a browser to link your LiveKit Cloud account.

3. **Set Default Project** (optional)
   ```bash
   lk project set-default "voice-agent-qnma0l98"
   ```

---

## Deployment Steps

### Step 1: Navigate to Backend Directory
```bash
cd backend
```

### Step 2: Create Agent (First Time Only)
```bash
lk agent create \
  --region us-east \
  --secrets-file .env \
  .
```

This will:
- Create `livekit.toml` with agent ID
- Create `Dockerfile` if it doesn't exist
- Build and deploy the agent

**Note:** Make sure `.env` contains all required secrets:
- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `DEEPGRAM_API_KEY`
- `ELEVENLABS_API_KEY`
- `VOYAGE_API_KEY`
- `OPENROUTER_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `DATABASE_URL`

### Step 3: Deploy Updates
```bash
lk agent deploy
```

This builds a new version and deploys it.

### Step 4: Check Status
```bash
lk agent status
```

### Step 5: View Logs
```bash
lk agent logs --log-type deploy
```

---

## Files Created

- ✅ `Dockerfile` - Container definition
- ✅ `.dockerignore` - Files to exclude from build
- ✅ `start_agent.py` - Agent startup script
- ✅ `livekit.toml` - Agent configuration (created on first deploy)

---

## Troubleshooting

### "Agent not responding"
- Check logs: `lk agent logs`
- Verify secrets: `lk agent secrets`
- Check status: `lk agent status`

### "Build failed"
- Check Dockerfile syntax
- Verify all dependencies in `requirements.txt`
- Check build logs: `lk agent logs --log-type build`

### "Agent not joining rooms"
- Verify agent is deployed and running: `lk agent status`
- Check that `entrypoint` function is correct
- Verify LiveKit URL and credentials

---

## Environment Variables

The agent needs these environment variables (set via `--secrets-file .env`):

```bash
LIVEKIT_URL=wss://voice-agent-qnma0l98.livekit.cloud
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
DEEPGRAM_API_KEY=...
ELEVENLABS_API_KEY=...
VOYAGE_API_KEY=...
OPENROUTER_API_KEY=...
SUPABASE_URL=...
SUPABASE_KEY=...
DATABASE_URL=...
```

---

## Quick Commands Reference

```bash
# Create new agent
lk agent create --region us-east --secrets-file .env .

# Deploy updates
lk agent deploy

# Check status
lk agent status

# View logs
lk agent logs

# Update secrets
lk agent update-secrets --secrets-file .env

# Restart agent
lk agent restart

# Rollback to previous version
lk agent rollback

# Delete agent
lk agent delete
```

---

## After Deployment

Once deployed, your agent will:
1. ✅ Automatically join LiveKit rooms when created
2. ✅ Capture audio from participants
3. ✅ Transcribe via Deepgram WebSocket
4. ✅ Send transcripts to frontend via data channel
5. ✅ Save transcripts to Supabase

**Test it:**
1. Open frontend: http://localhost:5175
2. Click "Start Fight Capture"
3. Speak into microphone
4. See transcripts appear in real-time!


