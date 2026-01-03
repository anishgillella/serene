# Phase 3: Frontend - Sending Experience

Frontend implementation for sending gestures - FAB, gesture picker, and send modal with AI-generated messages.

## Goals

- Create floating action button (FAB) for Partner Chat
- Build gesture picker with 3 options
- Implement send modal with AI message generation
- Add regenerate and edit capabilities
- Create useGestures hook for state management

## Prerequisites

- Phase 1 complete (API endpoints)
- Phase 2 complete (AI message generation endpoint)

---

## Component Architecture

```
PartnerChat.tsx
├── GestureFAB.tsx (floating button, expands to picker)
├── SendGestureModal.tsx (modal with AI message)
│   ├── AI message display
│   ├── Regenerate button
│   ├── Edit textarea
│   └── Send button
└── hooks/useGestures.ts (state management)
```

---

## Gesture Configuration

**File**: `frontend/src/components/gestures/gestureConfig.ts`

```typescript
export interface GestureConfig {
    type: 'hug' | 'kiss' | 'thinking_of_you';
    emoji: string;
    label: string;
    color: string;
    bgColor: string;
    borderColor: string;
    animation: string;
    celebrationEmojis: string[];
}

export const GESTURE_CONFIG: Record<string, GestureConfig> = {
    hug: {
        type: 'hug',
        emoji: '🤗',
        label: 'Hug',
        color: 'text-amber-600',
        bgColor: 'bg-amber-50',
        borderColor: 'border-amber-200',
        animation: 'animate-bounce',
        celebrationEmojis: ['🤗', '💛', '🧡', '✨', '💫', '🌟']
    },
    kiss: {
        type: 'kiss',
        emoji: '💋',
        label: 'Kiss',
        color: 'text-pink-600',
        bgColor: 'bg-pink-50',
        borderColor: 'border-pink-200',
        animation: 'animate-pulse',
        celebrationEmojis: ['💋', '💕', '💖', '💗', '💓', '❤️', '💘']
    },
    thinking_of_you: {
        type: 'thinking_of_you',
        emoji: '💚',
        label: 'Thinking of You',
        color: 'text-emerald-600',
        bgColor: 'bg-emerald-50',
        borderColor: 'border-emerald-200',
        animation: 'animate-pulse',
        celebrationEmojis: ['💚', '💭', '✨', '🌟', '💫', '🌿', '🍀']
    }
};

export type GestureType = keyof typeof GESTURE_CONFIG;
```

---

## Gestures Hook

**File**: `frontend/src/hooks/useGestures.ts`

```typescript
import { useState, useEffect, useCallback } from 'react';

interface Gesture {
    id: string;
    relationship_id: string;
    gesture_type: 'hug' | 'kiss' | 'thinking_of_you';
    sent_by: string;
    message?: string;
    ai_generated: boolean;
    sent_at: string;
    delivered_at?: string;
    acknowledged_at?: string;
    acknowledged_by?: string;
}

interface GeneratedMessage {
    message: string;
    context_used: string[];
}

interface UseGesturesProps {
    relationshipId: string;
    partnerId: string;
    onGestureReceived?: (gesture: Gesture) => void;
}

interface UseGesturesReturn {
    pendingGestures: Gesture[];
    loading: boolean;
    error: string | null;
    generateMessage: (gestureType: string) => Promise<GeneratedMessage>;
    regenerateMessage: (gestureType: string, previousMessage: string) => Promise<GeneratedMessage>;
    sendGesture: (gestureType: string, message: string, aiGenerated: boolean) => Promise<Gesture>;
    acknowledgeGesture: (gestureId: string, sendBack?: { type: string; message?: string }) => Promise<void>;
    handleWebSocketGesture: (gesture: Gesture) => void;
}

export const useGestures = ({
    relationshipId,
    partnerId,
    onGestureReceived
}: UseGesturesProps): UseGesturesReturn => {
    const [pendingGestures, setPendingGestures] = useState<Gesture[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    // Fetch pending gestures on mount
    useEffect(() => {
        const fetchPending = async () => {
            if (!relationshipId || !partnerId) return;

            try {
                const response = await fetch(
                    `${apiUrl}/api/gestures/pending?relationship_id=${relationshipId}&partner_id=${partnerId}`,
                    { headers: { 'ngrok-skip-browser-warning': 'true' } }
                );
                if (response.ok) {
                    const data = await response.json();
                    setPendingGestures(data.gestures);
                }
            } catch (err) {
                console.error('Failed to fetch pending gestures:', err);
            }
        };

        fetchPending();
    }, [relationshipId, partnerId, apiUrl]);

    // Generate AI message for a gesture
    const generateMessage = useCallback(async (gestureType: string): Promise<GeneratedMessage> => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`${apiUrl}/api/gestures/generate-message`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'ngrok-skip-browser-warning': 'true'
                },
                body: JSON.stringify({
                    relationship_id: relationshipId,
                    sender_id: partnerId,
                    gesture_type: gestureType
                })
            });

            if (!response.ok) {
                throw new Error('Failed to generate message');
            }

            return await response.json();
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to generate message';
            setError(errorMessage);
            // Return a default message on error
            return {
                message: getDefaultMessage(gestureType),
                context_used: []
            };
        } finally {
            setLoading(false);
        }
    }, [relationshipId, partnerId, apiUrl]);

    // Regenerate a different message
    const regenerateMessage = useCallback(async (
        gestureType: string,
        previousMessage: string
    ): Promise<GeneratedMessage> => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`${apiUrl}/api/gestures/regenerate-message`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'ngrok-skip-browser-warning': 'true'
                },
                body: JSON.stringify({
                    relationship_id: relationshipId,
                    sender_id: partnerId,
                    gesture_type: gestureType,
                    previous_message: previousMessage
                })
            });

            if (!response.ok) {
                throw new Error('Failed to regenerate message');
            }

            return await response.json();
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to regenerate message';
            setError(errorMessage);
            return {
                message: previousMessage, // Keep previous on error
                context_used: []
            };
        } finally {
            setLoading(false);
        }
    }, [relationshipId, partnerId, apiUrl]);

    // Send a gesture
    const sendGesture = useCallback(async (
        gestureType: string,
        message: string,
        aiGenerated: boolean
    ): Promise<Gesture> => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`${apiUrl}/api/gestures/send`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'ngrok-skip-browser-warning': 'true'
                },
                body: JSON.stringify({
                    relationship_id: relationshipId,
                    gesture_type: gestureType,
                    sender_id: partnerId,
                    message: message.trim() || undefined,
                    ai_generated: aiGenerated
                })
            });

            if (!response.ok) {
                throw new Error('Failed to send gesture');
            }

            const data = await response.json();
            return data.gesture;
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to send gesture';
            setError(errorMessage);
            throw err;
        } finally {
            setLoading(false);
        }
    }, [relationshipId, partnerId, apiUrl]);

    // Acknowledge a gesture
    const acknowledgeGesture = useCallback(async (
        gestureId: string,
        sendBack?: { type: string; message?: string }
    ): Promise<void> => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`${apiUrl}/api/gestures/acknowledge`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'ngrok-skip-browser-warning': 'true'
                },
                body: JSON.stringify({
                    gesture_id: gestureId,
                    acknowledged_by: partnerId,
                    send_back: !!sendBack,
                    send_back_type: sendBack?.type,
                    send_back_message: sendBack?.message
                })
            });

            if (!response.ok) {
                throw new Error('Failed to acknowledge gesture');
            }

            // Remove from pending
            setPendingGestures(prev => prev.filter(g => g.id !== gestureId));
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to acknowledge gesture';
            setError(errorMessage);
            throw err;
        } finally {
            setLoading(false);
        }
    }, [partnerId, apiUrl]);

    // Handler for receiving gestures via WebSocket
    const handleWebSocketGesture = useCallback((gesture: Gesture) => {
        setPendingGestures(prev => [...prev, gesture]);
        if (onGestureReceived) {
            onGestureReceived(gesture);
        }
    }, [onGestureReceived]);

    return {
        pendingGestures,
        loading,
        error,
        generateMessage,
        regenerateMessage,
        sendGesture,
        acknowledgeGesture,
        handleWebSocketGesture
    };
};

// Helper function for default messages
function getDefaultMessage(gestureType: string): string {
    switch (gestureType) {
        case 'hug':
            return "Sending you a big warm hug right now.";
        case 'kiss':
            return "Sending you all my love.";
        case 'thinking_of_you':
            return "Just wanted you to know you're on my mind.";
        default:
            return "Thinking of you.";
    }
}
```

---

## Floating Action Button

**File**: `frontend/src/components/gestures/GestureFAB.tsx`

```tsx
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
                                animate-in slide-in-from-bottom-2
                            `}
                            style={{
                                animationDelay: `${index * 50}ms`,
                                animationFillMode: 'both'
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
        </div>
    );
};

export default GestureFAB;
```

---

## Send Gesture Modal

**File**: `frontend/src/components/gestures/SendGestureModal.tsx`

```tsx
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
    }, [onGenerateMessage]);

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
            <div className="bg-white rounded-3xl shadow-2xl w-full max-w-sm overflow-hidden animate-in zoom-in-95 duration-200">
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
                        <div className="flex items-center gap-2 mb-3 text-xs text-accent">
                            <Sparkles size={14} />
                            <span>Personalized using {contextUsed.join(', ')}</span>
                        </div>
                    )}

                    {/* Message display/edit */}
                    {generating ? (
                        <div className="flex flex-col items-center justify-center py-8">
                            <Loader2 size={32} className="animate-spin text-accent mb-3" />
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
                                    focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent
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
        </div>
    );
};

export default SendGestureModal;
```

---

## Component Barrel Export

**File**: `frontend/src/components/gestures/index.ts`

```typescript
export { default as GestureFAB } from './GestureFAB';
export { default as SendGestureModal } from './SendGestureModal';
export { GESTURE_CONFIG } from './gestureConfig';
export type { GestureType, GestureConfig } from './gestureConfig';
```

---

## Integration into PartnerChat (Partial)

**File**: `frontend/src/pages/PartnerChat.tsx` (add these pieces)

```tsx
// Add imports
import { GestureFAB, SendGestureModal, GestureType } from '@/components/gestures';
import { useGestures } from '@/hooks/useGestures';

// Inside component, add state
const [selectedGestureType, setSelectedGestureType] = useState<GestureType | null>(null);

// Initialize gesture hook
const {
    generateMessage,
    regenerateMessage,
    sendGesture,
    loading: gestureLoading
} = useGestures({
    relationshipId: relationshipId || '',
    partnerId: currentPartnerId
});

// Add handlers
const handleSelectGesture = (type: GestureType) => {
    setSelectedGestureType(type);
};

const handleSendGesture = async (message: string, aiGenerated: boolean) => {
    if (!selectedGestureType) return;
    await sendGesture(selectedGestureType, message, aiGenerated);
    setSelectedGestureType(null);
};

// Add to JSX return (before closing div)
<>
    {/* Gesture FAB */}
    <GestureFAB
        onSelectGesture={handleSelectGesture}
        disabled={!isConnected}
    />

    {/* Send Gesture Modal */}
    {selectedGestureType && (
        <SendGestureModal
            gestureType={selectedGestureType}
            partnerName={otherPartnerName || 'your partner'}
            onGenerateMessage={() => generateMessage(selectedGestureType)}
            onRegenerateMessage={(prev) => regenerateMessage(selectedGestureType, prev)}
            onSend={handleSendGesture}
            onClose={() => setSelectedGestureType(null)}
            loading={gestureLoading}
        />
    )}
</>
```

---

## Tailwind Animation Classes

If not already present, add these animations to `tailwind.config.js`:

```javascript
module.exports = {
    theme: {
        extend: {
            animation: {
                'in': 'fadeIn 0.2s ease-out',
                'slide-in-from-bottom-2': 'slideInFromBottom 0.2s ease-out',
                'zoom-in-95': 'zoomIn95 0.2s ease-out',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                slideInFromBottom: {
                    '0%': { transform: 'translateY(8px)', opacity: '0' },
                    '100%': { transform: 'translateY(0)', opacity: '1' },
                },
                zoomIn95: {
                    '0%': { transform: 'scale(0.95)', opacity: '0' },
                    '100%': { transform: 'scale(1)', opacity: '1' },
                },
            },
        },
    },
};
```

---

## Testing Checklist

### GestureFAB Tests
- [ ] FAB displays heart icon when collapsed
- [ ] Tapping FAB expands to show 3 gesture options
- [ ] Gesture options animate in with stagger
- [ ] Tapping outside closes the picker
- [ ] Tapping X closes the picker
- [ ] Selecting a gesture calls onSelectGesture
- [ ] Disabled state prevents interaction

### SendGestureModal Tests
- [ ] Modal opens with loading state
- [ ] AI message generates and displays
- [ ] Context indicators show what was used
- [ ] "Different message" button regenerates
- [ ] "Edit" button enables textarea
- [ ] "Write my own" clears message and enables edit
- [ ] Character count shows and limits to 280
- [ ] Send button disabled when empty
- [ ] Send button shows loading state
- [ ] Modal closes after successful send
- [ ] Cancel button closes modal

### useGestures Hook Tests
- [ ] generateMessage calls API and returns message
- [ ] regenerateMessage calls API with previous message
- [ ] sendGesture calls API with correct payload
- [ ] loading state updates correctly
- [ ] error handling works gracefully

### Integration Tests
- [ ] Full flow: FAB → select → generate → send
- [ ] Full flow: FAB → select → regenerate → send
- [ ] Full flow: FAB → select → write own → send
- [ ] Full flow: FAB → select → edit AI → send
