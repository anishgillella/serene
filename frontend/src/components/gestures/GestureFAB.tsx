import React, { useState } from 'react';
import { Heart, X } from 'lucide-react';
import { GESTURE_CONFIG, GestureType } from './gestureConfig';

interface GestureFABProps {
    onSelectGesture: (gestureType: GestureType) => void;
    disabled?: boolean;
}

const GestureFAB: React.FC<GestureFABProps> = ({
    onSelectGesture,
    disabled = false
}) => {
    const [isExpanded, setIsExpanded] = useState(false);

    const handleToggle = () => {
        if (!disabled) {
            setIsExpanded(!isExpanded);
        }
    };

    const handleSelect = (gestureType: GestureType) => {
        onSelectGesture(gestureType);
        setIsExpanded(false);
    };

    const gestures = Object.values(GESTURE_CONFIG);

    return (
        <div className="fixed bottom-24 right-4 z-40 flex flex-col-reverse items-center gap-3">
            {/* Gesture options - appear above FAB when expanded */}
            {isExpanded && (
                <div className="flex flex-col-reverse gap-2">
                    {gestures.map((gesture, index) => (
                        <button
                            key={gesture.type}
                            onClick={() => handleSelect(gesture.type as GestureType)}
                            className={`
                                w-14 h-14 rounded-full shadow-lg
                                flex items-center justify-center
                                ${gesture.bgColor} ${gesture.color}
                                transform transition-all duration-200
                                hover:scale-110 active:scale-95
                                border-2 border-white
                            `}
                            style={{
                                animation: `slideIn 0.2s ease-out ${index * 50}ms both`
                            }}
                            title={gesture.label}
                        >
                            <span className="text-2xl">{gesture.emoji}</span>
                        </button>
                    ))}
                </div>
            )}

            {/* Backdrop when expanded */}
            {isExpanded && (
                <div
                    className="fixed inset-0 -z-10"
                    onClick={() => setIsExpanded(false)}
                />
            )}

            {/* Main FAB */}
            <button
                onClick={handleToggle}
                disabled={disabled}
                className={`
                    w-16 h-16 rounded-full shadow-xl
                    flex items-center justify-center
                    transition-all duration-300 transform
                    ${isExpanded
                        ? 'bg-gray-200 rotate-45'
                        : 'bg-gradient-to-br from-pink-400 to-rose-500 hover:from-pink-500 hover:to-rose-600'
                    }
                    disabled:opacity-50 disabled:cursor-not-allowed
                    hover:scale-105 active:scale-95
                `}
                title={isExpanded ? 'Close' : 'Send a gesture'}
            >
                {isExpanded ? (
                    <X size={28} className="text-gray-600" />
                ) : (
                    <Heart size={28} className="text-white fill-white/30" />
                )}
            </button>

            <style>{`
                @keyframes slideIn {
                    from {
                        opacity: 0;
                        transform: translateY(10px) scale(0.8);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0) scale(1);
                    }
                }
            `}</style>
        </div>
    );
};

export default GestureFAB;
