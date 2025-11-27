import React from 'react';
interface TranscriptBubbleProps {
  speaker: 'you' | 'heartsync';
  message: string;
  isPrivate?: boolean;
}
const TranscriptBubble: React.FC<TranscriptBubbleProps> = ({
  speaker,
  message,
  isPrivate = false
}) => {
  return <div className={`flex w-full mb-3 ${speaker === 'you' ? 'justify-end' : 'justify-start'}`}>
    <div className={`rounded-2xl py-2 px-4 max-w-[80%] ${speaker === 'you' ? 'bg-lavender text-gray-800' : 'bg-white/80 text-gray-700'} ${isPrivate ? 'opacity-70' : ''}`}>
      <div className="text-xs font-semibold mb-1">
        {speaker === 'you' ? 'You' : 'Luna'}
        {isPrivate && speaker === 'you' && <span className="ml-2 text-rose-500 text-[10px]">Private</span>}
      </div>
      <div className="text-sm">{message}</div>
    </div>
  </div>;
};
export default TranscriptBubble;