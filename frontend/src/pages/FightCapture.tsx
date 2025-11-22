import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import ParticipantBadge from '../components/ParticipantBadge';
import { MicOffIcon } from 'lucide-react';

interface TranscriptMessage {
  type: string;
  text: string;
  speaker?: string; // Speaker name from diarization (e.g., "Speaker 1", "Speaker 2")
  is_final?: boolean;
}

interface TranscriptItem {
  speaker: string;
  text: string;
}

const FightCapture = () => {
  const navigate = useNavigate();
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]); // Final transcripts with speaker info
  const [interimTranscript, setInterimTranscript] = useState<TranscriptItem | null>(null); // Current partial transcript
  const [error, setError] = useState<string>('');
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  
  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]); // Store audio chunks for post-processing

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
            
            // Also record audio with MediaRecorder for post-processing diarization
            const mediaRecorder = new MediaRecorder(stream, {
              mimeType: 'audio/webm;codecs=opus'
            });
            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];
            
            mediaRecorder.ondataavailable = (event) => {
              if (event.data.size > 0) {
                audioChunksRef.current.push(event.data);
              }
            };
            
            mediaRecorder.start(1000); // Collect data every second
            console.log('🎙️ Started MediaRecorder for post-processing');
            
            // Use AudioContext to capture raw PCM audio for real-time streaming
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
              const speakerName = data.speaker || 'Boyfriend'; // Use speaker from diarization
              console.log('📝 Transcript received:', speakerName, ':', data.text, 'final:', data.is_final);
              
              if (data.is_final) {
                // Final transcript: add to permanent list and clear interim
                setTranscript((prev) => [...prev, { speaker: speakerName, text: data.text }]);
                setInterimTranscript(null); // Clear interim when final arrives
              } else {
                // Interim transcript: update temporary display only
                setInterimTranscript({ speaker: speakerName, text: data.text });
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
          setInterimTranscript(null); // Clear interim transcript on disconnect
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

  const handleEndCapture = async () => {
    setIsRecording(false);
    
    // Stop WebSocket first
    if (wsRef.current) {
      wsRef.current.close();
    }
    
    // Stop MediaRecorder and process audio for accurate diarization
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      
      // Wait for recording to finish
      await new Promise<void>((resolve) => {
        if (mediaRecorderRef.current) {
          mediaRecorderRef.current.onstop = () => {
            resolve();
          };
        } else {
          resolve();
        }
      });
      
      // Combine audio chunks
      if (audioChunksRef.current.length > 0) {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        
        // Send to REST API for accurate diarization
        try {
          const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
          const formData = new FormData();
          formData.append('audio_file', audioBlob, 'recording.webm');
          
          console.log('🔄 Sending audio to REST API for accurate diarization...');
          const response = await fetch(`${apiUrl}/api/transcription/transcribe`, {
            method: 'POST',
            body: formData,
          });
          
          if (response.ok) {
            const result = await response.json();
            console.log('✅ Received diarized transcript:', result);
            
            // Update transcripts with accurate speaker labels
            if (result.utterances && result.utterances.length > 0) {
              const diarizedTranscripts: TranscriptItem[] = result.utterances.map((utt: any) => {
                // Map Deepgram speaker IDs: 0 -> Boyfriend, 1 -> Girlfriend
                const speakerName = utt.speaker === 0 ? 'Boyfriend' : 'Girlfriend';
                return { speaker: speakerName, text: utt.transcript };
              });
              
              // Replace current transcripts with accurate ones
              setTranscript(diarizedTranscripts);
              console.log('✅ Updated transcripts with accurate speaker labels');
            }
          }
        } catch (error) {
          console.error('❌ Error processing audio with REST API:', error);
          // Continue anyway with existing transcripts
        }
      }
    }
    
    // Stop microphone
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
    
    // Navigate to post-fight after processing
    setTimeout(() => {
      // Convert transcript items back to string format for post-fight page compatibility
      const transcriptStrings = transcript.map(item => `${item.speaker}: ${item.text}`);
      navigate('/post-fight', { 
        state: { 
          transcript: transcriptStrings,
          interimTranscript: interimTranscript ? `${interimTranscript.speaker}: ${interimTranscript.text}` : ''
        } 
      });
    }, 1000);
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
            <p className="text-xs text-gray-500 mb-3 font-medium">Live transcript</p>
            <div className="space-y-2">
              {transcript.map((item, index) => {
                const isBoyfriend = item.speaker === 'Boyfriend';
                return (
                  <div key={index} className={`flex w-full ${isBoyfriend ? 'justify-start' : 'justify-end'}`}>
                    <div className={`rounded-2xl py-2 px-4 max-w-[80%] ${
                      isBoyfriend 
                        ? 'bg-blue-100 text-gray-800' 
                        : 'bg-pink-100 text-gray-800'
                    }`}>
                      <div className="text-xs font-semibold mb-1 text-gray-600">
                        {item.speaker}
                      </div>
                      <div className="text-sm">{item.text}</div>
                    </div>
                  </div>
                );
              })}
              {interimTranscript && (
                <div className={`flex w-full ${interimTranscript.speaker === 'Boyfriend' ? 'justify-start' : 'justify-end'}`}>
                  <div className={`rounded-2xl py-2 px-4 max-w-[80%] opacity-70 ${
                    interimTranscript.speaker === 'Boyfriend'
                      ? 'bg-blue-100 text-gray-800'
                      : 'bg-pink-100 text-gray-800'
                  }`}>
                    <div className="text-xs font-semibold mb-1 text-gray-600">
                      {interimTranscript.speaker}
                    </div>
                    <div className="text-sm italic">{interimTranscript.text}</div>
                  </div>
                </div>
              )}
            </div>
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
