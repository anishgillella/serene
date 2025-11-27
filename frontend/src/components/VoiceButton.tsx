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
  return (
    <button
      className={`rounded-full flex items-center justify-center transition-all duration-300 ${sizeClasses[size]} 
      ${isActive
          ? 'bg-white border-2 border-accent shadow-soft'
          : 'bg-surface-hover border border-transparent hover:bg-white hover:border-border-subtle hover:shadow-subtle'}`}
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <MicIcon
        size={iconSizes[size]}
        className={`transition-colors ${isActive ? 'text-accent' : 'text-text-secondary'}`}
        strokeWidth={1.5}
      />
      {isActive && (
        <div className="absolute w-full h-full rounded-full border border-accent opacity-40 animate-ping"></div>
      )}
    </button>
  );
};
export default VoiceButton;