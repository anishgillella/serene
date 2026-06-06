import React, { useState, useEffect, useRef } from 'react';
import { Room, RoomEvent, RemoteParticipant, LocalParticipant } from 'livekit-client';
import { XIcon, MicIcon, MicOffIcon, Moon } from 'lucide-react';
import { usePartnerContext } from '../contexts/PartnerContext';
import { useRelationship } from '../contexts/RelationshipContext';
import { useMossContextEvents } from '../hooks/useMossContextEvents';
import MossResultsPanel from './voice/MossResultsPanel';

interface MediatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  conflictId: string;
  context?: {
    activeView?: 'analysis' | 'repair' | 'chat' | null;
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
  const { partnerRole, partnerName } = usePartnerContext();
  const { relationshipId } = useRelationship();
  const [isConnected, setIsConnected] = useState(false);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isAgentJoining, setIsAgentJoining] = useState(false);
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
  const [activeRoom, setActiveRoom] = useState<Room | null>(null);
  const roomRef = useRef<Room | null>(null);
  const localTracksRef = useRef<any[]>([]);
  const agentJoinedRef = useRef<boolean>(false);

  const { events: mossEvents, latest: mossLatest, clear: clearMossEvents } = useMossContextEvents(activeRoom);

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8100';

  const generateToken = async (conflictId: string) => {
    console.log('🔑 generateToken called with conflictId:', conflictId);
    console.log('🌐 API_BASE_URL:', API_BASE_URL);

    try {
      const requestBody = {
        conflict_id: conflictId,
        participant_name: partnerName || 'user',
        partner_role: partnerRole,
        relationship_id: relationshipId || undefined,
        user_id: partnerName || 'user',
      };
      console.log('📤 Sending token request:', requestBody);

      const response = await fetch(`${API_BASE_URL}/api/mediator/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
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
      setActiveRoom(room);

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
        setIsAgentSpeaking(false);
        agentJoinedRef.current = false;
        addTranscriptEntry('system', 'Disconnected from Luna');
        cleanup();
      });

      room.on(RoomEvent.ParticipantDisconnected, (participant) => {
        console.log('Participant disconnected:', participant.identity);
        const isAgent = participant.identity.startsWith('agent-') || participant.name === 'Luna';
        if (isAgent) {
          console.log('✅ Agent (Luna) disconnected');
          addTranscriptEntry('system', 'Luna has left');
          setIsAgentSpeaking(false);
        }
      });

      room.on(RoomEvent.ParticipantConnected, (participant) => {
        console.log('Participant connected:', participant.identity, 'name:', participant.name);
        const isAgent = participant.identity.startsWith('agent-') || participant.name === 'Luna';
        const displayName = isAgent ? 'Luna' : participant.identity;

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
          console.log('✅ Subscribing to audio track from', participant.identity);
          publication.setSubscribed(true);
        }
      });

      room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
        console.log('🎧 Track subscribed:', track.kind, 'from', participant.identity);
        if (track.kind === 'audio') {
          const audioElement = track.attach();

          // Add event listeners to detect when agent is speaking
          const isAgent = participant.identity.startsWith('agent-') || participant.name === 'Luna';
          if (isAgent) {
            audioElement.addEventListener('play', () => {
              console.log('🎤 Agent started speaking');
              setIsAgentSpeaking(true);
            });

            audioElement.addEventListener('pause', () => {
              console.log('🔇 Agent stopped speaking');
              setIsAgentSpeaking(false);
            });

            audioElement.addEventListener('ended', () => {
              console.log('🔇 Agent finished speaking');
              setIsAgentSpeaking(false);
            });
          }

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

      console.log('🔌 Connecting to room:', { url, roomName: `mediator-${conflictId}`, tokenLength: token.length });
      try {
        await room.connect(url, token);
        console.log('✅ Connected to room:', room.name);
        console.log('👥 Remote participants:', room.remoteParticipants.size);

        console.log('⏳ Dispatching agent to room...');
        setIsAgentJoining(true);

        // Explicitly dispatch the agent
        try {
          const dispatchResponse = await fetch(`${API_BASE_URL}/api/dispatch-agent`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'ngrok-skip-browser-warning': 'true'
            },
            body: JSON.stringify({
              room_name: room.name
            })
          });

          if (!dispatchResponse.ok) {
            console.warn('⚠️ Dispatch request failed, agent might not join automatically');
          } else {
            console.log('✅ Agent dispatched successfully');
          }
        } catch (dispatchError) {
          console.error('❌ Error dispatching agent:', dispatchError);
        }

        let agentJoined = false;
        for (let i = 0; i < 20; i++) { // Increased wait time to 10s
          await new Promise(resolve => setTimeout(resolve, 500));

          agentJoined = Array.from(room.remoteParticipants.values()).some(
            p => p.identity?.toLowerCase().includes('luna') ||
              p.identity?.toLowerCase().includes('agent') ||
              p.name === 'Luna'
          );

          if (agentJoined) {
            console.log('✅ Agent joined');
            setIsAgentJoining(false);
            break;
          }
        }

        if (!agentJoined) {
          console.warn('⚠️ Agent did not join after 10 seconds');
          setIsAgentJoining(false);
        }

      } catch (connectError) {
        console.error('❌ Connection error:', connectError);
        throw connectError;
      }

      try {
        await room.localParticipant.setMicrophoneEnabled(true);
        console.log('Microphone enabled (voice-only mode)');
        localTracksRef.current = [];
      } catch (error) {
        console.error('Error enabling microphone:', error);
        localTracksRef.current = [];
      }

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

      if (roomRef.current.localParticipant) {
        await roomRef.current.localParticipant.setMicrophoneEnabled(false);
        roomRef.current.localParticipant.trackPublications.forEach((publication) => {
          if (publication.track) {
            publication.track.stop();
          }
        });
      }

      await roomRef.current.disconnect();
      console.log('✅ Disconnected from room');

      cleanup();
      setIsConnected(false);
      setIsAgentJoining(false);
      setIsAgentSpeaking(false);
      addTranscriptEntry('system', 'Call ended');
    } catch (error) {
      console.error('Error disconnecting:', error);
      cleanup();
      setIsConnected(false);
      setIsAgentJoining(false);
      setIsAgentSpeaking(false);
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
    setActiveRoom(null);
  };

  const addTranscriptEntry = (speaker: 'agent' | 'user' | 'system', text: string) => {
    setTranscript(prev => [...prev, { speaker, text, timestamp: new Date() }]);
  };

  useEffect(() => {
    console.log('🔄 MediatorModal useEffect - isOpen changed:', isOpen, 'conflictId:', conflictId);

    if (!isOpen) {
      console.log('🚪 Modal closed, cleaning up');
      if (roomRef.current) {
        endCall();
      }
      setTranscript([]);
      clearMossEvents();
      setIsConnected(false);
      setIsAgentJoining(false);
      setIsAgentSpeaking(false);
      agentJoinedRef.current = false;
    } else {
      console.log('🚪 Modal opened, ready to connect');
      if (isConnected && roomRef.current) {
        console.log('⚠️ Conflict ID changed while connected, disconnecting old room...');
        endCall();
      }
      agentJoinedRef.current = false;
    }

    return () => {
      console.log('🧹 MediatorModal cleanup');
      cleanup();
    };
  }, [isOpen, conflictId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md px-4">
      <div className="bg-surface-elevated rounded-3xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden border border-border-subtle">
        {/* Header with gradient */}
        <div className="relative p-8 pb-6 bg-gradient-to-br from-accent/5 via-surface-elevated to-surface-elevated border-b border-border-subtle">
          <button
            onClick={async () => {
              if (isConnected && roomRef.current) {
                await endCall();
              }
              onClose();
            }}
            className="absolute top-6 right-6 p-2 hover:bg-surface-hover rounded-xl transition-colors"
          >
            <XIcon size={24} className="text-text-tertiary hover:text-text-primary transition-colors" />
          </button>

          <div className="flex items-center gap-4 mb-4">
            <div className="w-14 h-14 rounded-2xl bg-accent/10 flex items-center justify-center">
              <Moon size={28} className="text-accent fill-accent/20" />
            </div>
            <div>
              <h2 className="text-h2 font-semibold text-text-primary">Talk to Luna</h2>
              <p className="text-small text-text-secondary mt-1">Your AI relationship mediator</p>
            </div>
          </div>

          {/* Status badges */}
          <div className="flex flex-wrap items-center gap-2">
            <div className={`inline-flex items-center px-3 py-1.5 rounded-full text-tiny font-medium transition-all ${isConnected
              ? 'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20'
              : 'bg-surface-hover text-text-tertiary border border-border-subtle'
              }`}>
              <div className={`w-2 h-2 rounded-full mr-2 ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-text-tertiary'}`}></div>
              {isConnected ? 'Connected' : 'Disconnected'}
            </div>

            {isAgentJoining && (
              <div className="inline-flex items-center px-3 py-1.5 rounded-full text-tiny font-medium bg-accent/10 text-accent border border-accent/20 animate-pulse">
                <div className="w-2 h-2 rounded-full mr-2 bg-accent animate-ping"></div>
                Summoning Luna...
              </div>
            )}

            {isAgentSpeaking && (
              <div className="inline-flex items-center px-3 py-1.5 rounded-full text-tiny font-medium bg-accent/10 text-accent border border-accent/20">
                <div className="flex items-center gap-1 mr-2">
                  <div className="w-1 h-3 bg-accent rounded-full animate-[pulse_0.6s_ease-in-out_infinite]"></div>
                  <div className="w-1 h-4 bg-accent rounded-full animate-[pulse_0.6s_ease-in-out_0.1s_infinite]"></div>
                  <div className="w-1 h-2 bg-accent rounded-full animate-[pulse_0.6s_ease-in-out_0.2s_infinite]"></div>
                  <div className="w-1 h-4 bg-accent rounded-full animate-[pulse_0.6s_ease-in-out_0.3s_infinite]"></div>
                </div>
                Luna is speaking...
              </div>
            )}
          </div>
        </div>

        {/* Transcript + Moss retrieval panel */}
        <div className="flex-1 flex overflow-hidden min-h-0">
          <div className="flex-1 overflow-y-auto p-6 bg-gradient-to-b from-bg-primary to-surface-elevated">
            {transcript.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className={`w-24 h-24 mx-auto mb-6 rounded-3xl bg-accent/5 flex items-center justify-center ${isConnecting ? 'animate-pulse' : ''
                    }`}>
                    <MicIcon size={48} className="text-accent/40" />
                  </div>
                  <p className="text-body text-text-secondary">
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
                    className={`p-4 rounded-2xl transition-all ${entry.speaker === 'agent'
                      ? 'bg-accent/5 border border-accent/10 ml-0 mr-8'
                      : entry.speaker === 'user'
                        ? 'bg-surface-hover border border-border-subtle ml-8 mr-0'
                        : 'bg-white/40 border border-border-subtle mx-8'
                      }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-tiny font-semibold text-text-secondary">
                            {entry.speaker === 'agent' ? '🌙 Luna' : entry.speaker === 'user' ? '👤 You' : '💬 System'}
                          </span>
                          <span className="text-tiny text-text-tertiary">
                            {entry.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                        <p className="text-body text-text-primary leading-relaxed">{entry.text}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="w-64 border-l border-border-subtle bg-surface-elevated/50 hidden md:flex flex-col">
            <MossResultsPanel latest={mossLatest} events={mossEvents} />
          </div>
        </div>

        {/* Controls */}
        <div className="p-6 border-t border-border-subtle bg-surface-elevated">
          {!isConnected ? (
            <button
              onClick={startCall}
              disabled={isConnecting}
              className="w-full py-4 px-6 bg-accent text-white rounded-2xl font-semibold hover:bg-accent/90 transition-all shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center group"
            >
              {isConnecting ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent mr-3"></div>
                  Connecting...
                </>
              ) : (
                <>
                  <MicIcon size={20} className="mr-3 group-hover:scale-110 transition-transform" />
                  Start Call
                </>
              )}
            </button>
          ) : (
            <button
              onClick={endCall}
              className="w-full py-4 px-6 bg-rose-500 text-white rounded-2xl font-semibold hover:bg-rose-600 transition-all shadow-lg hover:shadow-xl flex items-center justify-center group"
            >
              <MicOffIcon size={20} className="mr-3 group-hover:scale-110 transition-transform" />
              End Call
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default MediatorModal;
