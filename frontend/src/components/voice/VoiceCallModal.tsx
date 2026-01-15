/**
 * VoiceCallModal - Beautiful voice call interface for Luna
 * Uses VAPI for voice AI
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { X, Mic, MicOff, Phone, PhoneOff } from 'lucide-react';
import Vapi from '@vapi-ai/web';

interface VoiceCallModalProps {
  isOpen: boolean;
  onClose: () => void;
  conflictId: string;
  relationshipId: string;
  partnerAName: string;
  partnerBName: string;
}

interface TranscriptMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

type CallStatus = 'idle' | 'connecting' | 'connected' | 'speaking' | 'listening' | 'ended' | 'error';

const VoiceCallModal: React.FC<VoiceCallModalProps> = ({
  isOpen,
  onClose,
  conflictId,
  relationshipId,
  partnerAName,
  partnerBName,
}) => {
  const [callStatus, setCallStatus] = useState<CallStatus>('idle');
  const [isMuted, setIsMuted] = useState(false);
  const [callDuration, setCallDuration] = useState(0);
  const [transcript, setTranscript] = useState<TranscriptMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [volumeLevel, setVolumeLevel] = useState(0);

  const vapiRef = useRef<Vapi | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  // Initialize VAPI
  useEffect(() => {
    const publicKey = import.meta.env.VITE_VAPI_PUBLIC_KEY;
    if (publicKey) {
      vapiRef.current = new Vapi(publicKey);
      setupEventListeners();
    }

    return () => {
      if (vapiRef.current) {
        vapiRef.current.stop();
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  // Auto-scroll transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript]);

  // Setup VAPI event listeners
  const setupEventListeners = useCallback(() => {
    if (!vapiRef.current) return;

    vapiRef.current.on('call-start', () => {
      console.log('Call started');
      setCallStatus('connected');
      setError(null);
      // Start timer
      timerRef.current = setInterval(() => {
        setCallDuration(prev => prev + 1);
      }, 1000);
    });

    vapiRef.current.on('call-end', () => {
      console.log('Call ended');
      setCallStatus('ended');
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    });

    vapiRef.current.on('speech-start', () => {
      setCallStatus('speaking');
    });

    vapiRef.current.on('speech-end', () => {
      setCallStatus('listening');
    });

    vapiRef.current.on('volume-level', (level: number) => {
      setVolumeLevel(level);
    });

    vapiRef.current.on('message', (message: any) => {
      if (message.type === 'transcript') {
        const role = message.role as 'user' | 'assistant';
        const content = message.transcript;

        if (content && content.trim()) {
          setTranscript(prev => {
            // Update last message if same role, otherwise add new
            const last = prev[prev.length - 1];
            if (last && last.role === role && message.transcriptType === 'partial') {
              return [...prev.slice(0, -1), { ...last, content }];
            }
            if (message.transcriptType === 'final') {
              // Remove partial and add final
              const withoutPartial = prev.filter(
                (m, i) => !(i === prev.length - 1 && m.role === role)
              );
              return [...withoutPartial, { role, content, timestamp: new Date() }];
            }
            return [...prev, { role, content, timestamp: new Date() }];
          });
        }
      }
    });

    vapiRef.current.on('error', (err: any) => {
      console.error('VAPI error:', err);
      setError(err.message || 'An error occurred');
      setCallStatus('error');
    });
  }, []);

  // Start call
  const startCall = async () => {
    if (!vapiRef.current) {
      setError('Voice service not initialized');
      return;
    }

    const assistantId = import.meta.env.VITE_VAPI_ASSISTANT_ID;
    if (!assistantId) {
      setError('Assistant not configured');
      return;
    }

    setCallStatus('connecting');
    setTranscript([]);
    setCallDuration(0);
    setError(null);

    try {
      await vapiRef.current.start(assistantId, {
        metadata: {
          conflict_id: conflictId,
          relationship_id: relationshipId,
          partner_a_name: partnerAName,
          partner_b_name: partnerBName,
        },
        assistantOverrides: {
          firstMessage: `Hey ${partnerAName}! I'm Luna. What's on your mind?`,
        },
      });
    } catch (err: any) {
      console.error('Failed to start call:', err);
      setError(err.message || 'Failed to start call');
      setCallStatus('error');
    }
  };

  // End call
  const endCall = () => {
    if (vapiRef.current) {
      vapiRef.current.stop();
    }
    setCallStatus('ended');
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
  };

  // Toggle mute
  const toggleMute = () => {
    if (vapiRef.current) {
      vapiRef.current.setMuted(!isMuted);
      setIsMuted(!isMuted);
    }
  };

  // Format time
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Close modal and cleanup
  const handleClose = () => {
    if (callStatus === 'connected' || callStatus === 'speaking' || callStatus === 'listening') {
      endCall();
    }
    setCallStatus('idle');
    setTranscript([]);
    setCallDuration(0);
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 bg-gradient-to-br from-rose-50 via-purple-50 to-indigo-50 rounded-3xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="relative px-6 pt-6 pb-4">
          <button
            onClick={handleClose}
            className="absolute top-4 right-4 p-2 rounded-full hover:bg-white/50 transition-colors"
          >
            <X size={20} className="text-gray-500" />
          </button>

          {/* Timer */}
          {(callStatus === 'connected' || callStatus === 'speaking' || callStatus === 'listening') && (
            <div className="absolute top-4 left-6 text-sm font-medium text-gray-500">
              {formatTime(callDuration)}
            </div>
          )}
        </div>

        {/* Main Content */}
        <div className="px-6 pb-6">
          {/* Luna Avatar / Visualization */}
          <div className="flex flex-col items-center mb-6">
            {/* Animated Orb */}
            <div className="relative w-32 h-32 mb-4">
              {/* Outer glow */}
              <div
                className={`absolute inset-0 rounded-full bg-gradient-to-br from-rose-300 to-purple-400 blur-xl opacity-50 transition-all duration-300 ${
                  callStatus === 'speaking' ? 'scale-110 opacity-70' :
                  callStatus === 'listening' ? 'scale-100 opacity-40 animate-pulse' :
                  'scale-90 opacity-30'
                }`}
              />

              {/* Main orb */}
              <div
                className={`absolute inset-2 rounded-full bg-gradient-to-br from-rose-400 via-purple-400 to-indigo-400 shadow-lg transition-all duration-300 ${
                  callStatus === 'speaking' ? 'scale-105' :
                  callStatus === 'listening' ? 'scale-100' :
                  'scale-95'
                }`}
              >
                {/* Inner highlight */}
                <div className="absolute inset-4 rounded-full bg-gradient-to-br from-white/40 to-transparent" />

                {/* Waveform visualization */}
                {(callStatus === 'speaking' || callStatus === 'listening') && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="flex items-end gap-1 h-8">
                      {[...Array(5)].map((_, i) => (
                        <div
                          key={i}
                          className="w-1 bg-white/80 rounded-full transition-all duration-150"
                          style={{
                            height: callStatus === 'speaking'
                              ? `${Math.max(8, Math.min(32, volumeLevel * 40 + Math.random() * 10))}px`
                              : `${8 + Math.sin(Date.now() / 200 + i) * 4}px`,
                            animationDelay: `${i * 100}ms`,
                          }}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* Connecting spinner */}
                {callStatus === 'connecting' && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-8 h-8 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  </div>
                )}
              </div>
            </div>

            {/* Status Text */}
            <h2 className="text-xl font-semibold text-gray-800 mb-1">Luna</h2>
            <p className="text-sm text-gray-500">
              {callStatus === 'idle' && 'Your AI relationship mediator'}
              {callStatus === 'connecting' && 'Connecting...'}
              {callStatus === 'connected' && 'Connected'}
              {callStatus === 'speaking' && 'Luna is speaking...'}
              {callStatus === 'listening' && 'Listening to you...'}
              {callStatus === 'ended' && 'Call ended'}
              {callStatus === 'error' && 'Connection error'}
            </p>
          </div>

          {/* Transcript */}
          {transcript.length > 0 && (
            <div className="bg-white/60 backdrop-blur rounded-2xl p-4 mb-6 max-h-48 overflow-y-auto">
              <div className="space-y-3">
                {transcript.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[85%] px-4 py-2 rounded-2xl text-sm ${
                        msg.role === 'user'
                          ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-br-md'
                          : 'bg-gradient-to-r from-rose-100 to-purple-100 text-gray-800 rounded-bl-md'
                      }`}
                    >
                      {msg.content}
                    </div>
                  </div>
                ))}
                <div ref={transcriptEndRef} />
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Controls */}
          <div className="flex items-center justify-center gap-4">
            {callStatus === 'idle' || callStatus === 'ended' || callStatus === 'error' ? (
              <button
                onClick={startCall}
                className="flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-rose-500 to-purple-500 hover:from-rose-600 hover:to-purple-600 text-white rounded-full font-medium shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105"
              >
                <Phone size={20} />
                <span>Start Call</span>
              </button>
            ) : (
              <>
                {/* Mute Button */}
                <button
                  onClick={toggleMute}
                  disabled={callStatus === 'connecting'}
                  className={`p-4 rounded-full transition-all duration-200 ${
                    isMuted
                      ? 'bg-red-100 text-red-600 hover:bg-red-200'
                      : 'bg-white/80 text-gray-600 hover:bg-white'
                  } shadow-md hover:shadow-lg disabled:opacity-50`}
                >
                  {isMuted ? <MicOff size={24} /> : <Mic size={24} />}
                </button>

                {/* End Call Button */}
                <button
                  onClick={endCall}
                  className="p-4 bg-red-500 hover:bg-red-600 text-white rounded-full shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105"
                >
                  <PhoneOff size={24} />
                </button>
              </>
            )}
          </div>

          {/* Hint Text */}
          {callStatus === 'idle' && (
            <p className="text-center text-xs text-gray-400 mt-4">
              Click to start talking with Luna about this conflict
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default VoiceCallModal;
