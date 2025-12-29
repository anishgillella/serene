import React, { useState } from 'react';
import { Bot, AlertTriangle, X, ChevronRight, Check, ArrowRight } from 'lucide-react';

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

interface LunaSuggestionOverlayProps {
    suggestion: LunaSuggestion;
    onAccept: (text: string, alternativeIndex: number) => void;
    onReject: () => void;
    onCancel: () => void;
}

const LunaSuggestionOverlay: React.FC<LunaSuggestionOverlayProps> = ({
    suggestion,
    onAccept,
    onReject,
    onCancel
}) => {
    const [selectedIndex, setSelectedIndex] = useState(0);
    const [showAlternatives, setShowAlternatives] = useState(false);

    const allOptions = [
        { text: suggestion.primary_suggestion, tone: 'recommended', rationale: suggestion.suggestion_rationale },
        ...suggestion.alternatives
    ];

    const selectedOption = allOptions[selectedIndex];

    const getRiskColor = (risk: string) => {
        switch (risk) {
            case 'high_risk': return 'text-red-600 bg-red-50 border-red-200';
            case 'risky': return 'text-amber-600 bg-amber-50 border-amber-200';
            default: return 'text-green-600 bg-green-50 border-green-200';
        }
    };

    const getRiskLabel = (risk: string) => {
        switch (risk) {
            case 'high_risk': return 'High Risk';
            case 'risky': return 'Could Be Better';
            default: return 'Looks Good';
        }
    };

    const getToneEmoji = (tone: string) => {
        switch (tone) {
            case 'gentle': return '🕊️';
            case 'direct': return '🎯';
            case 'curious': return '🤔';
            case 'empathetic': return '💗';
            case 'playful': return '😊';
            case 'recommended': return '⭐';
            default: return '💬';
        }
    };

    const getToneColor = (tone: string) => {
        switch (tone) {
            case 'gentle': return 'bg-blue-100 text-blue-700';
            case 'direct': return 'bg-orange-100 text-orange-700';
            case 'curious': return 'bg-yellow-100 text-yellow-700';
            case 'empathetic': return 'bg-pink-100 text-pink-700';
            case 'playful': return 'bg-green-100 text-green-700';
            case 'recommended': return 'bg-purple-100 text-purple-700';
            default: return 'bg-gray-100 text-gray-700';
        }
    };

    return (
        <div className="absolute bottom-full left-0 right-0 mb-2 z-50 animate-in slide-in-from-bottom-2 duration-200">
            <div className="bg-white rounded-2xl border border-gray-200 shadow-2xl overflow-hidden mx-2">
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-gradient-to-r from-purple-50 to-white">
                    <div className="flex items-center gap-2">
                        <div className="p-1.5 bg-purple-100 rounded-lg">
                            <Bot size={18} className="text-purple-600" />
                        </div>
                        <span className="font-semibold text-gray-900">Luna's Suggestion</span>
                    </div>
                    <button
                        onClick={onCancel}
                        className="p-1.5 hover:bg-gray-100 rounded-full transition-colors"
                    >
                        <X size={18} className="text-gray-500" />
                    </button>
                </div>

                {/* Risk Assessment */}
                <div className="px-4 pt-3">
                    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium border ${getRiskColor(suggestion.risk_assessment)}`}>
                        {suggestion.risk_assessment !== 'safe' && <AlertTriangle size={14} />}
                        {getRiskLabel(suggestion.risk_assessment)}
                    </div>

                    {suggestion.detected_issues.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-2">
                            {suggestion.detected_issues.map((issue, idx) => (
                                <span
                                    key={idx}
                                    className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full"
                                >
                                    {issue}
                                </span>
                            ))}
                        </div>
                    )}
                </div>

                {/* Side-by-side comparison */}
                <div className="p-4 grid grid-cols-2 gap-3">
                    {/* Original */}
                    <div className="p-3 bg-red-50 rounded-xl border border-red-100">
                        <div className="flex items-center gap-1.5 mb-2">
                            <X size={14} className="text-red-500" />
                            <span className="text-xs font-semibold text-red-600 uppercase tracking-wide">Your message</span>
                        </div>
                        <p className="text-sm text-red-900 leading-relaxed">{suggestion.original_message}</p>
                    </div>

                    {/* Suggested */}
                    <div className="p-3 bg-green-50 rounded-xl border border-green-100">
                        <div className="flex items-center gap-1.5 mb-2">
                            <Check size={14} className="text-green-500" />
                            <span className={`text-xs font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded ${getToneColor(selectedOption.tone)}`}>
                                {getToneEmoji(selectedOption.tone)} {selectedOption.tone === 'recommended' ? 'Recommended' : selectedOption.tone}
                            </span>
                        </div>
                        <p className="text-sm text-green-900 leading-relaxed">{selectedOption.text}</p>
                    </div>
                </div>

                {/* Rationale */}
                <div className="px-4 pb-2">
                    <p className="text-xs text-gray-500 italic leading-relaxed">
                        "{selectedOption.rationale}"
                    </p>
                </div>

                {/* Underlying Need */}
                {suggestion.underlying_need && (
                    <div className="px-4 pb-3">
                        <div className="p-3 bg-purple-50 rounded-xl border border-purple-100">
                            <p className="text-xs font-semibold text-purple-600 mb-1">What you're really trying to say</p>
                            <p className="text-sm text-purple-900">{suggestion.underlying_need}</p>
                        </div>
                    </div>
                )}

                {/* Historical Context */}
                {suggestion.historical_context && (
                    <div className="px-4 pb-3">
                        <div className="p-3 bg-amber-50 rounded-xl border border-amber-100">
                            <p className="text-xs font-semibold text-amber-600 mb-1">From your history</p>
                            <p className="text-sm text-amber-900">{suggestion.historical_context}</p>
                        </div>
                    </div>
                )}

                {/* Alternatives Toggle */}
                {suggestion.alternatives.length > 0 && (
                    <div className="px-4 pb-3">
                        <button
                            onClick={() => setShowAlternatives(!showAlternatives)}
                            className="flex items-center gap-2 text-sm text-purple-600 hover:text-purple-700 font-medium transition-colors"
                        >
                            <ChevronRight
                                size={16}
                                className={`transition-transform duration-200 ${showAlternatives ? 'rotate-90' : ''}`}
                            />
                            {showAlternatives ? 'Hide' : 'Show'} {suggestion.alternatives.length} alternative{suggestion.alternatives.length > 1 ? 's' : ''}
                        </button>

                        {showAlternatives && (
                            <div className="mt-3 space-y-2">
                                {allOptions.map((alt, idx) => (
                                    <button
                                        key={idx}
                                        onClick={() => setSelectedIndex(idx)}
                                        className={`
                                            w-full p-3 rounded-xl text-left transition-all border-2
                                            ${selectedIndex === idx
                                                ? 'bg-purple-50 border-purple-400 shadow-sm'
                                                : 'bg-gray-50 border-transparent hover:border-purple-200 hover:bg-white'
                                            }
                                        `}
                                    >
                                        <div className="flex items-center gap-2 mb-1.5">
                                            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${getToneColor(alt.tone)}`}>
                                                {getToneEmoji(alt.tone)} {alt.tone}
                                            </span>
                                            {selectedIndex === idx && (
                                                <Check size={14} className="text-purple-600" />
                                            )}
                                        </div>
                                        <p className="text-sm text-gray-800">{alt.text}</p>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 p-4 border-t border-gray-100 bg-gray-50">
                    <button
                        onClick={() => onAccept(selectedOption.text, selectedIndex)}
                        className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-xl transition-colors shadow-sm"
                    >
                        <Check size={18} />
                        Use Suggestion
                    </button>
                    <button
                        onClick={onReject}
                        className="flex-1 flex items-center justify-center gap-2 py-3 px-4 bg-white hover:bg-gray-100 text-gray-700 font-medium rounded-xl border border-gray-200 transition-colors"
                    >
                        <ArrowRight size={18} />
                        Send Original
                    </button>
                </div>
            </div>
        </div>
    );
};

export default LunaSuggestionOverlay;
