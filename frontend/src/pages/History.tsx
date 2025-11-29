import React, { useEffect, useState } from 'react';
import { History as HistoryIcon, Loader2 } from 'lucide-react';
import HistoryStats from '../components/history/HistoryStats';
import FilterBar from '../components/history/FilterBar';
import Timeline from '../components/history/Timeline';

interface Conflict {
  id: string;
  date: string;
  status: string;
  duration?: string;
  summary?: string;
}

const History = () => {
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'completed'>('all');

  useEffect(() => {
    const fetchConflicts = async () => {
      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
        const response = await fetch(`${apiUrl}/api/conflicts`, {
          headers: {
            'ngrok-skip-browser-warning': 'true'
          }
        });
        if (response.ok) {
          const data = await response.json();
          // Transform data to match Conflict interface if needed
          // Assuming API returns list of conflicts with created_at, status, title/summary
          const transformedData = data.conflicts ? data.conflicts.map((item: any) => ({
            id: item.id,
            date: item.started_at || item.created_at, // Handle different field names
            status: item.status,
            duration: item.duration || '25m', // Placeholder if not available
            summary: item.title || 'Conflict Session'
          })) : [];

          // Sort by date descending
          transformedData.sort((a: Conflict, b: Conflict) => new Date(b.date).getTime() - new Date(a.date).getTime());

          setConflicts(transformedData);
        }
      } catch (error) {
        console.error('Error fetching conflicts:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchConflicts();
  }, []);

  // Filter conflicts
  const filteredConflicts = conflicts.filter(conflict => {
    const matchesSearch = (conflict.summary?.toLowerCase().includes(searchQuery.toLowerCase()) || false) ||
      conflict.date.includes(searchQuery);
    const matchesStatus = statusFilter === 'all' || conflict.status.toLowerCase() === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Calculate stats
  const totalConflicts = conflicts.length;
  const completedConflicts = conflicts.filter(c => c.status.toLowerCase() === 'completed').length;
  const resolutionRate = totalConflicts > 0 ? Math.round((completedConflicts / totalConflicts) * 100) : 0;

  // Calculate streak
  const lastConflictDate = conflicts.length > 0 ? new Date(conflicts[0].date) : new Date();
  const today = new Date();
  const streakDays = Math.floor((today.getTime() - lastConflictDate.getTime()) / (1000 * 3600 * 24));
  // If no conflicts, streak is 0 or maybe infinite? Let's say 0 for now if empty, or days since start if we knew that.
  // Actually, if last conflict was today, streak is 0. If yesterday, 1.
  const displayStreak = conflicts.length === 0 ? 0 : Math.max(0, streakDays);

  return (
    <div className="min-h-screen bg-bg-primary p-4 md:p-8 font-sans text-text-primary">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12 animate-fade-in">
          <h2 className="text-h2 text-text-primary flex items-center justify-center gap-3 mb-2">
            <HistoryIcon className="text-accent" size={28} strokeWidth={1.5} />
            Conflict History
          </h2>
          <p className="text-body text-text-secondary">
            Your relationship journey and growth over time
          </p>
        </div>

        {loading ? (
          <div className="flex justify-center items-center h-64">
            <Loader2 className="animate-spin text-accent" size={32} />
          </div>
        ) : (
          <div className="animate-slide-up">
            <HistoryStats
              totalConflicts={totalConflicts}
              resolutionRate={resolutionRate}
              streakDays={displayStreak}
            />

            <FilterBar
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              statusFilter={statusFilter}
              onStatusFilterChange={setStatusFilter}
            />

            {filteredConflicts.length > 0 ? (
              <Timeline conflicts={filteredConflicts} />
            ) : (
              <div className="text-center py-12 bg-surface-elevated rounded-2xl border border-border-subtle border-dashed shadow-soft">
                <div className="text-h3 text-text-secondary mb-2">No conflicts found</div>
                <p className="text-body text-text-tertiary">
                  {searchQuery || statusFilter !== 'all'
                    ? "Try adjusting your filters"
                    : "Your relationship is in harmony!"}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default History;
