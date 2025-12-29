import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useRelationship } from '@/contexts/RelationshipContext';
import { Loader2, Settings, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';
import ConversationView from '@/components/partner-chat/ConversationView';
import MessageInput from '@/components/partner-chat/MessageInput';

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

const PartnerChat: React.FC = () => {
    const { relationshipId, partnerAName, partnerBName } = useRelationship();
    const [conversation, setConversation] = useState<Conversation | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [partnerTyping, setPartnerTyping] = useState(false);
    const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    // For demo purposes, we'll use partner_a as the current user
    // In production, this would come from auth context
    const [currentPartnerId] = useState<string>('partner_a');

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

    const handleSendMessage = useCallback((content: string) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
            setError('Not connected. Please refresh.');
            return;
        }

        wsRef.current.send(JSON.stringify({
            type: 'message',
            content
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

    return (
        <div className="flex flex-col h-full bg-surface-base">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-border-subtle bg-surface-card shadow-sm">
                <div className="flex items-center gap-3">
                    <Link to="/" className="p-2 -ml-2 hover:bg-surface-hover rounded-full transition-colors">
                        <ArrowLeft size={20} className="text-text-secondary" />
                    </Link>
                    <div>
                        <h2 className="font-semibold text-text-primary">
                            {otherPartnerName || 'Your Partner'}
                        </h2>
                        <p className="text-xs text-text-tertiary">
                            {isConnected ? (
                                <span className="flex items-center gap-1">
                                    <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                                    Connected
                                </span>
                            ) : (
                                <span className="flex items-center gap-1">
                                    <span className="w-2 h-2 bg-amber-500 rounded-full animate-pulse"></span>
                                    Connecting...
                                </span>
                            )}
                        </p>
                    </div>
                </div>
                <Link
                    to="/chat/settings"
                    className="p-2 hover:bg-surface-hover rounded-full transition-colors"
                >
                    <Settings size={20} className="text-text-secondary" />
                </Link>
            </div>

            {/* Error Banner */}
            {error && (
                <div className="px-4 py-2 bg-red-50 text-red-600 text-sm">
                    {error}
                </div>
            )}

            {/* Messages */}
            <ConversationView
                messages={messages}
                currentPartnerId={currentPartnerId}
                partnerTyping={partnerTyping}
                partnerName={otherPartnerName}
            />

            {/* Input */}
            <MessageInput
                onSend={handleSendMessage}
                onTyping={handleTyping}
                disabled={!isConnected}
            />
        </div>
    );
};

export default PartnerChat;
