import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import VoiceButton from '../components/VoiceButton';
import TranscriptBubble from '../components/TranscriptBubble';
import { BarChart4Icon, RefreshCwIcon, FileTextIcon } from 'lucide-react';

interface LocationState {
  transcript?: string[];
  interimTranscript?: string;
}

interface Message {
  speaker: 'speaker1' | 'speaker2' | 'heartsync';
  message: string;
  isPrivate?: boolean;
}

const PostFightSession = () => {
  const location = useLocation();
  const state = location.state as LocationState | null;
  
  const [isListening, setIsListening] = useState(false);
  const [isPrivateMode, setIsPrivateMode] = useState(false);
  
  // Initialize messages with transcript from fight capture only (no HeartSync greeting)
  const [messages, setMessages] = useState<Message[]>(() => {
    const initialMessages: Message[] = [];
    
    // Add transcript from fight capture if available
    if (state?.transcript && state.transcript.length > 0) {
      state.transcript.forEach((line: string) => {
        // Parse "Boyfriend: text" or "Girlfriend: text" format (also support old "Speaker 1/2" format)
        const boyfriendMatch = line.match(/^(?:Boyfriend|Speaker\s+1):\s*(.+)$/i);
        const girlfriendMatch = line.match(/^(?:Girlfriend|Speaker\s+2):\s*(.+)$/i);
        
        if (boyfriendMatch) {
          initialMessages.push({
            speaker: 'speaker1',
            message: boyfriendMatch[1].trim()
          });
        } else if (girlfriendMatch) {
          initialMessages.push({
            speaker: 'speaker2',
            message: girlfriendMatch[1].trim()
          });
        } else {
          // Fallback: treat as Boyfriend if no match
          const messageText = line.replace(/^(?:You|Boyfriend|Girlfriend|Speaker\s+\d+):\s*/i, '').trim();
          if (messageText) {
            initialMessages.push({
              speaker: 'speaker1',
              message: messageText
            });
          }
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
        addMessage('speaker1', 'I felt ignored when they were on their phone during our conversation.', isPrivateMode);
        // Simulate HeartSync response
        setTimeout(() => {
          addMessage('heartsync', 'I understand that felt hurtful. Have you shared how that specific behavior makes you feel?');
          setIsListening(false);
        }, 2000);
      }, 2000);
    }
  };
  const addMessage = (speaker: 'speaker1' | 'speaker2' | 'heartsync', message: string, isPrivate: boolean = false) => {
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
        <div className="space-y-2">
          {messages.map((msg, idx) => {
            // Handle different speaker types
            if (msg.speaker === 'heartsync') {
              return <TranscriptBubble key={idx} speaker="heartsync" message={msg.message} isPrivate={msg.isPrivate} />;
            } else {
              // Boyfriend on left, Girlfriend on right
              const isBoyfriend = msg.speaker === 'speaker1';
              return (
                <div key={idx} className={`flex w-full ${isBoyfriend ? 'justify-start' : 'justify-end'}`}>
                  <div className={`rounded-2xl py-2 px-4 max-w-[80%] ${
                    isBoyfriend 
                      ? 'bg-blue-100 text-gray-800' 
                      : 'bg-pink-100 text-gray-800'
                  } ${msg.isPrivate ? 'opacity-70' : ''}`}>
                    <div className="text-xs font-semibold mb-1 text-gray-600">
                      {isBoyfriend ? 'Boyfriend' : 'Girlfriend'}
                      {msg.isPrivate && <span className="ml-2 text-rose-500 text-[10px]">Private</span>}
                    </div>
                    <div className="text-sm">{msg.message}</div>
                  </div>
                </div>
              );
            }
          })}
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