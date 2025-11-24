import React, { useState, useEffect, useRef } from 'react';
import { Room, RoomEvent, RemoteParticipant, LocalParticipant } from 'livekit-client';
import { XIcon, MicIcon, MicOffIcon } from 'lucide-react';

interface MediatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  conflictId: string;
  context?: {
    activeView?: 'analysis' | 'repair' | null;
    povView?: 'boyfriend' | 'girlfriend';
    hasAnalysis?: boolean;
    hasRepairPlans?: boolean;
  };
}

interface TranscriptEntry {
  speaker: 'agent' | 'user' | 'system';
  text: string;
  timestamp: Date;
}

const MediatorModal: React.FC<MediatorModalProps> = ({ isOpen, onClose, conflictId, context }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isAgentJoining, setIsAgentJoining] = useState(false);
  const roomRef = useRef<Room | null>(null);
  const localTracksRef = useRef<any[]>([]);
  const agentJoinedRef = useRef<boolean>(false); // Track if agent already joined to prevent duplicates

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

  // Generate token from backend
  const generateToken = async (conflictId: string) => {
    console.log('🔑 generateToken called with conflictId:', conflictId);
    console.log('🌐 API_BASE_URL:', API_BASE_URL);

    try {
      const requestBody = {
        conflict_id: conflictId,
        participant_name: 'user'
      };
      console.log('📤 Sending token request:', requestBody);

      const response = await fetch(`${API_BASE_URL}/api/mediator/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      console.log('📥 Response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Token request failed:', errorText);
        throw new Error(`Failed to generate token: ${response.status} ${errorText}`);
      }

      const data = await response.json();
      console.log('✅ Token response received:', {
        hasToken: !!data.token,
        room: data.room,
        url: data.url,
        tokenPreview: data.token?.substring(0, 30) + '...'
      });

      return { token: data.token, room: data.room, url: data.url };
    } catch (error) {
      console.error('❌ Error generating token:', error);
      throw error;
    }
  };

  const startCall = async () => {
    console.log('🚀 startCall called', { isConnecting, isConnected, conflictId });

    if (isConnecting || isConnected) {
      console.log('⚠️ Already connecting or connected, skipping');
      return;
    }

    setIsConnecting(true);

    try {
      console.log('📝 Generating token for conflict:', conflictId);
      const { token, url } = await generateToken(conflictId);
      console.log('✅ Token generated:', { token: token?.substring(0, 20) + '...', url, room: conflictId });

      if (!token) {
        console.error('❌ No token received');
        alert('Failed to generate token. Please try again.');
        setIsConnecting(false);
        return;
      }

      console.log('🏠 Creating new Room instance');
      const room = new Room();
      roomRef.current = room;

      // Set up event listeners
      room.on(RoomEvent.Connected, () => {
        console.log('Connected to mediator room');
        setIsConnected(true);
        setIsConnecting(false);
        addTranscriptEntry('system', 'Connected to room. Waiting for Luna...');
      });

      room.on(RoomEvent.Disconnected, () => {
        console.log('Disconnected from mediator room');
        setIsConnected(false);
        setIsAgentJoining(false);
        agentJoinedRef.current = false; // Reset agent joined flag
        addTranscriptEntry('system', 'Disconnected from Luna');
        cleanup();
      });

      room.on(RoomEvent.ParticipantDisconnected, (participant) => {
        console.log('Participant disconnected:', participant.identity);
        const isAgent = participant.identity.startsWith('agent-') || participant.name === 'Luna';
        if (isAgent) {
          console.log('✅ Agent (Luna) disconnected');
          addTranscriptEntry('system', 'Luna has left');
        }
      });

      room.on(RoomEvent.ParticipantConnected, (participant) => {
        console.log('Participant connected:', participant.identity, 'name:', participant.name);
        // Check if it's the agent (usually starts with agent- or has name Luna)
        const isAgent = participant.identity.startsWith('agent-') || participant.name === 'Luna';
        const displayName = isAgent ? 'Luna' : participant.identity;

        // Only log agent joining once to prevent duplicate messages
        if (isAgent) {
          if (!agentJoinedRef.current) {
            agentJoinedRef.current = true;
            addTranscriptEntry('system', `${displayName} joined`);
            setIsAgentJoining(false);
          } else {
            console.log('⚠️ Duplicate agent join detected, ignoring:', participant.identity);
          }
        } else {
          addTranscriptEntry('system', `${displayName} joined`);
        }

        // Subscribe to all audio tracks from the agent
        if (participant.audioTracks && participant.audioTracks.size > 0) {
          participant.audioTracks.forEach((publication) => {
            if (publication.track) {
              const audioElement = publication.track.attach();
              audioElement.play().catch(err => console.error('Error playing audio:', err));
            } else if (publication.setSubscribed) {
              publication.setSubscribed(true);
            }
          });
        }
      });

      room.on(RoomEvent.TrackPublished, (publication, participant) => {
        console.log('🔊 Track published:', publication.kind, 'by', participant.identity, 'trackName:', publication.trackName, 'subscribed:', publication.isSubscribed);
        if (publication.kind === 'audio') {
          // Subscribe to ALL audio tracks (agent will publish TTS audio)
          console.log('✅ Subscribing to audio track from', participant.identity);
          publication.setSubscribed(true);
        }
      });

      room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
        console.log('🎧 Track subscribed:', track.kind, 'from', participant.identity);
        if (track.kind === 'audio') {
          // Simple approach - EXACTLY like working Livekit Voice Agent
          const audioElement = track.attach();
          audioElement.play().catch(err => console.error('Error playing audio:', err));
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
        console.log('🔌 Connecting to room:', { url, roomName: `mediator-${conflictId}`, tokenLength: token.length });
        try {
          await room.connect(url, token);
          console.log('✅ Connected to room:', room.name);
          console.log('👥 Remote participants:', room.remoteParticipants.size);
          
          // Wait for agent to auto-join via AgentServer pattern
          // Don't use explicit dispatch to avoid duplicate agents
          console.log('⏳ Waiting for agent to auto-join (AgentServer pattern)...');
          setIsAgentJoining(true); // Show "Summoning Luna..."
          
          // Wait up to 5 seconds for agent to join
          let agentJoined = false;
          for (let i = 0; i < 10; i++) {
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Check if agent joined
            agentJoined = Array.from(room.remoteParticipants.values()).some(
              p => p.identity?.toLowerCase().includes('luna') || 
                   p.identity?.toLowerCase().includes('agent') ||
                   p.name === 'Luna'
            );
            
            if (agentJoined) {
              console.log('✅ Agent joined via auto-join');
              setIsAgentJoining(false);
              break;
            }
          }
          
          if (!agentJoined) {
            console.warn('⚠️ Agent did not auto-join after 5 seconds');
            setIsAgentJoining(false);
            // Don't dispatch explicitly - AgentServer should handle it
            // Explicit dispatch causes duplicate agents
          }

      } catch (connectError) {
        console.error('❌ Connection error:', connectError);
        throw connectError;
      }

      // Enable microphone only (no camera needed for voice-only conversation)
      try {
        await room.localParticipant.setMicrophoneEnabled(true);
        console.log('Microphone enabled (voice-only mode)');
        // Track will be available after publication
        localTracksRef.current = [];
      } catch (error) {
        console.error('Error enabling microphone:', error);
        // Continue anyway - user can still listen to agent
        localTracksRef.current = [];
      }

      // Subscribe to existing remote participants' tracks
      room.remoteParticipants.forEach((participant) => {
        console.log('Found remote participant:', participant.identity);
        console.log('  Audio tracks:', participant.audioTracks?.size || 0);
        console.log('  Video tracks:', participant.videoTracks?.size || 0);

        if (participant.audioTracks && participant.audioTracks.size > 0) {
          participant.audioTracks.forEach((publication) => {
            console.log('  Audio track:', publication.trackName, 'subscribed:', publication.isSubscribed);
            if (!publication.isSubscribed) {
              publication.setSubscribed(true);
              console.log('  Subscribed to audio track from', participant.identity);
            }
          });
        } else {
          console.log('  No audio tracks found yet, waiting for TrackPublished event...');
        }
      });

    } catch (error: any) {
      console.error('Error connecting to room:', error);
      alert('Failed to connect: ' + error.message);
      setIsConnecting(false);
      setIsAgentJoining(false);
      cleanup();
    }
  };

  const endCall = async () => {
    if (!roomRef.current) return;

    try {
      console.log('🔌 Disconnecting from room...');
      
      // Stop all local tracks first
      if (roomRef.current.localParticipant) {
        await roomRef.current.localParticipant.setMicrophoneEnabled(false);
        roomRef.current.localParticipant.trackPublications.forEach((publication) => {
          if (publication.track) {
            publication.track.stop();
          }
        });
      }
      
      // Disconnect from room (this will trigger agent to disconnect too)
      await roomRef.current.disconnect();
      console.log('✅ Disconnected from room');
      
      cleanup();
      setIsConnected(false);
      setIsAgentJoining(false);
      addTranscriptEntry('system', 'Call ended');
    } catch (error) {
      console.error('Error disconnecting:', error);
      // Force cleanup even if disconnect fails
      cleanup();
      setIsConnected(false);
      setIsAgentJoining(false);
    }
  };

  const cleanup = () => {
    if (localTracksRef.current && Array.isArray(localTracksRef.current)) {
      localTracksRef.current.forEach(track => {
        try {
          track.stop();
          track.detach();
        } catch (e) {
          console.warn('Error cleaning up track:', e);
        }
      });
    }
    localTracksRef.current = [];
    roomRef.current = null;
  };

  const addTranscriptEntry = (speaker: 'agent' | 'user' | 'system', text: string) => {
    setTranscript(prev => [...prev, { speaker, text, timestamp: new Date() }]);
  };

  // Cleanup on unmount or modal close
  useEffect(() => {
    console.log('🔄 MediatorModal useEffect - isOpen changed:', isOpen, 'conflictId:', conflictId);

    if (!isOpen) {
      console.log('🚪 Modal closed, cleaning up');
      if (roomRef.current) {
        endCall();
      }
      setTranscript([]);
      setIsConnected(false);
      setIsAgentJoining(false);
      agentJoinedRef.current = false; // Reset agent joined flag
    } else {
      console.log('🚪 Modal opened, ready to connect');
      agentJoinedRef.current = false; // Reset when opening modal
      // Don't auto-start - let user click "Start Call" button
    }

    return () => {
      console.log('🧹 MediatorModal cleanup');
      cleanup();
    };
  }, [isOpen, conflictId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col m-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-2xl font-bold text-gray-800">🎙️ Talk to Luna</h2>
            <p className="text-sm text-gray-500 mt-1">Your friendly relationship mediator</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <XIcon size={24} className="text-gray-600" />
          </button>
        </div>

        {/* Status */}
        <div className="px-6 py-3 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${isConnected
                ? 'bg-green-100 text-green-800'
                : 'bg-gray-100 text-gray-600'
              }`}>
              {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
            </div>

            {isAgentJoining && (
              <div className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-800 animate-pulse">
                ✨ Summoning Luna...
              </div>
            )}
          </div>
        </div>

        {/* Transcript */}
        <div className="flex-1 overflow-y-auto p-6 bg-gray-50">
          {transcript.length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-400">
              <div className="text-center">
                <MicIcon size={48} className="mx-auto mb-3 opacity-30" />
                <p className="text-sm">
                  {isConnecting
                    ? 'Connecting to Luna...'
                    : 'Click "Start Call" to begin talking with Luna'}
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {transcript.map((entry, index) => (
                <div
                  key={index}
                  className={`p-3 rounded-lg ${entry.speaker === 'agent'
                    ? 'bg-purple-50 border-l-4 border-purple-400'
                    : entry.speaker === 'user'
                      ? 'bg-blue-50 border-l-4 border-blue-400'
                      : 'bg-gray-100 border-l-4 border-gray-400'
                    }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <span className="font-semibold text-sm text-gray-700">
                        {entry.speaker === 'agent' ? 'Luna' : entry.speaker === 'user' ? 'You' : 'System'}:
                      </span>
                      <p className="text-gray-800 mt-1">{entry.text}</p>
                    </div>
                    <span className="text-xs text-gray-500 ml-2">
                      {entry.timestamp.toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Controls */}
        <div className="p-6 border-t border-gray-200">
          {!isConnected ? (
            <button
              onClick={startCall}
              disabled={isConnecting}
              className="w-full py-3 px-6 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-xl font-semibold hover:from-purple-600 hover:to-pink-600 transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {isConnecting ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                  Connecting...
                </>
              ) : (
                <>
                  <MicIcon size={20} className="mr-2" />
                  Start Call
                </>
              )}
            </button>
          ) : (
            <button
              onClick={endCall}
              className="w-full py-3 px-6 bg-gradient-to-r from-red-500 to-pink-500 text-white rounded-xl font-semibold hover:from-red-600 hover:to-pink-600 transition-all shadow-lg hover:shadow-xl flex items-center justify-center"
            >
              <MicOffIcon size={20} className="mr-2" />
              End Call
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default MediatorModal;

