export interface GestureConfig {
    type: 'hug' | 'kiss' | 'thinking_of_you';
    emoji: string;
    label: string;
    color: string;
    bgColor: string;
    borderColor: string;
    animation: string;
    celebrationEmojis: string[];
}

export const GESTURE_CONFIG: Record<string, GestureConfig> = {
    hug: {
        type: 'hug',
        emoji: '🤗',
        label: 'Hug',
        color: 'text-amber-600',
        bgColor: 'bg-amber-50',
        borderColor: 'border-amber-200',
        animation: 'animate-bounce',
        celebrationEmojis: ['🤗', '💛', '🧡', '✨', '💫', '🌟']
    },
    kiss: {
        type: 'kiss',
        emoji: '💋',
        label: 'Kiss',
        color: 'text-pink-600',
        bgColor: 'bg-pink-50',
        borderColor: 'border-pink-200',
        animation: 'animate-pulse',
        celebrationEmojis: ['💋', '💕', '💖', '💗', '💓', '❤️', '💘']
    },
    thinking_of_you: {
        type: 'thinking_of_you',
        emoji: '💚',
        label: 'Thinking of You',
        color: 'text-emerald-600',
        bgColor: 'bg-emerald-50',
        borderColor: 'border-emerald-200',
        animation: 'animate-pulse',
        celebrationEmojis: ['💚', '💭', '✨', '🌟', '💫', '🌿', '🍀']
    }
};

export type GestureType = keyof typeof GESTURE_CONFIG;
