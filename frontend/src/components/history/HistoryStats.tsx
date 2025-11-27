import React from 'react';
import { CheckCircle2, Clock, Flame } from 'lucide-react';

interface HistoryStatsProps {
    totalConflicts: number;
    resolutionRate: number;
    streakDays: number;
}

const HistoryStats: React.FC<HistoryStatsProps> = ({ totalConflicts, resolutionRate, streakDays }) => {
    return (
        <div className="grid grid-cols-3 gap-4 mb-8">
            <div className="bg-surface-elevated rounded-xl p-4 border border-border-subtle shadow-soft flex flex-col items-center text-center">
                <div className="p-2 bg-surface-hover rounded-full mb-2">
                    <Clock size={20} className="text-text-secondary" strokeWidth={1.5} />
                </div>
                <div className="text-h2 text-text-primary mb-0.5">{totalConflicts}</div>
                <div className="text-tiny text-text-tertiary uppercase tracking-wider">Total Conflicts</div>
            </div>

            <div className="bg-surface-elevated rounded-xl p-4 border border-border-subtle shadow-soft flex flex-col items-center text-center">
                <div className="p-2 bg-surface-hover rounded-full mb-2">
                    <CheckCircle2 size={20} className="text-green-600" strokeWidth={1.5} />
                </div>
                <div className="text-h2 text-text-primary mb-0.5">{resolutionRate}%</div>
                <div className="text-tiny text-text-tertiary uppercase tracking-wider">Resolution Rate</div>
            </div>

            <div className="bg-surface-elevated rounded-xl p-4 border border-border-subtle shadow-soft flex flex-col items-center text-center">
                <div className="p-2 bg-surface-hover rounded-full mb-2">
                    <Flame size={20} className="text-amber-500" strokeWidth={1.5} />
                </div>
                <div className="text-h2 text-text-primary mb-0.5">{streakDays}</div>
                <div className="text-tiny text-text-tertiary uppercase tracking-wider">Day Streak</div>
            </div>
        </div>
    );
};

export default HistoryStats;
