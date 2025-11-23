# LiveKit Voice Agent - Luna

A RAG-enabled voice agent built with LiveKit that provides real-time voice conversations with a friendly digital companion named Luna.

## Features

- 🎙️ Real-time voice conversation with LiveKit
- 🧠 GPT-4 powered responses
- 🎤 Deepgram STT for accurate speech recognition
- 🔊 ElevenLabs TTS for natural voice synthesis
- 📝 Live transcript display
- 🛠️ Tool calling (time/date checking)
- 🎨 Simple, clean React frontend

## Project Structure

```
.
├── src/
│   ├── agent.py              # Main LiveKit agent code
│   └── generate_token.py     # Token generation utility
├── frontend/
│   ├── src/
│   │   ├── App.js            # Main React component
│   │   ├── App.css           # Styles
│   │   └── index.js          # React entry point
│   └── package.json          # Frontend dependencies
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
└── README.md                # This file
```

## Setup Instructions

### 1. Prerequisites

- Python 3.9 or higher
- Node.js 16+ and npm
- LiveKit Cloud account (get one at https://cloud.livekit.io)
- API keys for:
  - OpenAI (for LLM)
  - Deepgram (for STT)
  - ElevenLabs (for TTS)

### 2. Backend Setup

1. **Clone and navigate to project:**
   ```bash
   cd "Livekit Voice Agent"
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env.local
   ```
   
   Edit `.env.local` and add your API keys:
   ```env
   LIVEKIT_API_KEY=your_api_key
   LIVEKIT_API_SECRET=your_api_secret
   LIVEKIT_URL=wss://your-project.livekit.cloud
   OPENAI_API_KEY=your_openai_key
   DEEPGRAM_API_KEY=your_deepgram_key
   ELEVEN_API_KEY=your_elevenlabs_key
   ```

5. **Download required models:**
   ```bash
   python src/agent.py download-files
   ```

### 3. Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Create `.env` file in frontend directory:**
   ```env
   REACT_APP_LIVEKIT_URL=wss://your-project.livekit.cloud
   REACT_APP_LIVEKIT_TOKEN=  # Leave empty, will be generated
   ```

### 4. Token Server

The token server (`src/token_server.py`) will automatically generate tokens for the frontend. Make sure to run it alongside your agent (see Running the Application section).

## Running the Application

You'll need **three terminals** running:

### Terminal 1: Start the Agent (Backend)

```bash
# Activate virtual environment if not already active
source venv/bin/activate

# Run in development mode
python src/agent.py dev
```

The agent will connect to LiveKit Cloud and wait for connections.

### Terminal 2: Start the Token Server

```bash
# Activate virtual environment if not already active
source venv/bin/activate

# Run the token server
python src/token_server.py
```

The token server will run on `http://localhost:8080` and generate tokens for the frontend.

### Terminal 3: Start the Frontend

```bash
cd frontend
npm start
```

The React app will open at `http://localhost:3000`.

### Using the Application

1. Click "Start Call" to connect to Luna
2. Allow microphone permissions when prompted
3. Start talking! Luna will respond in real-time
4. Watch the live transcript update as you converse
5. Try asking "What time is it?" to see tool calling in action
6. Click "End Call" when done

## Testing in Console Mode

You can test the agent directly in your terminal:

```bash
python src/agent.py console
```

This allows you to test the agent without the frontend.

## Agent Personality

Luna is a friendly digital companion with:
- Warm, approachable personality
- Helpful and enthusiastic
- Keeps responses concise (2-3 sentences)
- Natural, conversational language

## Tool Calling

The agent includes a simple tool for getting the current time. Ask Luna "What time is it?" or "What's the date?" to see it in action.

## Development Notes

- The agent uses GPT-4o-mini for cost-effectiveness
- Deepgram Nova-2 model for fast, accurate transcription
- ElevenLabs multilingual model for natural voice synthesis
- Silero VAD for voice activity detection

## Next Steps (RAG Integration)

To add RAG capabilities:
1. Choose a RAG framework (LangChain recommended)
2. Set up vector store (ChromaDB, Pinecone, etc.)
3. Process PDF documents into embeddings
4. Integrate retrieval into agent's LLM pipeline
5. Update agent instructions to use retrieved context

## Troubleshooting

**Agent won't connect:**
- Check `.env.local` credentials
- Verify LiveKit Cloud project is active
- Ensure all API keys are valid

**No audio:**
- Check microphone permissions
- Verify browser audio settings
- Check browser console for errors

**Transcript not updating:**
- Ensure room connection is established
- Check browser console for errors
- Verify token is valid

## Resources

- [LiveKit Agents Docs](https://docs.livekit.io/agents/)
- [LiveKit Python SDK](https://github.com/livekit/agents)
- [Deepgram Docs](https://developers.deepgram.com/)
- [ElevenLabs Docs](https://elevenlabs.io/docs)

## License

MIT

