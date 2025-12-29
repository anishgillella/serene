import React, { useState, useRef, useCallback } from 'react';
import { Send, Loader2, Bot } from 'lucide-react';
import LunaSuggestionOverlay from './LunaSuggestionOverlay';

interface Alternative {
    text: string;
    tone: string;
    rationale: string;
}

interface LunaSuggestion {
    suggestion_id: string | null;
    original_message: string;
    risk_assessment: 'safe' | 'risky' | 'high_risk';
    detected_issues: string[];
    primary_suggestion: string;
    suggestion_rationale: string;
    alternatives: Alternative[];
    underlying_need?: string;
    historical_context?: string;
}

interface MessageInputProps {
    conversationId: string;
    senderId: string;
    onSend: (content: string, originalContent?: string, lunaIntervened?: boolean) => void;
    onTyping: (isTyping: boolean) => void;
    disabled?: boolean;
    lunaEnabled?: boolean;
    suggestionMode?: 'always' | 'on_request' | 'high_risk_only' | 'off';
}

const MessageInput: React.FC<MessageInputProps> = ({
    conversationId,
    senderId,
    onSend,
    onTyping,
    disabled = false,
    lunaEnabled = true,
    suggestionMode = 'always'
}) => {
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [suggestion, setSuggestion] = useState<LunaSuggestion | null>(null);
    const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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

    const requestLunaReview = async (): Promise<LunaSuggestion | null> => {
        if (!input.trim()) return null;

        try {
            const response = await fetch(`${apiUrl}/api/partner-messages/suggest`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    conversation_id: conversationId,
                    sender_id: senderId,
                    draft_message: input.trim()
                })
            });

            if (!response.ok) throw new Error('Failed to get suggestion');
            return await response.json();
        } catch (err) {
            console.error('Luna review error:', err);
            return null;
        }
    };

    const recordSuggestionResponse = async (
        suggestionId: string,
        action: 'accepted' | 'rejected' | 'modified' | 'ignored',
        selectedIndex?: number
    ) => {
        try {
            await fetch(`${apiUrl}/api/partner-messages/suggestion/${suggestionId}/respond`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action,
                    selected_alternative_index: selectedIndex
                })
            });
        } catch (err) {
            console.error('Error recording suggestion response:', err);
        }
    };

    const handleSend = useCallback(async () => {
        const content = input.trim();
        if (!content || disabled || isLoading) return;

        // Clear typing indicator
        if (typingTimeoutRef.current) {
            clearTimeout(typingTimeoutRef.current);
        }
        onTyping(false);

        // Check if Luna should review this message
        if (lunaEnabled && suggestionMode !== 'off') {
            setIsLoading(true);
            try {
                const result = await requestLunaReview();

                if (result) {
                    // Determine if we should show suggestion based on mode and risk
                    const hasChanges = result.primary_suggestion !== result.original_message;
                    const isRisky = result.risk_assessment !== 'safe';

                    const shouldShowSuggestion =
                        (suggestionMode === 'always' && (isRisky || hasChanges)) ||
                        (suggestionMode === 'high_risk_only' && result.risk_assessment === 'high_risk');

                    if (shouldShowSuggestion) {
                        setSuggestion(result);
                        setIsLoading(false);
                        return; // Wait for user decision
                    }
                }
            } catch (err) {
                console.error('Error getting Luna suggestion:', err);
            }
            setIsLoading(false);
        }

        // Send message directly (Luna is off, message is safe, or error occurred)
        onSend(content);
        setInput('');

        // Reset textarea height
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
        }
    }, [input, disabled, isLoading, onSend, onTyping, lunaEnabled, suggestionMode, conversationId, senderId]);

    const handleAcceptSuggestion = async (text: string, alternativeIndex: number) => {
        if (!suggestion) return;

        // Record the response
        if (suggestion.suggestion_id) {
            await recordSuggestionResponse(suggestion.suggestion_id, 'accepted', alternativeIndex);
        }

        // Send the accepted suggestion, storing original
        onSend(text, suggestion.original_message, true);
        setInput('');
        setSuggestion(null);
        onTyping(false);

        // Reset textarea height
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
        }
    };

    const handleRejectSuggestion = async () => {
        if (!suggestion) return;

        // Record the rejection
        if (suggestion.suggestion_id) {
            await recordSuggestionResponse(suggestion.suggestion_id, 'rejected');
        }

        // Send original message
        onSend(suggestion.original_message, undefined, false);
        setInput('');
        setSuggestion(null);
        onTyping(false);

        // Reset textarea height
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
        }
    };

    const handleCancelSuggestion = async () => {
        if (suggestion?.suggestion_id) {
            await recordSuggestionResponse(suggestion.suggestion_id, 'ignored');
        }
        setSuggestion(null);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="relative p-4 border-t border-border-subtle bg-surface-card">
            {/* Luna Suggestion Overlay */}
            {suggestion && (
                <LunaSuggestionOverlay
                    suggestion={suggestion}
                    onAccept={handleAcceptSuggestion}
                    onReject={handleRejectSuggestion}
                    onCancel={handleCancelSuggestion}
                />
            )}

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

                    {/* Luna indicator when enabled */}
                    {lunaEnabled && suggestionMode !== 'off' && (
                        <div className="absolute right-3 bottom-3 flex items-center gap-1">
                            <Bot size={14} className="text-purple-400" />
                            <span className="text-[10px] text-purple-400">Luna</span>
                        </div>
                    )}
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
                {lunaEnabled && suggestionMode !== 'off'
                    ? "Luna will review your message before sending"
                    : "Press Enter to send, Shift+Enter for new line"
                }
            </p>
        </div>
    );
};

export default MessageInput;
