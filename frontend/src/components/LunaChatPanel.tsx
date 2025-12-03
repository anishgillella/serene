import React, { useState, useEffect, useRef } from 'react';
import { SendIcon, BotIcon, UserIcon, LoaderIcon, AlertCircleIcon } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Button } from "@/components/ui/button";

interface Message {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    created_at?: string;
}

interface LunaChatPanelProps {
    conflictId: string;
}

const LunaChatPanel: React.FC<LunaChatPanelProps> = ({ conflictId }) => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Scroll to bottom on new message
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Initial greeting (local only)
    useEffect(() => {
        if (messages.length === 0) {
            setMessages([
                {
                    id: 'welcome',
                    role: 'assistant',
                    content: "Hi! I'm Luna. I've analyzed your conversation. Feel free to ask me anything about the conflict, the analysis, or how to move forward."
                }
            ]);
        }
    }, []);

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: input
        };

        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);
        setError(null);

        try {
            const response = await fetch('http://localhost:8000/api/mediator/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    conflict_id: conflictId,
                    message: userMessage.content
                }),
            });

            if (!response.ok) {
                throw new Error('Failed to get response from Luna');
            }

            const data = await response.json();

            const lunaMessage: Message = {
                id: data.message_id || Date.now().toString(),
                role: 'assistant',
                content: data.response
            };

            setMessages(prev => [...prev, lunaMessage]);
        } catch (err) {
            console.error('Error sending message:', err);
            setError('Failed to send message. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="flex flex-col h-full bg-surface-card rounded-2xl border border-border-subtle overflow-hidden shadow-sm">
            {/* Header */}
            <div className="p-4 border-b border-border-subtle bg-surface-base/50 backdrop-blur-sm">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-accent/10 flex items-center justify-center text-accent">
                        <BotIcon size={18} />
                    </div>
                    <div>
                        <h3 className="font-medium text-text-primary">Chat with Luna</h3>
                        <p className="text-xs text-text-tertiary">AI Mediator • Always here to help</p>
                    </div>
                </div>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-surface-base/30">
                {messages.map((msg) => (
                    <div
                        key={msg.id}
                        className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
                    >
                        <div className={`
              w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center
              ${msg.role === 'user' ? 'bg-primary/10 text-primary' : 'bg-accent/10 text-accent'}
            `}>
                            {msg.role === 'user' ? <UserIcon size={16} /> : <BotIcon size={16} />}
                        </div>

                        <div className={`
              max-w-[85%] rounded-2xl p-3 text-sm leading-relaxed
              ${msg.role === 'user'
                                ? 'bg-primary text-white rounded-tr-none'
                                : 'bg-surface-card border border-border-subtle text-text-secondary rounded-tl-none shadow-sm'}
            `}>
                            {msg.role === 'assistant' ? (
                                <div className="prose prose-sm max-w-none dark:prose-invert prose-p:leading-relaxed prose-pre:bg-black/10">
                                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                                </div>
                            ) : (
                                <p>{msg.content}</p>
                            )}
                        </div>
                    </div>
                ))}

                {isLoading && (
                    <div className="flex gap-3">
                        <div className="w-8 h-8 rounded-full bg-accent/10 flex items-center justify-center text-accent">
                            <BotIcon size={16} />
                        </div>
                        <div className="bg-surface-card border border-border-subtle rounded-2xl rounded-tl-none p-3 shadow-sm flex items-center gap-2">
                            <span className="w-2 h-2 bg-accent/50 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                            <span className="w-2 h-2 bg-accent/50 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                            <span className="w-2 h-2 bg-accent/50 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                    </div>
                )}

                {error && (
                    <div className="flex items-center gap-2 text-red-500 text-sm justify-center p-2 bg-red-500/10 rounded-lg">
                        <AlertCircleIcon size={16} />
                        <span>{error}</span>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 border-t border-border-subtle bg-surface-base">
                <div className="flex gap-2">
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask Luna anything..."
                        className="flex-1 bg-surface-input border border-border-input rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent resize-none h-[50px] max-h-[120px]"
                        disabled={isLoading}
                    />
                    <Button
                        onClick={handleSend}
                        disabled={!input.trim() || isLoading}
                        className="h-[50px] w-[50px] rounded-xl flex items-center justify-center p-0 bg-accent hover:bg-accent-hover text-white transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:shadow-none"
                    >
                        {isLoading ? <LoaderIcon className="animate-spin" size={20} /> : <SendIcon size={20} />}
                    </Button>
                </div>
                <p className="text-[10px] text-text-tertiary text-center mt-2">
                    Luna can make mistakes. Please verify important information.
                </p>
            </div>
        </div>
    );
};

export default LunaChatPanel;
