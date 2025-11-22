import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import VoiceButton from '../components/VoiceButton';
import TranscriptBubble from '../components/TranscriptBubble';
import { BarChart4Icon, RefreshCwIcon, FileTextIcon } from 'lucide-react';

interface LocationState {
  transcript?: string[];
  interimTranscript?: string;
}

const PostFightSession = () => {
  const location = useLocation();
  const state = location.state as LocationState | null;
  
  const [isListening, setIsListening] = useState(false);
  const [isPrivateMode, setIsPrivateMode] = useState(false);
  
  // Initialize messages with HeartSync greeting and transcript from fight capture
  const [messages, setMessages] = useState<Array<{ speaker: 'you' | 'heartsync'; message: string; isPrivate?: boolean }>>(() => {
    const initialMessages: Array<{ speaker: 'you' | 'heartsync'; message: string; isPrivate?: boolean }> = [
      {
        speaker: 'heartsync',
        message: 'I noticed there was some tension earlier. How are you feeling now?'
      }
    ];
    
    // Add transcript from fight capture if available
    if (state?.transcript && state.transcript.length > 0) {
      state.transcript.forEach((line: string) => {
        // Extract the message text (remove "You: " prefix if present)
        const messageText = line.replace(/^You:\s*/, '').trim();
        if (messageText) {
          initialMessages.push({
            speaker: 'you',
            message: messageText
          });
        }
      });
    }
    
    return initialMessages;
  });
  const toggleListening = () => {
    setIsListening(!isListening);
    // Simulate user speaking after a delay
    if (!isListening) {
      setTimeout(() => {
        addMessage('you', 'I felt ignored when they were on their phone during our conversation.', isPrivateMode);
        // Simulate HeartSync response
        setTimeout(() => {
          addMessage('heartsync', 'I understand that felt hurtful. Have you shared how that specific behavior makes you feel?');
          setIsListening(false);
        }, 2000);
      }, 2000);
    }
  };
  const addMessage = (speaker: 'you' | 'heartsync', message: string, isPrivate: boolean = false) => {
    setMessages(prev => [...prev, {
      speaker,
      message,
      isPrivate
    }]);
  };
  const togglePrivateMode = () => {
    setIsPrivateMode(!isPrivateMode);
  };
  return <div className="flex flex-col min-h-[80vh] py-4">
      <div className="text-center mb-4">
        <h2 className="text-xl font-semibold text-gray-800">
          Post-Fight Session
        </h2>
        <p className="text-sm text-gray-600">
          Talk freely — HeartSync is here to help.
        </p>
      </div>
      <div className="flex-1 overflow-y-auto mb-4 px-1">
        <div className="space-y-1">
          {messages.map((msg, idx) => <TranscriptBubble key={idx} speaker={msg.speaker} message={msg.message} isPrivate={msg.isPrivate} />)}
        </div>
      </div>
      <div className="flex flex-col items-center">
        <div className="flex justify-center mb-4">
          <VoiceButton isActive={isListening} onClick={toggleListening} size="lg" />
        </div>
        <div className="flex items-center justify-center mb-4">
          <button className={`flex items-center py-1 px-3 rounded-full text-sm ${isPrivateMode ? 'bg-rose-200 text-rose-700' : 'bg-white/50 text-gray-600'}`} onClick={togglePrivateMode}>
            <div size={14} className="mr-1" />
            Mark rant as private
          </button>
        </div>
        <div className="flex justify-center space-x-2">
          <button className="p-2 rounded-xl bg-white/50 hover:bg-white/70 transition-colors">
            <BarChart4Icon size={20} className="text-gray-700" />
          </button>
          <button className="p-2 rounded-xl bg-white/50 hover:bg-white/70 transition-colors">
            <RefreshCwIcon size={20} className="text-gray-700" />
          </button>
          <button className="p-2 rounded-xl bg-white/50 hover:bg-white/70 transition-colors">
            <FileTextIcon size={20} className="text-gray-700" />
          </button>
        </div>
      </div>
    </div>;
};
export default PostFightSession;