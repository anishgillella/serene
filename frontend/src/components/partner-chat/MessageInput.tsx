import React, { useState, useRef, useCallback } from 'react';
import { Send, Loader2 } from 'lucide-react';

interface MessageInputProps {
    onSend: (content: string) => void;
    onTyping: (isTyping: boolean) => void;
    disabled?: boolean;
}

const MessageInput: React.FC<MessageInputProps> = ({
    onSend,
    onTyping,
    disabled = false
}) => {
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const value = e.target.value;
        setInput(value);

        // Auto-resize textarea
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
        }

        // Typing indicator with debounce
        if (value.trim()) {
            onTyping(true);
            if (typingTimeoutRef.current) {
                clearTimeout(typingTimeoutRef.current);
            }
            typingTimeoutRef.current = setTimeout(() => {
                onTyping(false);
            }, 2000);
        } else {
            onTyping(false);
        }
    };

    const handleSend = useCallback(() => {
        const content = input.trim();
        if (!content || disabled || isLoading) return;

        // Clear typing indicator
        if (typingTimeoutRef.current) {
            clearTimeout(typingTimeoutRef.current);
        }
        onTyping(false);

        // Send message
        onSend(content);
        setInput('');

        // Reset textarea height
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
        }
    }, [input, disabled, isLoading, onSend, onTyping]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="p-4 border-t border-border-subtle bg-surface-card">
            <div className="flex gap-2 items-end">
                <div className="flex-1 relative">
                    <textarea
                        ref={textareaRef}
                        value={input}
                        onChange={handleInputChange}
                        onKeyDown={handleKeyDown}
                        placeholder="Message your partner..."
                        disabled={disabled || isLoading}
                        rows={1}
                        className="
                            w-full bg-surface-input border border-border-input rounded-xl
                            px-4 py-3 text-sm
                            focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent
                            resize-none
                            min-h-[50px] max-h-[120px]
                            disabled:opacity-50
                            placeholder:text-text-tertiary
                        "
                    />
                </div>

                <button
                    onClick={handleSend}
                    disabled={!input.trim() || isLoading || disabled}
                    className="
                        h-[50px] w-[50px] rounded-xl
                        flex items-center justify-center
                        bg-accent hover:bg-accent/90
                        text-white
                        transition-all
                        shadow-md hover:shadow-lg
                        disabled:opacity-50 disabled:shadow-none disabled:cursor-not-allowed
                    "
                >
                    {isLoading ? (
                        <Loader2 className="animate-spin" size={20} />
                    ) : (
                        <Send size={20} />
                    )}
                </button>
            </div>

            <p className="text-[10px] text-text-tertiary text-center mt-2">
                Press Enter to send, Shift+Enter for new line
            </p>
        </div>
    );
};

export default MessageInput;
