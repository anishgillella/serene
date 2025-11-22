import React, { useState } from 'react';
import { MicIcon } from 'lucide-react';
interface VoiceButtonProps {
  isActive?: boolean;
  onClick?: () => void;
  size?: 'sm' | 'md' | 'lg';
}
const VoiceButton: React.FC<VoiceButtonProps> = ({
  isActive = false,
  onClick,
  size = 'md'
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const sizeClasses = {
    sm: 'w-12 h-12',
    md: 'w-16 h-16',
    lg: 'w-24 h-24'
  };
  const iconSizes = {
    sm: 20,
    md: 28,
    lg: 36
  };
  return <button className={`rounded-full flex items-center justify-center transition-all duration-300 ${sizeClasses[size]} 
      ${isActive ? 'bg-rose-400 shadow-lg breathing-animation' : 'bg-white/70 hover:bg-white/90'}`} onClick={onClick} onMouseEnter={() => setIsHovered(true)} onMouseLeave={() => setIsHovered(false)}>
      <MicIcon size={iconSizes[size]} className={`transition-colors ${isActive ? 'text-white' : 'text-gray-700'}`} />
      {isActive && <div className="absolute w-full h-full rounded-full bg-rose-400 opacity-20 animate-ping"></div>}
    </button>;
};
export default VoiceButton;