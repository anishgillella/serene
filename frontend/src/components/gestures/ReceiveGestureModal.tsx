import React, { useState, useEffect, useCallback } from 'react';
import { Heart, Send, Loader2 } from 'lucide-react';
import { GESTURE_CONFIG, GestureType } from './gestureConfig';

interface Gesture {
    id: string;
    gesture_type: string;
    sent_by: string;
    message?: string;
    sent_at: string;
}

interface ReceiveGestureModalProps {
    gesture: Gesture;
    senderName: string;
    onAcknowledge: (sendBack?: { type: string; message?: string }) => Promise<void>;
    onGenerateMessage?: (gestureType: string) => Promise<{ message: string; context_used: string[] }>;
}

// Floating emoji particle component
const FloatingEmoji: React.FC<{
    emoji: string;
    delay: number;
    duration: number;
    startX: number;
    startSize: number;
}> = ({ emoji, delay, duration, startX, startSize }) => {
    return (
        <div
            className="absolute pointer-events-none"
            style={{
                left: `${startX}%`,
                bottom: '-10%',
                fontSize: `${startSize}rem`,
                animation: `floatUp ${duration}s ease-out ${delay}s forwards`,
                opacity: 0,
            }}
        >
            {emoji}
        </div>
    );
};

const ReceiveGestureModal: React.FC<ReceiveGestureModalProps> = ({
    gesture,
    senderName,
    onAcknowledge,
    onGenerateMessage
}) => {
    const [particles, setParticles] = useState<Array<{
        id: number;
        emoji: string;
        delay: number;
        duration: number;
        startX: number;
        startSize: number;
    }>>([]);
    const [showSendBack, setShowSendBack] = useState(false);
    const [sendBackType, setSendBackType] = useState<GestureType | null>(null);
    const [sendBackMessage, setSendBackMessage] = useState('');
    const [generatingMessage, setGeneratingMessage] = useState(false);
    const [acknowledging, setAcknowledging] = useState(false);

    const config = GESTURE_CONFIG[gesture.gesture_type as GestureType];

    // Generate floating particles on mount
    useEffect(() => {
        if (!config) return;

        const newParticles = [];
        for (let i = 0; i < 30; i++) {
            newParticles.push({
                id: i,
                emoji: config.celebrationEmojis[
                    Math.floor(Math.random() * config.celebrationEmojis.length)
                ],
                delay: Math.random() * 2.5,
                duration: 3 + Math.random() * 2.5,
                startX: Math.random() * 100,
                startSize: 1.5 + Math.random() * 1.5
            });
        }
        setParticles(newParticles);
    }, [config]);

    // Handle just closing (acknowledge without sending back)
    const handleClose = useCallback(async () => {
        setAcknowledging(true);
        try {
            await onAcknowledge();
        } catch (error) {
            console.error('Failed to acknowledge gesture:', error);
            setAcknowledging(false);
        }
    }, [onAcknowledge]);

    // Handle selecting a gesture to send back
    const handleSelectSendBack = async (type: GestureType) => {
        setSendBackType(type);

        // Generate AI message for the response
        if (onGenerateMessage) {
            setGeneratingMessage(true);
            try {
                const result = await onGenerateMessage(type);
                setSendBackMessage(result.message);
            } catch (err) {
                console.error('Failed to generate message:', err);
            } finally {
                setGeneratingMessage(false);
            }
        }
    };

    // Handle sending back
    const handleSendBack = async () => {
        if (!sendBackType) return;

        setAcknowledging(true);
        try {
            await onAcknowledge({
                type: sendBackType,
                message: sendBackMessage.trim() || undefined
            });
        } catch (error) {
            console.error('Failed to send back gesture:', error);
            setAcknowledging(false);
        }
    };

    if (!config) return null;

    // Determine gradient based on gesture type
    const gradientClass = {
        hug: 'from-amber-100 via-orange-50 to-white',
        kiss: 'from-pink-100 via-rose-50 to-white',
        thinking_of_you: 'from-emerald-100 via-green-50 to-white'
    }[gesture.gesture_type] || 'from-pink-100 via-rose-50 to-white';

    return (
        <>
            {/* CSS for float animation */}
            <style>{`
                @keyframes floatUp {
                    0% {
                        opacity: 0;
                        transform: translateY(0) scale(0.5) rotate(0deg);
                    }
                    15% {
                        opacity: 1;
                    }
                    100% {
                        opacity: 0;
                        transform: translateY(-100vh) scale(1.2) rotate(360deg);
                    }
                }

                @keyframes heartbeat {
                    0%, 100% { transform: scale(1); }
                    15% { transform: scale(1.15); }
                    30% { transform: scale(1); }
                    45% { transform: scale(1.1); }
                }

                @keyframes gentlePulse {
                    0%, 100% { opacity: 0.6; }
                    50% { opacity: 1; }
                }

                @keyframes zoomIn {
                    from {
                        opacity: 0;
                        transform: scale(0.95);
                    }
                    to {
                        opacity: 1;
                        transform: scale(1);
                    }
                }
            `}</style>

            <div className="fixed inset-0 z-50 flex items-center justify-center overflow-hidden">
                {/* Gradient background */}
                <div
                    className={`absolute inset-0 bg-gradient-to-b ${gradientClass}`}
                    style={{ animation: 'gentlePulse 4s ease-in-out infinite' }}
                />

                {/* Floating particles */}
                <div className="absolute inset-0 overflow-hidden pointer-events-none">
                    {particles.map((p) => (
                        <FloatingEmoji key={p.id} {...p} />
                    ))}
                </div>

                {/* Main content */}
                <div className="relative z-10 text-center px-6 py-12 max-w-sm mx-auto w-full">
                    {!showSendBack ? (
                        /* Main gesture display */
                        <>
                            {/* Main gesture emoji with heartbeat animation */}
                            <div
                                className="text-8xl sm:text-9xl mb-6"
                                style={{ animation: 'heartbeat 1.5s ease-in-out infinite' }}
                            >
                                {config.emoji}
                            </div>

                            {/* Sender info */}
                            <h1 className={`text-2xl sm:text-3xl font-bold ${config.color} mb-2`}>
                                {senderName} sent you a {config.label.toLowerCase()}!
                            </h1>

                            {/* Personal message */}
                            {gesture.message && (
                                <div className="mt-6 mb-6">
                                    <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-5 shadow-lg border border-white/50">
                                        <p className="text-gray-800 text-lg italic leading-relaxed">
                                            "{gesture.message}"
                                        </p>
                                    </div>
                                </div>
                            )}

                            {/* Timestamp */}
                            <p className="text-gray-500 text-sm mb-8">
                                {new Date(gesture.sent_at).toLocaleTimeString([], {
                                    hour: '2-digit',
                                    minute: '2-digit'
                                })}
                            </p>

                            {/* Action buttons */}
                            <div className="flex flex-col gap-3">
                                <button
                                    onClick={() => setShowSendBack(true)}
                                    disabled={acknowledging}
                                    className={`
                                        w-full py-4 px-6 rounded-2xl font-semibold text-lg
                                        flex items-center justify-center gap-3
                                        bg-gradient-to-r from-pink-500 to-rose-500 text-white
                                        hover:from-pink-600 hover:to-rose-600
                                        shadow-xl hover:shadow-2xl
                                        transform hover:scale-[1.02] active:scale-[0.98]
                                        transition-all duration-200
                                        disabled:opacity-50 disabled:cursor-not-allowed
                                    `}
                                >
                                    <Heart size={24} className="fill-white/30" />
                                    Send One Back
                                </button>

                                <button
                                    onClick={handleClose}
                                    disabled={acknowledging}
                                    className={`
                                        w-full py-4 px-6 rounded-2xl font-medium
                                        bg-white/80 backdrop-blur-sm text-gray-700
                                        hover:bg-white border border-gray-200
                                        shadow-md hover:shadow-lg
                                        transition-all duration-200
                                        disabled:opacity-50 disabled:cursor-not-allowed
                                    `}
                                >
                                    {acknowledging ? (
                                        <span className="flex items-center justify-center gap-2">
                                            <Loader2 size={20} className="animate-spin" />
                                            Closing...
                                        </span>
                                    ) : (
                                        'Close'
                                    )}
                                </button>
                            </div>
                        </>
                    ) : (
                        /* Send back flow */
                        <div
                            className="bg-white/95 backdrop-blur-sm rounded-3xl p-6 shadow-xl"
                            style={{ animation: 'zoomIn 0.2s ease-out' }}
                        >
                            <h2 className="text-xl font-bold text-gray-900 mb-4">
                                Send a gesture back
                            </h2>

                            {/* Gesture selection */}
                            <div className="flex justify-center gap-4 mb-6">
                                {Object.values(GESTURE_CONFIG).map((g) => (
                                    <button
                                        key={g.type}
                                        onClick={() => handleSelectSendBack(g.type as GestureType)}
                                        disabled={generatingMessage}
                                        className={`
                                            w-16 h-16 rounded-xl flex items-center justify-center
                                            text-3xl transition-all duration-200
                                            ${sendBackType === g.type
                                                ? `${g.bgColor} ring-2 ring-offset-2 ring-pink-500 scale-110`
                                                : 'bg-gray-100 hover:bg-gray-200'
                                            }
                                            disabled:opacity-50
                                        `}
                                    >
                                        {g.emoji}
                                    </button>
                                ))}
                            </div>

                            {/* Message input (appears after selecting gesture) */}
                            {sendBackType && (
                                <div className="mb-6" style={{ animation: 'zoomIn 0.2s ease-out' }}>
                                    {generatingMessage ? (
                                        <div className="flex items-center justify-center py-4">
                                            <Loader2 size={24} className="animate-spin text-pink-500 mr-2" />
                                            <span className="text-sm text-gray-500">Crafting a message...</span>
                                        </div>
                                    ) : (
                                        <>
                                            <label className="block text-sm font-medium text-gray-700 mb-2 text-left">
                                                Your message (optional)
                                            </label>
                                            <textarea
                                                value={sendBackMessage}
                                                onChange={(e) => setSendBackMessage(e.target.value.slice(0, 280))}
                                                placeholder="Add a heartfelt note..."
                                                className="
                                                    w-full px-4 py-3 rounded-xl border border-gray-200
                                                    focus:outline-none focus:ring-2 focus:ring-pink-500/20 focus:border-pink-500
                                                    resize-none text-sm
                                                "
                                                rows={3}
                                                maxLength={280}
                                            />
                                            <p className="text-xs text-gray-400 text-right mt-1">
                                                {sendBackMessage.length}/280
                                            </p>
                                        </>
                                    )}
                                </div>
                            )}

                            {/* Actions */}
                            <div className="flex gap-3">
                                <button
                                    onClick={() => {
                                        setShowSendBack(false);
                                        setSendBackType(null);
                                        setSendBackMessage('');
                                    }}
                                    disabled={acknowledging}
                                    className="flex-1 py-3 px-4 rounded-xl border border-gray-200 text-gray-600 font-medium hover:bg-gray-50 transition-colors disabled:opacity-50"
                                >
                                    Back
                                </button>
                                <button
                                    onClick={handleSendBack}
                                    disabled={!sendBackType || acknowledging || generatingMessage}
                                    className={`
                                        flex-1 py-3 px-4 rounded-xl font-medium
                                        flex items-center justify-center gap-2
                                        bg-gradient-to-r from-pink-500 to-rose-500 text-white
                                        hover:from-pink-600 hover:to-rose-600
                                        disabled:opacity-50 disabled:cursor-not-allowed
                                        transition-all
                                    `}
                                >
                                    {acknowledging ? (
                                        <Loader2 size={18} className="animate-spin" />
                                    ) : (
                                        <>
                                            <Send size={18} />
                                            Send
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </>
    );
};

export default ReceiveGestureModal;
