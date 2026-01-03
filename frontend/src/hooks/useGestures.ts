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
