import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import ParticipantBadge from '../components/ParticipantBadge';
import { MicOffIcon } from 'lucide-react';

interface TranscriptMessage {
  type: string;
  text: string;
  is_final?: boolean;
}

const FightCapture = () => {
  const navigate = useNavigate();
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState<string[]>([]); // Final transcripts only
  const [interimTranscript, setInterimTranscript] = useState<string>(''); // Current partial transcript
  const [error, setError] = useState<string>('');
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  
  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Start recording when component mounts
  useEffect(() => {
    const startRecording = async () => {
      try {
        setConnectionStatus('connecting');
        setError('');
        
        const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
        const wsUrl = apiUrl.replace('http://', 'ws://').replace('https://', 'wss://');
        const fullWsUrl = `${wsUrl}/api/realtime/transcribe`;
        
        console.log('🔗 Connecting to WebSocket:', fullWsUrl);
        
        // Connect to WebSocket
        const ws = new WebSocket(fullWsUrl);
        wsRef.current = ws;
        
        ws.onopen = async () => {
          console.log('✅ WebSocket connected');
          setConnectionStatus('connected');
          setIsRecording(true);
          
          // Request microphone access
          try {
            const stream = await navigator.mediaDevices.getUserMedia({ 
              audio: {
                sampleRate: 16000,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true,
              }
            });
            
            streamRef.current = stream;
            
            // Use AudioContext to capture raw PCM audio
            const audioContext = new AudioContext({ sampleRate: 16000 });
            const source = audioContext.createMediaStreamSource(stream);
            const processor = audioContext.createScriptProcessor(4096, 1, 1);
            
            processor.onaudioprocess = (event) => {
              if (ws.readyState === WebSocket.OPEN) {
                const inputData = event.inputBuffer.getChannelData(0);
                // Convert Float32Array to Int16Array (PCM format)
                const pcmData = new Int16Array(inputData.length);
                for (let i = 0; i < inputData.length; i++) {
                  // Clamp and convert to 16-bit PCM
                  const s = Math.max(-1, Math.min(1, inputData[i]));
                  pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                }
                // Send PCM data as binary
                ws.send(pcmData.buffer);
              }
            };
            
            source.connect(processor);
            processor.connect(audioContext.destination);
            
            console.log('🎤 Started recording with AudioContext');
            
          } catch (micError) {
            console.error('Microphone error:', micError);
            setError('Failed to access microphone. Please allow microphone access.');
            setConnectionStatus('disconnected');
          }
        };
        
        ws.onmessage = (event) => {
          try {
            const data: TranscriptMessage = JSON.parse(event.data);
            
            if (data.type === 'transcript' && data.text) {
              console.log('📝 Transcript received:', data.text, 'final:', data.is_final);
              
              if (data.is_final) {
                // Final transcript: add to permanent list and clear interim
                setTranscript((prev) => [...prev, `You: ${data.text}`]);
                setInterimTranscript(''); // Clear interim when final arrives
              } else {
                // Interim transcript: update temporary display only
                setInterimTranscript(data.text);
              }
            } else if (data.type === 'error') {
              setError(data.text || 'Transcription error');
            }
          } catch (e) {
            console.error('Failed to parse transcript:', e);
          }
        };
        
        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          setError('Connection error. Please try again.');
          setConnectionStatus('disconnected');
        };
        
        ws.onclose = () => {
          console.log('WebSocket closed');
          setConnectionStatus('disconnected');
          setIsRecording(false);
          setInterimTranscript(''); // Clear interim transcript on disconnect
        };
        
      } catch (e) {
        console.error('Failed to start recording:', e);
        setError(`Failed to start: ${e}`);
        setConnectionStatus('disconnected');
      }
    };

    startRecording();

    // Cleanup on unmount
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const handleEndCapture = () => {
    setIsRecording(false);
    
    // Stop recording
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    
    // Stop microphone
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
    
    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close();
    }
    
    // Navigate to post-fight after a short delay, passing transcript data
    setTimeout(() => {
      navigate('/post-fight', { 
        state: { 
          transcript: transcript,
          interimTranscript: interimTranscript 
        } 
      });
    }, 500);
  };

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[80vh] py-8">
        <div className="bg-red-100 text-red-600 p-4 rounded-xl max-w-md">
          <p className="font-medium">Error</p>
          <p className="text-sm mt-1">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg text-sm"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-between min-h-[80vh] py-8">
      <div className="w-full">
        <div className="mb-6 flex justify-center">
          <div className={`py-1 px-4 rounded-full text-sm font-medium flex items-center ${
            connectionStatus === 'connected' 
              ? 'bg-green-400 text-white' 
              : connectionStatus === 'connecting'
              ? 'bg-yellow-400 text-white'
              : 'bg-gray-400 text-white'
          }`}>
            <div className={`w-2 h-2 rounded-full mr-2 ${
              connectionStatus === 'connected' ? 'bg-white animate-pulse' : 'bg-white'
            }`}></div>
            {connectionStatus === 'connecting' && 'Connecting...'}
            {connectionStatus === 'connected' && isRecording && 'Recording conflict...'}
            {connectionStatus === 'disconnected' && 'Disconnected'}
          </div>
        </div>

        <div className="space-y-1 mb-8">
          <ParticipantBadge name="Partner A (you)" isActive={isRecording} />
          <ParticipantBadge name="Partner B" isActive={false} />
          <ParticipantBadge name="HeartSync" isSilent={true} />
        </div>

        {(transcript.length > 0 || interimTranscript) && (
          <div className="bg-white/40 backdrop-blur-sm rounded-xl p-4 mb-8 max-h-60 overflow-y-auto">
            <p className="text-xs text-gray-500 mb-2 font-medium">Live transcript</p>
            {transcript.map((line, index) => (
              <p key={index} className="text-sm text-gray-700 mb-2">
                {line}
              </p>
            ))}
            {interimTranscript && (
              <p className="text-sm text-gray-500 mb-2 italic opacity-70">
                You: {interimTranscript}
              </p>
            )}
          </div>
        )}

        {transcript.length === 0 && !interimTranscript && connectionStatus === 'connected' && (
          <div className="bg-white/40 backdrop-blur-sm rounded-xl p-4 mb-8 text-center">
            <p className="text-sm text-gray-500">
              🎤 Listening... Start speaking to see the transcript.
            </p>
          </div>
        )}

        {connectionStatus === 'connecting' && (
          <div className="bg-white/40 backdrop-blur-sm rounded-xl p-4 mb-8 text-center">
            <p className="text-sm text-gray-500">
              Connecting to transcription service...
            </p>
          </div>
        )}
      </div>

      <button
        onClick={handleEndCapture}
        disabled={!isRecording}
        className="w-full max-w-xs py-3 px-4 bg-rose-100 hover:bg-rose-200 rounded-xl flex items-center justify-center transition-all shadow-soft hover:shadow-cozy text-rose-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <MicOffIcon size={18} className="mr-2" />
        End Fight Capture
      </button>
    </div>
  );
};

export default FightCapture;
