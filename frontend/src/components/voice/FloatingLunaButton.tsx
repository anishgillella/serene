/**
 * FloatingLunaButton - A floating action button to start voice calls with Luna
 * Can be placed on any page that has conflict context
 */

import React, { useState } from 'react';
import { Mic, X, Sparkles } from 'lucide-react';
import VoiceCallModal from './VoiceCallModal';

interface FloatingLunaButtonProps {
  conflictId: string;
  relationshipId?: string;
  partnerAName?: string;
  partnerBName?: string;
  position?: 'bottom-right' | 'bottom-left';
}

const FloatingLunaButton: React.FC<FloatingLunaButtonProps> = ({
  conflictId,
  relationshipId = '00000000-0000-0000-0000-000000000000',
  partnerAName = 'Partner A',
  partnerBName = 'Partner B',
  position = 'bottom-right',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  const positionClasses = position === 'bottom-right'
    ? 'right-6 bottom-6'
    : 'left-6 bottom-6';

  return (
    <>
      {/* Floating Button */}
      <div className={`fixed ${positionClasses} z-40`}>
        {/* Tooltip */}
        <div
          className={`absolute bottom-full mb-2 right-0 whitespace-nowrap transition-all duration-200 ${
            isHovered ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2 pointer-events-none'
          }`}
        >
          <div className="bg-gray-900 text-white text-sm px-3 py-2 rounded-lg shadow-lg">
            <div className="flex items-center gap-2">
              <Sparkles size={14} className="text-purple-400" />
              <span>Talk to Luna</span>
            </div>
            <div className="text-xs text-gray-400 mt-1">Voice AI mediator</div>
          </div>
          {/* Tooltip arrow */}
          <div className="absolute -bottom-1 right-6 w-2 h-2 bg-gray-900 rotate-45" />
        </div>

        {/* Main Button */}
        <button
          onClick={() => setIsOpen(true)}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          disabled={!conflictId}
          className={`
            group relative w-14 h-14 rounded-full shadow-lg
            bg-gradient-to-br from-rose-500 via-purple-500 to-indigo-500
            hover:from-rose-600 hover:via-purple-600 hover:to-indigo-600
            disabled:opacity-50 disabled:cursor-not-allowed
            transition-all duration-300 ease-out
            hover:scale-110 hover:shadow-xl hover:shadow-purple-500/25
            active:scale-95
          `}
        >
          {/* Pulse animation ring */}
          <div className="absolute inset-0 rounded-full bg-gradient-to-br from-rose-500 to-purple-500 animate-ping opacity-20" />

          {/* Inner glow */}
          <div className="absolute inset-1 rounded-full bg-gradient-to-br from-white/20 to-transparent" />

          {/* Icon */}
          <div className="relative flex items-center justify-center">
            <Mic
              size={24}
              className="text-white transition-transform duration-200 group-hover:scale-110"
            />
          </div>

          {/* Status dot - shows when Luna is available */}
          <div className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-green-400 rounded-full border-2 border-white shadow-sm">
            <div className="absolute inset-0 rounded-full bg-green-400 animate-pulse" />
          </div>
        </button>
      </div>

      {/* Voice Call Modal */}
      <VoiceCallModal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        conflictId={conflictId}
        relationshipId={relationshipId}
        partnerAName={partnerAName}
        partnerBName={partnerBName}
      />
    </>
  );
};

export default FloatingLunaButton;
