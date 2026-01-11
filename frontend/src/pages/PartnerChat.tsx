import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useRelationship } from '@/contexts/RelationshipContext';
import { Loader2, Settings, ArrowLeft, Users } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import ConversationView from '@/components/partner-chat/ConversationView';
import MessageInput from '@/components/partner-chat/MessageInput';
import SettingsDrawer from '@/components/partner-chat/SettingsDrawer';
import { GestureFAB, SendGestureModal, ReceiveGestureModal, GestureType } from '@/components/gestures';
import { useGestures } from '@/hooks/useGestures';

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

interface Message {
    id: string;
    conversation_id: string;
    sender_id: string;
    content: string;
    status: string;
    sent_at: string;
    delivered_at?: string;
    read_at?: string;
    sentiment_label?: string;
    emotions?: string[];
    escalation_risk?: string;
    luna_intervened?: boolean;
}

interface Conversation {
    id: string;
    relationship_id: string;
    last_message_at?: string;
    message_count: number;
}

interface MessagingPreferences {
    id: string;
    relationship_id: string;
    partner_id: string;
    luna_assistance_enabled: boolean;
    suggestion_mode: string;
    intervention_enabled: boolean;
    intervention_sensitivity: string;
    show_read_receipts: boolean;
    show_typing_indicators: boolean;
    demo_mode_enabled: boolean;
}

const PartnerChat: React.FC = () => {
    const { relationshipId, partnerAName, partnerBName } = useRelationship();
    const [searchParams, setSearchParams] = useSearchParams();
    const [conversation, setConversation] = useState<Conversation | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [partnerTyping, setPartnerTyping] = useState(false);
    const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    // Settings drawer state
    const [settingsOpen, setSettingsOpen] = useState(false);
    const [preferences, setPreferences] = useState<MessagingPreferences | null>(null);
    const [savingPreferences, setSavingPreferences] = useState(false);

    // Gesture state
    const [selectedGestureType, setSelectedGestureType] = useState<GestureType | null>(null);
    const [receivedGesture, setReceivedGesture] = useState<Gesture | null>(null);

    // Get partner ID from URL param or default to partner_a
    // Use ?as=partner_b to test as the other partner
    const currentPartnerId = useMemo(() => {
        const asParam = searchParams.get('as');
        return asParam === 'partner_b' ? 'partner_b' : 'partner_a';
    }, [searchParams]);

    // Toggle between partners for testing
    const switchPartner = useCallback(() => {
        const newPartner = currentPartnerId === 'partner_a' ? 'partner_b' : 'partner_a';
        setSearchParams({ as: newPartner });
        // Force reload to reconnect WebSocket as new partner
        window.location.href = `/chat?as=${newPartner}`;
    }, [currentPartnerId, setSearchParams]);

    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    // Initialize gesture hook
    const {
        pendingGestures,
        generateMessage,
        regenerateMessage,
        sendGesture,
        acknowledgeGesture,
        handleWebSocketGesture,
        loading: gestureLoading
    } = useGestures({
        relationshipId: relationshipId || '',
        partnerId: currentPartnerId,
        onGestureReceived: (gesture) => {
            setReceivedGesture(gesture);
        }
    });

    // Show first pending gesture on initial load
    useEffect(() => {
        if (pendingGestures.length > 0 && !receivedGesture) {
            setReceivedGesture(pendingGestures[0]);
        }
    }, [pendingGestures, receivedGesture]);

    // Get or create conversation
    useEffect(() => {
        const initConversation = async () => {
            if (!relationshipId) return;

            try {
                const response = await fetch(
                    `${apiUrl}/api/partner-messages/conversation?relationship_id=${relationshipId}`,
                    {
                        headers: {
                            'ngrok-skip-browser-warning': 'true'
                        }
                    }
                );
                if (!response.ok) throw new Error('Failed to load conversation');

                const data = await response.json();
                setConversation(data);
            } catch (err) {
                setError('Failed to load conversation');
                console.error(err);
            }
        };

        initConversation();
    }, [relationshipId, apiUrl]);

    // Load messages
    useEffect(() => {
        const loadMessages = async () => {
            if (!conversation?.id) return;

            try {
                const response = await fetch(
                    `${apiUrl}/api/partner-messages/messages?conversation_id=${conversation.id}&limit=50`,
                    {
                        headers: {
                            'ngrok-skip-browser-warning': 'true'
                        }
                    }
                );
                if (!response.ok) throw new Error('Failed to load messages');

                const data = await response.json();
                setMessages(data.messages);
            } catch (err) {
                setError('Failed to load messages');
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        loadMessages();
    }, [conversation?.id, apiUrl]);

    // Load preferences
    useEffect(() => {
        const loadPreferences = async () => {
            if (!relationshipId || !currentPartnerId) return;

            try {
                const response = await fetch(
                    `${apiUrl}/api/partner-messages/preferences?relationship_id=${relationshipId}&partner_id=${currentPartnerId}`,
                    {
                        headers: {
                            'ngrok-skip-browser-warning': 'true'
                        }
                    }
                );
                if (!response.ok) throw new Error('Failed to load preferences');

                const data = await response.json();
                setPreferences(data);
            } catch (err) {
                console.error('Failed to load preferences:', err);
            }
        };

        loadPreferences();
    }, [relationshipId, currentPartnerId, apiUrl]);

    // Update a single preference
    const handleUpdatePreference = useCallback(async (key: string, value: boolean | string) => {
        if (!relationshipId || !currentPartnerId) return;

        setSavingPreferences(true);
        try {
            const response = await fetch(
                `${apiUrl}/api/partner-messages/preferences?relationship_id=${relationshipId}&partner_id=${currentPartnerId}`,
                {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'ngrok-skip-browser-warning': 'true'
                    },
                    body: JSON.stringify({ [key]: value })
                }
            );

            if (!response.ok) throw new Error('Failed to update preference');

            const updatedPrefs = await response.json();
            setPreferences(updatedPrefs);
        } catch (err) {
            console.error('Failed to update preference:', err);
            setError('Failed to save settings');
        } finally {
            setSavingPreferences(false);
        }
    }, [relationshipId, currentPartnerId, apiUrl]);

    // WebSocket connection
    useEffect(() => {
        if (!conversation?.id || !currentPartnerId) return;

        const wsUrl = apiUrl.replace('http://', 'ws://').replace('https://', 'wss://');
        const ws = new WebSocket(
            `${wsUrl}/api/realtime/partner-chat?conversation_id=${conversation.id}&partner_id=${currentPartnerId}`
        );

        ws.onopen = () => {
            setIsConnected(true);
            console.log('WebSocket connected');
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            switch (data.type) {
                case 'new_message':
                    setMessages(prev => [...prev, data.message]);
                    // Clear typing indicator when message received
                    setPartnerTyping(false);
                    break;
                case 'message_sent':
                    // Replace the optimistic message (temp-*) with the confirmed message from backend
                    setMessages(prev => {
                        // Find and remove any optimistic message with matching content
                        const withoutOptimistic = prev.filter(m =>
                            !m.id.startsWith('temp-') || m.content !== data.message.content
                        );
                        return [...withoutOptimistic, data.message];
                    });
                    break;
                case 'typing':
                    if (data.partner_id !== currentPartnerId) {
                        setPartnerTyping(data.is_typing);
                        // Auto-clear typing after 3 seconds
                        if (data.is_typing) {
                            if (typingTimeoutRef.current) {
                                clearTimeout(typingTimeoutRef.current);
                            }
                            typingTimeoutRef.current = setTimeout(() => {
                                setPartnerTyping(false);
                            }, 3000);
                        }
                    }
                    break;
                case 'delivered':
                    setMessages(prev => prev.map(m =>
                        m.id === data.message_id
                            ? { ...m, status: 'delivered' }
                            : m
                    ));
                    break;
                case 'read_receipt':
                    setMessages(prev => prev.map(m =>
                        m.id === data.message_id
                            ? { ...m, status: 'read' }
                            : m
                    ));
                    break;
                case 'error':
                    console.error('WebSocket error:', data.message);
                    break;
                // Gesture handling
                case 'gesture_received':
                    handleWebSocketGesture(data.gesture);
                    setReceivedGesture(data.gesture);
                    break;
                case 'gesture_acknowledged':
                    console.log('Your gesture was acknowledged:', data.gesture_id);
                    break;
                case 'gesture_sent':
                    console.log('Gesture sent:', data.gesture);
                    break;
            }
        };

        ws.onclose = () => {
            setIsConnected(false);
            console.log('WebSocket disconnected');
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        wsRef.current = ws;

        return () => {
            ws.close();
        };
    }, [conversation?.id, currentPartnerId, apiUrl]);

    const handleSendMessage = useCallback((
        content: string,
        originalContent?: string,
        lunaIntervened?: boolean
    ) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
            setError('Not connected. Please refresh.');
            return;
        }

        // Optimistic update: immediately show the message in the UI
        const optimisticMessage: Message = {
            id: `temp-${Date.now()}`, // Temporary ID until backend confirms
            conversation_id: conversation?.id || '',
            sender_id: currentPartnerId,
            content,
            status: 'sending',
            sent_at: new Date().toISOString(),
            luna_intervened: lunaIntervened
        };
        setMessages(prev => [...prev, optimisticMessage]);

        wsRef.current.send(JSON.stringify({
            type: 'message',
            content,
            original_content: originalContent,
            luna_intervened: lunaIntervened || false
        }));
    }, [conversation?.id, currentPartnerId]);

    const handleTyping = useCallback((isTyping: boolean) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

        wsRef.current.send(JSON.stringify({
            type: 'typing',
            is_typing: isTyping
        }));
    }, []);

    // Gesture handlers
    const handleSelectGesture = (type: GestureType) => {
        setSelectedGestureType(type);
    };

    const handleSendGesture = async (message: string, aiGenerated: boolean) => {
        if (!selectedGestureType) return;
        await sendGesture(selectedGestureType, message, aiGenerated);
        setSelectedGestureType(null);
    };

    const handleAcknowledgeGesture = async (sendBack?: { type: string; message?: string }) => {
        if (!receivedGesture) return;
        await acknowledgeGesture(receivedGesture.id, sendBack);
        setReceivedGesture(null);
    };

    // Determine sender name for received gesture
    const gestureSenderName = receivedGesture?.sent_by === 'partner_a'
        ? partnerAName || 'Your partner'
        : partnerBName || 'Your partner';

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <Loader2 className="animate-spin text-accent" size={32} />
            </div>
        );
    }

    const otherPartnerName = currentPartnerId === 'partner_a' ? partnerBName : partnerAName;
    const currentPartnerName = currentPartnerId === 'partner_a' ? partnerAName : partnerBName;

    return (
        <div className="flex flex-col h-full w-full bg-white">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-white shadow-sm">
                <div className="flex items-center gap-4">
                    <Link to="/" className="p-2 -ml-2 hover:bg-gray-100 rounded-full transition-colors">
                        <ArrowLeft size={20} className="text-gray-600" />
                    </Link>
                    <div>
                        <h2 className="font-semibold text-gray-900 text-lg">
                            {otherPartnerName || 'Your Partner'}
                        </h2>
                        <p className="text-sm text-gray-500">
                            {isConnected ? (
                                <span className="flex items-center gap-1.5">
                                    <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                                    Online
                                </span>
                            ) : (
                                <span className="flex items-center gap-1.5">
                                    <span className="w-2 h-2 bg-amber-500 rounded-full animate-pulse"></span>
                                    Connecting...
                                </span>
                            )}
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    {/* Partner Switch Button (for testing) */}
                    <button
                        onClick={switchPartner}
                        className="flex items-center gap-2 px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                        title="Switch partner (for testing)"
                    >
                        <Users size={16} className="text-gray-600" />
                        <span className="text-gray-700">
                            You: <strong>{currentPartnerName || currentPartnerId}</strong>
                        </span>
                    </button>

                    <button
                        onClick={() => setSettingsOpen(true)}
                        className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                    >
                        <Settings size={20} className="text-gray-600" />
                    </button>
                </div>
            </div>

            {/* Error Banner */}
            {error && (
                <div className="px-6 py-3 bg-red-50 text-red-600 text-sm border-b border-red-100">
                    {error}
                </div>
            )}

            {/* Messages - Full width */}
            <ConversationView
                messages={messages}
                currentPartnerId={currentPartnerId}
                partnerTyping={partnerTyping}
                partnerName={otherPartnerName}
            />

            {/* Input */}
            <MessageInput
                conversationId={conversation?.id || ''}
                senderId={currentPartnerId}
                onSend={handleSendMessage}
                onTyping={handleTyping}
                disabled={!isConnected || !conversation?.id}
                lunaEnabled={preferences?.luna_assistance_enabled ?? true}
                suggestionMode={preferences?.suggestion_mode as 'always' | 'on_request' | 'high_risk_only' | 'off' || 'always'}
            />

            {/* Settings Drawer */}
            <SettingsDrawer
                isOpen={settingsOpen}
                onClose={() => setSettingsOpen(false)}
                preferences={preferences}
                onUpdatePreference={handleUpdatePreference}
                saving={savingPreferences}
            />

            {/* Gesture FAB - only show when not viewing a received gesture */}
            {!receivedGesture && (
                <GestureFAB
                    onSelectGesture={handleSelectGesture}
                    disabled={!isConnected}
                />
            )}

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

            {/* Receive Gesture Celebration Modal */}
            {receivedGesture && (
                <ReceiveGestureModal
                    gesture={receivedGesture}
                    senderName={gestureSenderName}
                    onAcknowledge={handleAcknowledgeGesture}
                    onGenerateMessage={generateMessage}
                />
            )}
        </div>
    );
};

export default PartnerChat;
