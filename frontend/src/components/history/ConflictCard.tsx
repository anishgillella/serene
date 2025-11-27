import React from 'react';
import { Calendar, Clock, ArrowRight, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface Conflict {
    id: string;
    date: string;
    status: string;
    duration?: string;
    summary?: string;
}

interface ConflictCardProps {
    conflict: Conflict;
}

const ConflictCard: React.FC<ConflictCardProps> = ({ conflict }) => {
    const navigate = useNavigate();
    const dateObj = new Date(conflict.date);
    const formattedDate = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    const formattedTime = dateObj.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });

    const isActive = conflict.status.toLowerCase() === 'active';

    return (
        <div
            onClick={() => navigate('/post-fight', { state: { conflict_id: conflict.id } })}
            className="group relative bg-surface-elevated rounded-2xl p-5 border border-border-subtle shadow-soft transition-all duration-300 hover:shadow-lifted hover:border-accent/30 cursor-pointer"
        >
            {/* Status Dot */}
            <div className={`absolute top-5 right-5 w-2.5 h-2.5 rounded-full ${isActive ? 'bg-amber-400' : 'bg-green-500'}`} />

            <div className="flex flex-col h-full">
                {/* Header */}
                <div className="mb-3">
                    <div className="flex items-center gap-2 text-tiny font-medium text-text-tertiary uppercase tracking-wider mb-1">
                        <Calendar size={12} />
                        <span>{formattedDate}</span>
                        <span>•</span>
                        <span>{formattedTime}</span>
                    </div>
                    <h3 className="text-body font-medium text-text-primary group-hover:text-accent transition-colors">
                        {conflict.summary || 'Conflict Session'}
                    </h3>
                </div>

                {/* Details */}
                <div className="mt-auto flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className={`flex items-center gap-1.5 text-tiny px-2 py-0.5 rounded-full border ${isActive
                                ? 'bg-amber-50 text-amber-700 border-amber-100'
                                : 'bg-green-50 text-green-700 border-green-100'
                            }`}>
                            {isActive ? <AlertCircle size={12} /> : <CheckCircle2 size={12} />}
                            <span className="font-medium capitalize">{conflict.status}</span>
                        </div>

                        {conflict.duration && (
                            <div className="flex items-center gap-1.5 text-tiny text-text-tertiary">
                                <Clock size={12} />
                                <span>{conflict.duration}</span>
                            </div>
                        )}
                    </div>

                    <div className="w-8 h-8 rounded-full bg-surface-hover flex items-center justify-center text-text-tertiary opacity-0 group-hover:opacity-100 transition-all transform translate-x-2 group-hover:translate-x-0">
                        <ArrowRight size={16} strokeWidth={1.5} />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ConflictCard;
