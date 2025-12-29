import React from 'react';

interface TypingIndicatorProps {
    partnerName?: string;
}

const TypingIndicator: React.FC<TypingIndicatorProps> = ({ partnerName = 'Partner' }) => {
    return (
        <div className="flex items-center gap-2 px-4 py-2">
            <div className="flex items-center gap-3 bg-surface-card border border-border-subtle rounded-2xl rounded-bl-sm px-4 py-2.5 shadow-sm">
                <div className="flex gap-1">
                    <span
                        className="w-2 h-2 bg-text-tertiary rounded-full animate-bounce"
                        style={{ animationDelay: '0ms' }}
                    />
                    <span
                        className="w-2 h-2 bg-text-tertiary rounded-full animate-bounce"
                        style={{ animationDelay: '150ms' }}
                    />
                    <span
                        className="w-2 h-2 bg-text-tertiary rounded-full animate-bounce"
                        style={{ animationDelay: '300ms' }}
                    />
                </div>
                <span className="text-xs text-text-tertiary">
                    {partnerName} is typing...
                </span>
            </div>
        </div>
    );
};

export default TypingIndicator;
