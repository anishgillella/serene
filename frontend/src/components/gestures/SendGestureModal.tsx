import React, { useState, useEffect } from 'react';
import { X, Send, RefreshCw, Loader2, Sparkles, Edit3 } from 'lucide-react';
import { GESTURE_CONFIG, GestureType } from './gestureConfig';

interface SendGestureModalProps {
    gestureType: GestureType;
    partnerName: string;
    onGenerateMessage: () => Promise<{ message: string; context_used: string[] }>;
    onRegenerateMessage: (previousMessage: string) => Promise<{ message: string; context_used: string[] }>;
    onSend: (message: string, aiGenerated: boolean) => Promise<void>;
    onClose: () => void;
    loading?: boolean;
}

const SendGestureModal: React.FC<SendGestureModalProps> = ({
    gestureType,
    partnerName,
    onGenerateMessage,
    onRegenerateMessage,
    onSend,
    onClose,
    loading: externalLoading = false
}) => {
    const [message, setMessage] = useState('');
    const [isAiGenerated, setIsAiGenerated] = useState(true);
    const [isEditing, setIsEditing] = useState(false);
    const [generating, setGenerating] = useState(false);
    const [sending, setSending] = useState(false);
    const [contextUsed, setContextUsed] = useState<string[]>([]);

    const config = GESTURE_CONFIG[gestureType];

    // Generate AI message on mount
    useEffect(() => {
        const generate = async () => {
            setGenerating(true);
            try {
                const result = await onGenerateMessage();
                setMessage(result.message);
                setContextUsed(result.context_used);
                setIsAiGenerated(true);
            } catch (err) {
                console.error('Failed to generate message:', err);
            } finally {
                setGenerating(false);
            }
        };

        generate();
    }, []);

    const handleRegenerate = async () => {
        setGenerating(true);
        try {
            const result = await onRegenerateMessage(message);
            setMessage(result.message);
            setContextUsed(result.context_used);
            setIsAiGenerated(true);
            setIsEditing(false);
        } catch (err) {
            console.error('Failed to regenerate message:', err);
        } finally {
            setGenerating(false);
        }
    };

    const handleSend = async () => {
        if (!message.trim()) return;

        setSending(true);
        try {
            await onSend(message.trim(), isAiGenerated && !isEditing);
            onClose();
        } catch (err) {
            console.error('Failed to send gesture:', err);
            setSending(false);
        }
    };

    const handleStartWriteOwn = () => {
        setMessage('');
        setIsAiGenerated(false);
        setIsEditing(true);
        setContextUsed([]);
    };

    const handleEditMessage = () => {
        setIsEditing(true);
    };

    if (!config) return null;

    const isLoading = generating || sending || externalLoading;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm px-4">
            <div className="bg-white rounded-3xl shadow-2xl w-full max-w-sm overflow-hidden" style={{ animation: 'zoomIn 0.2s ease-out' }}>
                {/* Header with gesture preview */}
                <div className={`${config.bgColor} px-6 py-8 text-center relative`}>
                    <button
                        onClick={onClose}
                        disabled={isLoading}
                        className="absolute top-4 right-4 p-2 hover:bg-white/50 rounded-full transition-colors disabled:opacity-50"
                    >
                        <X size={20} className="text-gray-600" />
                    </button>

                    {/* Animated gesture preview */}
                    <div className={`text-7xl ${config.animation} mb-4`}>
                        {config.emoji}
                    </div>

                    <h2 className={`text-xl font-bold ${config.color}`}>
                        Send a {config.label}
                    </h2>
                    <p className="text-gray-600 text-sm mt-1">
                        to {partnerName}
                    </p>
                </div>

                {/* Message section */}
                <div className="p-6">
                    {/* AI indicator */}
                    {isAiGenerated && !isEditing && contextUsed.length > 0 && (
                        <div className="flex items-center gap-2 mb-3 text-xs text-pink-600">
                            <Sparkles size={14} />
                            <span>Personalized using {contextUsed.join(', ')}</span>
                        </div>
                    )}

                    {/* Message display/edit */}
                    {generating ? (
                        <div className="flex flex-col items-center justify-center py-8">
                            <Loader2 size={32} className="animate-spin text-pink-500 mb-3" />
                            <p className="text-sm text-gray-500">Luna is crafting a message...</p>
                        </div>
                    ) : isEditing ? (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Your message
                            </label>
                            <textarea
                                value={message}
                                onChange={(e) => {
                                    setMessage(e.target.value.slice(0, 280));
                                    setIsAiGenerated(false);
                                }}
                                placeholder="Write something heartfelt..."
                                className="
                                    w-full px-4 py-3 rounded-xl border border-gray-200
                                    focus:outline-none focus:ring-2 focus:ring-pink-500/20 focus:border-pink-500
                                    resize-none text-sm
                                "
                                rows={4}
                                maxLength={280}
                                autoFocus
                            />
                            <p className="text-xs text-gray-400 text-right mt-1">
                                {message.length}/280
                            </p>
                        </div>
                    ) : (
                        <div>
                            <div className={`
                                p-4 rounded-xl border ${config.borderColor} ${config.bgColor}
                                text-gray-800 text-sm leading-relaxed
                            `}>
                                "{message}"
                            </div>

                            {/* Action buttons below message */}
                            <div className="flex gap-2 mt-3">
                                <button
                                    onClick={handleRegenerate}
                                    disabled={isLoading}
                                    className="flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm text-gray-600 hover:bg-gray-100 transition-colors disabled:opacity-50"
                                >
                                    <RefreshCw size={16} />
                                    Different message
                                </button>
                                <button
                                    onClick={handleEditMessage}
                                    disabled={isLoading}
                                    className="flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm text-gray-600 hover:bg-gray-100 transition-colors disabled:opacity-50"
                                >
                                    <Edit3 size={16} />
                                    Edit
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Write my own option */}
                    {!isEditing && !generating && (
                        <button
                            onClick={handleStartWriteOwn}
                            className="w-full mt-4 text-sm text-gray-500 hover:text-gray-700 underline"
                        >
                            Or write my own message
                        </button>
                    )}
                </div>

                {/* Actions */}
                <div className="px-6 pb-6 flex gap-3">
                    <button
                        onClick={onClose}
                        disabled={isLoading}
                        className="flex-1 py-3 px-4 rounded-xl border border-gray-200 text-gray-600 font-medium hover:bg-gray-50 transition-colors disabled:opacity-50"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSend}
                        disabled={isLoading || !message.trim()}
                        className={`
                            flex-1 py-3 px-4 rounded-xl font-medium
                            flex items-center justify-center gap-2
                            bg-gradient-to-r from-pink-500 to-rose-500 text-white
                            hover:from-pink-600 hover:to-rose-600
                            disabled:opacity-50 disabled:cursor-not-allowed
                            transition-all shadow-md hover:shadow-lg
                        `}
                    >
                        {sending ? (
                            <Loader2 size={20} className="animate-spin" />
                        ) : (
                            <>
                                <Send size={18} />
                                Send {config.emoji}
                            </>
                        )}
                    </button>
                </div>
            </div>

            <style>{`
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
        </div>
    );
};

export default SendGestureModal;
