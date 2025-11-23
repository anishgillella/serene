import React, { useState, useEffect, useRef } from 'react';
import { Room, RoomEvent, RemoteParticipant, LocalParticipant } from 'livekit-client';
import './App.css';

// Replace these with your LiveKit credentials
const LIVEKIT_URL = process.env.REACT_APP_LIVEKIT_URL || 'wss://trial-w97lcj4b.livekit.cloud';
const TOKEN_SERVER_URL = process.env.REACT_APP_TOKEN_SERVER_URL || 'http://localhost:8080';

function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [transcript, setTranscript] = useState([]);
  const [isConnecting, setIsConnecting] = useState(false);
  const roomRef = useRef(null);
  const localTracksRef = useRef([]);

  // Generate token from token server
  const generateToken = async (roomName) => {
    try {
      const response = await fetch(`${TOKEN_SERVER_URL}/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          room: roomName,
          participant: 'user'
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to generate token');
      }
      
      const data = await response.json();
      return { token: data.token, room: data.room, url: data.url };
    } catch (error) {
      console.error('Error generating token:', error);
      throw error;
    }
  };

  const startCall = async () => {
    if (isConnecting || isConnected) return;

    setIsConnecting(true);
    
    try {
      const roomName = `voice-agent-${Date.now()}`;
      const { token, url } = await generateToken(roomName);
      
      if (!token) {
        alert('Failed to generate token. Make sure token server is running on port 8080');
        setIsConnecting(false);
        return;
      }

      const room = new Room();
      roomRef.current = room;

      // Set up event listeners
      room.on(RoomEvent.Connected, () => {
        console.log('Connected to room');
        setIsConnected(true);
        setIsConnecting(false);
        addTranscriptEntry('system', 'Connected to Luna!');
      });

      room.on(RoomEvent.Disconnected, () => {
        console.log('Disconnected from room');
        setIsConnected(false);
        addTranscriptEntry('system', 'Disconnected from Luna');
        cleanup();
      });

      room.on(RoomEvent.ParticipantConnected, (participant) => {
        console.log('Participant connected:', participant.identity);
        addTranscriptEntry('system', `${participant.identity} joined`);
      });

      room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
        if (track.kind === 'audio') {
          const audioElement = track.attach();
          audioElement.play();
        }
      });

      room.on(RoomEvent.DataReceived, (payload, participant) => {
        if (participant) {
          try {
            const data = JSON.parse(new TextDecoder().decode(payload));
            if (data.type === 'transcript') {
              addTranscriptEntry(participant.identity === 'agent' ? 'agent' : 'user', data.text);
            }
          } catch (e) {
            console.error('Error parsing data:', e);
          }
        }
      });

      // Connect to room
      await room.connect(url || LIVEKIT_URL, token);

      // Enable microphone
      const localTracks = await room.localParticipant.enableCameraAndMicrophone(false, true);
      localTracksRef.current = localTracks;

    } catch (error) {
      console.error('Error connecting to room:', error);
      alert('Failed to connect: ' + error.message);
      setIsConnecting(false);
      cleanup();
    }
  };

  const endCall = async () => {
    if (!roomRef.current) return;

    try {
      await roomRef.current.disconnect();
      cleanup();
      setIsConnected(false);
      addTranscriptEntry('system', 'Call ended');
    } catch (error) {
      console.error('Error disconnecting:', error);
    }
  };

  const cleanup = () => {
    localTracksRef.current.forEach(track => {
      track.stop();
      track.detach();
    });
    localTracksRef.current = [];
    roomRef.current = null;
  };

  const addTranscriptEntry = (speaker, text) => {
    setTranscript(prev => [...prev, { speaker, text, timestamp: new Date() }]);
  };

  useEffect(() => {
    return () => {
      cleanup();
    };
  }, []);

  return (
    <div className="App">
      <div className="container">
        <h1>🎙️ Luna - Your Digital Companion</h1>
        
        <div className="controls">
          {!isConnected ? (
            <button 
              className="btn btn-start" 
              onClick={startCall}
              disabled={isConnecting}
            >
              {isConnecting ? 'Connecting...' : 'Start Call'}
            </button>
          ) : (
            <button 
              className="btn btn-end" 
              onClick={endCall}
            >
              End Call
            </button>
          )}
        </div>

        <div className="status">
          <div className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
            {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
          </div>
        </div>

        <div className="transcript-container">
          <h2>Live Transcript</h2>
          <div className="transcript">
            {transcript.length === 0 ? (
              <div className="transcript-empty">
                Start a call to see the conversation transcript here...
              </div>
            ) : (
              transcript.map((entry, index) => (
                <div key={index} className={`transcript-entry ${entry.speaker}`}>
                  <span className="speaker">{entry.speaker === 'agent' ? 'Luna' : entry.speaker === 'user' ? 'You' : 'System'}:</span>
                  <span className="text">{entry.text}</span>
                  <span className="timestamp">
                    {entry.timestamp.toLocaleTimeString()}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;

