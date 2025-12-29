import React, { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import TypingIndicator from './TypingIndicator';

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

interface ConversationViewProps {
    messages: Message[];
    currentPartnerId: string;
    partnerTyping: boolean;
    partnerName?: string;
}

const ConversationView: React.FC<ConversationViewProps> = ({
    messages,
    currentPartnerId,
    partnerTyping,
    partnerName
}) => {
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    // Scroll to bottom on new message
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, partnerTyping]);

    // Group messages by date
    const groupMessagesByDate = (msgs: Message[]) => {
        const groups: { date: string; messages: Message[] }[] = [];
        let currentDate = '';

        msgs.forEach(msg => {
            const msgDate = new Date(msg.sent_at).toLocaleDateString('en-US', {
                weekday: 'long',
                month: 'short',
                day: 'numeric'
            });

            if (msgDate !== currentDate) {
                currentDate = msgDate;
                groups.push({ date: msgDate, messages: [msg] });
            } else {
                groups[groups.length - 1].messages.push(msg);
            }
        });

        return groups;
    };

    const messageGroups = groupMessagesByDate(messages);

    if (messages.length === 0 && !partnerTyping) {
        return (
            <div className="flex-1 flex items-center justify-center p-8 text-center">
                <div className="max-w-sm">
                    <div className="w-16 h-16 bg-accent/10 rounded-full flex items-center justify-center mx-auto mb-4">
                        <span className="text-3xl">💬</span>
                    </div>
                    <h3 className="text-lg font-medium text-text-primary mb-2">
                        Start a Conversation
                    </h3>
                    <p className="text-sm text-text-secondary">
                        Send a message to {partnerName || 'your partner'} to start chatting.
                        Luna is here to help you communicate better.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div
            ref={containerRef}
            className="flex-1 overflow-y-auto p-4 space-y-4 bg-surface-base/50"
        >
            {messageGroups.map((group, groupIndex) => (
                <div key={groupIndex}>
                    {/* Date separator */}
                    <div className="flex items-center justify-center my-4">
                        <div className="px-3 py-1 bg-surface-card rounded-full text-xs text-text-tertiary border border-border-subtle">
                            {group.date}
                        </div>
                    </div>

                    {/* Messages for this date */}
                    <div className="space-y-2">
                        {group.messages.map((message) => (
                            <MessageBubble
                                key={message.id}
                                message={message}
                                isOwnMessage={message.sender_id === currentPartnerId}
                            />
                        ))}
                    </div>
                </div>
            ))}

            {/* Typing indicator */}
            {partnerTyping && (
                <TypingIndicator partnerName={partnerName} />
            )}

            {/* Scroll anchor */}
            <div ref={messagesEndRef} />
        </div>
    );
};

export default ConversationView;
