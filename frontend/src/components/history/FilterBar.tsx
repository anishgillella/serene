import React from 'react';
import { Search, Filter } from 'lucide-react';

interface FilterBarProps {
    searchQuery: string;
    onSearchChange: (query: string) => void;
    statusFilter: 'all' | 'active' | 'completed';
    onStatusFilterChange: (status: 'all' | 'active' | 'completed') => void;
}

const FilterBar: React.FC<FilterBarProps> = ({
    searchQuery,
    onSearchChange,
    statusFilter,
    onStatusFilterChange
}) => {
    return (
        <div className="flex flex-col sm:flex-row gap-4 mb-8">
            <div className="relative flex-1">
                <Search size={18} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-text-tertiary" strokeWidth={1.5} />
                <input
                    type="text"
                    placeholder="Search conflicts..."
                    value={searchQuery}
                    onChange={(e) => onSearchChange(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 bg-surface-elevated border border-border-subtle rounded-xl text-small text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all shadow-soft"
                />
            </div>

            <div className="flex gap-2">
                <button
                    onClick={() => onStatusFilterChange('all')}
                    className={`px-4 py-2.5 rounded-xl text-small font-medium transition-all border ${statusFilter === 'all'
                            ? 'bg-text-primary text-white border-text-primary shadow-md'
                            : 'bg-surface-elevated text-text-secondary border-border-subtle hover:border-border-medium hover:text-text-primary'
                        }`}
                >
                    All
                </button>
                <button
                    onClick={() => onStatusFilterChange('active')}
                    className={`px-4 py-2.5 rounded-xl text-small font-medium transition-all border ${statusFilter === 'active'
                            ? 'bg-amber-100 text-amber-800 border-amber-200'
                            : 'bg-surface-elevated text-text-secondary border-border-subtle hover:border-border-medium hover:text-text-primary'
                        }`}
                >
                    Active
                </button>
                <button
                    onClick={() => onStatusFilterChange('completed')}
                    className={`px-4 py-2.5 rounded-xl text-small font-medium transition-all border ${statusFilter === 'completed'
                            ? 'bg-green-100 text-green-800 border-green-200'
                            : 'bg-surface-elevated text-text-secondary border-border-subtle hover:border-border-medium hover:text-text-primary'
                        }`}
                >
                    Resolved
                </button>
            </div>
        </div>
    );
};

export default FilterBar;
