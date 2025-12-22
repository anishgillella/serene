import React from 'react';
import ConflictCard from './ConflictCard';

interface Conflict {
    id: string;
    date: string;
    status: string;
    duration?: string;
    summary?: string;
}

interface TimelineProps {
    conflicts: Conflict[];
    onDelete: (id: string) => void;
    isSelectionMode?: boolean;
    selectedIds?: Set<string>;
    onToggleSelect?: (id: string) => void;
}

interface MonthSectionProps {
    month: string;
    conflicts: Conflict[];
    onDelete: (id: string) => void;
    isSelectionMode?: boolean;
    selectedIds?: Set<string>;
    onToggleSelect?: (id: string) => void;
}

const MonthSection: React.FC<MonthSectionProps> = ({
    month,
    conflicts,
    onDelete,
    isSelectionMode = false,
    selectedIds = new Set(),
    onToggleSelect
}) => {
    const [showAll, setShowAll] = React.useState(false);
    const INITIAL_COUNT = 4;
    const hasMore = conflicts.length > INITIAL_COUNT;
    const visibleConflicts = showAll ? conflicts : conflicts.slice(0, INITIAL_COUNT);

    return (
        <div className="relative pb-12 last:pb-0">
            {/* Timeline Line Overlay to cover the gap if needed, though main line is in parent */}

            {/* Month Header */}
            <div className="flex items-center mb-6 -ml-[41px]">
                <div className="w-4 h-4 rounded-full bg-surface-elevated border-2 border-accent z-10 shadow-sm" />
                <h3 className="ml-6 text-h3 text-text-primary font-medium">{month}</h3>
                <span className="ml-3 text-tiny text-text-tertiary font-medium bg-surface-hover px-2 py-0.5 rounded-full border border-border-subtle">
                    {conflicts.length}
                </span>
            </div>

            {/* Conflicts Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {visibleConflicts.map((conflict) => (
                    <ConflictCard
                        key={conflict.id}
                        conflict={conflict}
                        onDelete={onDelete}
                        isSelectionMode={isSelectionMode}
                        isSelected={selectedIds.has(conflict.id)}
                        onToggleSelect={onToggleSelect}
                    />
                ))}
            </div>

            {/* Show More Button */}
            {hasMore && (
                <div className="mt-4 flex justify-center md:justify-start">
                    <button
                        onClick={() => setShowAll(!showAll)}
                        className="text-small font-medium text-text-secondary hover:text-accent transition-colors flex items-center gap-1 bg-surface-hover hover:bg-white px-4 py-2 rounded-lg border border-transparent hover:border-border-subtle"
                    >
                        {showAll ? 'Show Less' : `Show ${conflicts.length - INITIAL_COUNT} More`}
                    </button>
                </div>
            )}
        </div>
    );
};

const Timeline: React.FC<TimelineProps> = ({
    conflicts,
    onDelete,
    isSelectionMode = false,
    selectedIds = new Set(),
    onToggleSelect
}) => {
    // Group conflicts by month
    const groupedConflicts = conflicts.reduce((acc, conflict) => {
        const date = new Date(conflict.date);
        const monthYear = date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

        if (!acc[monthYear]) {
            acc[monthYear] = [];
        }
        acc[monthYear].push(conflict);
        return acc;
    }, {} as Record<string, Conflict[]>);

    const months = Object.keys(groupedConflicts);

    return (
        <div className="relative pl-8 border-l-2 border-border-subtle ml-4 md:ml-8 space-y-0">
            {months.map((month) => (
                <MonthSection
                    key={month}
                    month={month}
                    conflicts={groupedConflicts[month]}
                    onDelete={onDelete}
                    isSelectionMode={isSelectionMode}
                    selectedIds={selectedIds}
                    onToggleSelect={onToggleSelect}
                />
            ))}
        </div>
    );
};

export default Timeline;
