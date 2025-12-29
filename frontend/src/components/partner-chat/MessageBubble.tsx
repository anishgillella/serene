import React from 'react';
import { Check, CheckCheck } from 'lucide-react';

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

interface MessageBubbleProps {
    message: Message;
    isOwnMessage: boolean;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({
    message,
    isOwnMessage
}) => {
    const formatTime = (timestamp: string) => {
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    };

    const getStatusIcon = () => {
        switch (message.status) {
            case 'sent':
                return <Check size={14} className="text-white/50" />;
            case 'delivered':
                return <CheckCheck size={14} className="text-white/50" />;
            case 'read':
                return <CheckCheck size={14} className="text-white" />;
            default:
                return null;
        }
    };

    return (
        <div className={`flex ${isOwnMessage ? 'justify-end' : 'justify-start'}`}>
            <div
                className={`
                    max-w-[80%] md:max-w-[70%] rounded-2xl px-4 py-2.5
                    ${isOwnMessage
                        ? 'bg-accent text-white rounded-br-sm'
                        : 'bg-surface-card border border-border-subtle text-text-primary rounded-bl-sm shadow-sm'
                    }
                `}
            >
                {/* Message content */}
                <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                    {message.content}
                </p>

                {/* Timestamp and status */}
                <div className={`
                    flex items-center gap-1 mt-1.5
                    ${isOwnMessage ? 'justify-end' : 'justify-start'}
                `}>
                    <span className={`
                        text-[10px]
                        ${isOwnMessage ? 'text-white/70' : 'text-text-tertiary'}
                    `}>
                        {formatTime(message.sent_at)}
                    </span>

                    {/* Status indicator (only for own messages) */}
                    {isOwnMessage && getStatusIcon()}

                    {/* Luna indicator (if Luna helped with this message) */}
                    {message.luna_intervened && (
                        <span className="ml-1" title="Luna helped with this message">
                            ✨
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
};

export default MessageBubble;
