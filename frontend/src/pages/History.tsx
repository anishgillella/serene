import React, { useEffect, useState } from 'react';
import { History as HistoryIcon, Loader2, Search, Filter } from 'lucide-react';
import Timeline from '../components/history/Timeline';

interface Conflict {
  id: string;
  date: string;
  status: string;
  duration?: string;
  summary?: string;
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const History = () => {
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'resolved'>('all');

  useEffect(() => {
    const fetchConflicts = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/conflicts`, {
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

  const handleStatusChange = async (conflictId: string, newStatus: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/conflicts/${conflictId}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: newStatus }),
      });

      if (response.ok) {
        setConflicts(prevConflicts =>
          prevConflicts.map(c =>
            c.id === conflictId ? { ...c, status: newStatus } : c
          )
        );
      } else {
        console.error('Failed to update status');
      }
    } catch (error) {
      console.error('Error updating status:', error);
    }
  };

  // Filter conflicts
  const filteredConflicts = conflicts.filter(conflict => {
    const matchesSearch = (conflict.summary?.toLowerCase().includes(searchQuery.toLowerCase()) || false) ||
      conflict.date.includes(searchQuery);
    const matchesStatus = statusFilter === 'all' || conflict.status.toLowerCase() === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Calculate stats
  const totalConflicts = conflicts.length;
  const completedConflicts = conflicts.filter(c => c.status.toLowerCase() === 'completed' || c.status.toLowerCase() === 'resolved').length;
  const resolutionRate = totalConflicts > 0 ? Math.round((completedConflicts / totalConflicts) * 100) : 0;

  // Calculate streak
  const lastConflictDate = conflicts.length > 0 ? new Date(conflicts[0].date) : new Date();
  const today = new Date();
  const streakDays = Math.floor((today.getTime() - lastConflictDate.getTime()) / (1000 * 3600 * 24));
  const displayStreak = conflicts.length === 0 ? 0 : Math.max(0, streakDays);

  // Calculate average duration
  const totalDurationMinutes = conflicts.reduce((sum, c) => {
    if (c.duration) {
      const match = c.duration.match(/(\d+)m/);
      if (match && match[1]) {
        return sum + parseInt(match[1], 10);
      }
    }
    return sum;
  }, 0);
  const avgDuration = conflicts.length > 0 ? Math.round(totalDurationMinutes / conflicts.length) : 0;

  const stats = {
    total: totalConflicts,
    resolutionRate: resolutionRate,
    avgDuration: avgDuration,
    streak: displayStreak,
  };

  return (
    <div className="min-h-screen bg-bg-primary p-4 md:p-8 font-sans text-text-primary">
      <div className="max-w-4xl mx-auto py-8">
        {/* Header */}
        <div className="mb-12">
          <h2 className="text-h2 text-text-primary mb-3">Conflict History</h2>
          <p className="text-body text-text-secondary max-w-2xl">
            Review past conflicts, track resolutions, and monitor your relationship health over time.
          </p>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
          <div className="bg-surface-elevated p-5 rounded-2xl border border-border-subtle shadow-soft">
            <div className="text-tiny font-medium text-text-tertiary uppercase tracking-wider mb-2">Total Conflicts</div>
            <div className="text-h2 text-text-primary">{stats.total}</div>
          </div>
          <div className="bg-surface-elevated p-5 rounded-2xl border border-border-subtle shadow-soft">
            <div className="text-tiny font-medium text-text-tertiary uppercase tracking-wider mb-2">Resolution Rate</div>
            <div className="text-h2 text-emerald-600">{stats.resolutionRate}%</div>
          </div>
          <div className="bg-surface-elevated p-5 rounded-2xl border border-border-subtle shadow-soft">
            <div className="text-tiny font-medium text-text-tertiary uppercase tracking-wider mb-2">Avg Duration</div>
            <div className="text-h2 text-accent">{stats.avgDuration}m</div>
          </div>
          <div className="bg-surface-elevated p-5 rounded-2xl border border-border-subtle shadow-soft">
            <div className="text-tiny font-medium text-text-tertiary uppercase tracking-wider mb-2">Current Streak</div>
            <div className="text-h2 text-blue-500">{stats.streak} days</div>
          </div>
        </div>

        {/* Filters & Search */}
        <div className="flex flex-col md:flex-row gap-4 mb-8 sticky top-4 z-20 bg-surface-base/80 backdrop-blur-md p-2 rounded-2xl border border-border-subtle shadow-sm">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-text-tertiary" size={20} />
            <input
              type="text"
              placeholder="Search conflicts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-3 bg-surface-hover border border-transparent focus:bg-white focus:border-accent rounded-xl outline-none transition-all"
            />
          </div>
          <div className="flex gap-2 overflow-x-auto pb-2 md:pb-0">
            {['all', 'active', 'resolved'].map((filter) => (
              <button
                key={filter}
                onClick={() => setStatusFilter(filter as 'all' | 'active' | 'resolved')}
                className={`px-6 py-3 rounded-xl font-medium capitalize whitespace-nowrap transition-all ${statusFilter === filter
                  ? 'bg-accent text-white shadow-md transform scale-105'
                  : 'bg-surface-hover text-text-secondary hover:bg-white hover:shadow-sm'
                  }`}
              >
                {filter}
              </button>
            ))}
          </div>
        </div>

        {/* Timeline */}
        {loading ? (
          <div className="flex justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent"></div>
          </div>
        ) : filteredConflicts.length > 0 ? (
          <Timeline conflicts={filteredConflicts} onStatusChange={handleStatusChange} />
        ) : (
          <div className="text-center py-20 bg-surface-elevated rounded-3xl border border-border-subtle border-dashed">
            <div className="w-16 h-16 bg-surface-hover rounded-full flex items-center justify-center mx-auto mb-4 text-text-tertiary">
              <Filter size={24} />
            </div>
            <h3 className="text-h3 text-text-primary mb-2">No conflicts found</h3>
            <p className="text-text-secondary">Try adjusting your filters or search query</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default History;
