import React, { useState, useEffect, useRef } from 'react';

interface TranscriptItem {
  role: 'user' | 'assistant' | 'system';
  text: string;
  isFinal: boolean;
}

export const CallInterface: React.FC = () => {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [status, setStatus] = useState<'idle' | 'calling' | 'connected' | 'ended'>('idle');
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
  const WS_URL = BACKEND_URL.replace('http', 'ws') + '/api/events';

  useEffect(() => {
    // Connect to WebSocket for events
    const connectWs = () => {
      const ws = new WebSocket(WS_URL);
      
      ws.onopen = () => {
        console.log('Connected to event stream');
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'transcript') {
            setTranscript(prev => [...prev, message.data]);
            setStatus('connected');
          }
        } catch (e) {
          console.error('Failed to parse WS message', e);
        }
      };

      ws.onclose = () => {
        console.log('Disconnected from event stream');
        // Reconnect logic could go here
      };

      wsRef.current = ws;
    };

    connectWs();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [WS_URL]);

  useEffect(() => {
    // Auto-scroll to bottom of transcript
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript]);

  const handleCall = async () => {
    if (!phoneNumber) {
      setError('Please enter a phone number');
      return;
    }
    
    setStatus('calling');
    setError(null);
    setTranscript([]); // Clear previous transcript

    try {
      const response = await fetch(`${BACKEND_URL}/api/call`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ phoneNumber }),
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to initiate call');
      }
      
      console.log('Call initiated:', data.callSid);
      // Status will update to 'connected' when we receive the first event
      
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : 'An error occurred');
      setStatus('idle');
    }
  };

  return (
    <div className="flex flex-col h-full max-w-md mx-auto bg-gray-900 text-white rounded-xl shadow-2xl overflow-hidden border border-gray-800">
      {/* Header */}
      <div className="p-6 bg-gray-800 border-b border-gray-700">
        <h2 className="text-xl font-semibold text-center text-purple-400">Serene Voice Agent</h2>
        <p className="text-xs text-center text-gray-400 mt-1">Relationship Mediator</p>
      </div>

      {/* Transcript Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-900 min-h-[400px]">
        {transcript.length === 0 && status === 'idle' && (
          <div className="text-center text-gray-500 mt-20">
            <p>Ready to help you understand Amara.</p>
            <p className="text-sm mt-2">Enter your number to start.</p>
          </div>
        )}
        
        {transcript.map((item, index) => (
          <div 
            key={index} 
            className={`flex ${item.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div 
              className={`max-w-[80%] p-3 rounded-2xl text-sm ${
                item.role === 'user' 
                  ? 'bg-purple-600 text-white rounded-br-none' 
                  : 'bg-gray-700 text-gray-100 rounded-bl-none'
              }`}
            >
              {item.text}
            </div>
          </div>
        ))}
        <div ref={transcriptEndRef} />
      </div>

      {/* Controls */}
      <div className="p-6 bg-gray-800 border-t border-gray-700">
        {error && (
          <div className="mb-4 p-2 bg-red-900/50 text-red-200 text-xs rounded text-center">
            {error}
          </div>
        )}
        
        <div className="flex flex-col space-y-4">
          {status === 'idle' || status === 'ended' ? (
            <>
              <input
                type="tel"
                placeholder="+1 (555) 000-0000"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                className="w-full p-3 bg-gray-900 border border-gray-600 rounded-lg focus:outline-none focus:border-purple-500 text-center text-lg"
              />
              <button
                onClick={handleCall}
                className="w-full py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 rounded-lg font-medium transition-all shadow-lg shadow-purple-900/20"
              >
                Start Call
              </button>
            </>
          ) : (
            <div className="text-center space-y-4">
              <div className="animate-pulse text-purple-400 font-medium">
                {status === 'calling' ? 'Calling your phone...' : 'Call in progress'}
              </div>
              <button
                onClick={() => window.location.reload()} // Simple reset for now
                className="px-6 py-2 bg-gray-700 hover:bg-gray-600 rounded-full text-sm transition-colors"
              >
                End Session
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
