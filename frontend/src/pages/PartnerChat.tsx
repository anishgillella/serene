import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useRelationship } from '@/contexts/RelationshipContext';
import { Loader2, Settings, ArrowLeft, Users } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import ConversationView from '@/components/partner-chat/ConversationView';
import MessageInput from '@/components/partner-chat/MessageInput';
import SettingsDrawer from '@/components/partner-chat/SettingsDrawer';

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
                    setMessages(prev => [...prev, data.message]);
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

        wsRef.current.send(JSON.stringify({
            type: 'message',
            content,
            original_content: originalContent,
            luna_intervened: lunaIntervened || false
        }));
    }, []);

    const handleTyping = useCallback((isTyping: boolean) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

        wsRef.current.send(JSON.stringify({
            type: 'typing',
            is_typing: isTyping
        }));
    }, []);

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
        </div>
    );
};

export default PartnerChat;
