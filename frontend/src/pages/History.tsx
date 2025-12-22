import React, { useEffect, useState } from 'react';
import { History as HistoryIcon, Loader2, CheckSquare, X, Trash2 } from 'lucide-react';
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
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    const fetchConflicts = async () => {
      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
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

  const handleDelete = async (id: string) => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/conflicts/${id}`, {
        method: 'DELETE',
        headers: {
          'ngrok-skip-browser-warning': 'true'
        }
      });

      if (response.ok) {
        setConflicts(prev => prev.filter(c => c.id !== id));
      } else {
        console.error('Failed to delete conflict');
        alert('Failed to delete conflict. Please try again.');
      }
    } catch (error) {
      console.error('Error deleting conflict:', error);
      alert('Error deleting conflict. Please try again.');
    }
  };

  const handleClearTestData = async () => {
    if (!window.confirm('Are you sure you want to delete all conflicts with title "Conflict Session"? This cannot be undone.')) {
      return;
    }

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/conflicts/cleanup?title=Conflict Session`, {
        method: 'DELETE',
        headers: {
          'ngrok-skip-browser-warning': 'true'
        }
      });

      if (response.ok) {
        const data = await response.json();
        alert(data.message);
        // Refresh list
        setConflicts(prev => prev.filter(c => c.summary !== 'Conflict Session'));
      } else {
        console.error('Failed to clear test data');
        alert('Failed to clear test data. Please try again.');
      }
    } catch (error) {
      console.error('Error clearing test data:', error);
      alert('Error clearing test data. Please try again.');
    }
  };

  const handleToggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    if (selectedIds.size === filteredConflicts.length) {
      // Deselect all
      setSelectedIds(new Set());
    } else {
      // Select all filtered conflicts
      setSelectedIds(new Set(filteredConflicts.map(c => c.id)));
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;

    const count = selectedIds.size;
    if (!window.confirm(`Are you sure you want to delete ${count} conflict${count > 1 ? 's' : ''}? This cannot be undone.`)) {
      return;
    }

    setIsDeleting(true);
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/conflicts/bulk-delete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({ conflict_ids: Array.from(selectedIds) })
      });

      if (response.ok) {
        const data = await response.json();
        // Remove deleted conflicts from state
        setConflicts(prev => prev.filter(c => !selectedIds.has(c.id)));
        setSelectedIds(new Set());
        setIsSelectionMode(false);
        alert(`Successfully deleted ${data.deleted_count} conflict${data.deleted_count > 1 ? 's' : ''}`);
      } else {
        const errorData = await response.json();
        console.error('Failed to bulk delete conflicts:', errorData);
        alert('Failed to delete conflicts. Please try again.');
      }
    } catch (error) {
      console.error('Error bulk deleting conflicts:', error);
      alert('Error deleting conflicts. Please try again.');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleCancelSelection = () => {
    setIsSelectionMode(false);
    setSelectedIds(new Set());
  };

  return (
    <div className="min-h-screen bg-bg-primary p-4 md:p-8 font-sans text-text-primary">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12 animate-fade-in relative">
          <h2 className="text-h2 text-text-primary flex items-center justify-center gap-3 mb-2">
            <HistoryIcon className="text-accent" size={28} strokeWidth={1.5} />
            Conflict History
          </h2>
          <p className="text-body text-text-secondary">
            Your relationship journey and growth over time
          </p>

          {/* Action Buttons */}
          <div className="absolute right-0 top-0 flex items-center gap-2">
            {!isSelectionMode ? (
              <>
                <button
                  onClick={() => setIsSelectionMode(true)}
                  className="text-tiny text-text-tertiary hover:text-accent transition-colors hidden md:flex items-center gap-1"
                  title="Select multiple conflicts to delete"
                >
                  <CheckSquare size={14} />
                  Select
                </button>
                <button
                  onClick={handleClearTestData}
                  className="text-tiny text-text-tertiary hover:text-red-500 transition-colors hidden md:block"
                  title="Remove all 'Conflict Session' entries"
                >
                  Clear Test Data
                </button>
              </>
            ) : (
              <button
                onClick={handleCancelSelection}
                className="text-tiny text-text-tertiary hover:text-text-primary transition-colors flex items-center gap-1"
              >
                <X size={14} />
                Cancel
              </button>
            )}
          </div>
        </div>

        {/* Selection Mode Bar */}
        {isSelectionMode && (
          <div className="mb-6 p-4 bg-surface-elevated rounded-xl border border-accent/30 flex items-center justify-between animate-fade-in">
            <div className="flex items-center gap-4">
              <button
                onClick={handleSelectAll}
                className="text-small font-medium text-accent hover:text-accent/80 transition-colors"
              >
                {selectedIds.size === filteredConflicts.length ? 'Deselect All' : 'Select All'}
              </button>
              <span className="text-small text-text-secondary">
                {selectedIds.size} selected
              </span>
            </div>
            <button
              onClick={handleBulkDelete}
              disabled={selectedIds.size === 0 || isDeleting}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-small font-medium transition-all ${
                selectedIds.size === 0
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-red-500 text-white hover:bg-red-600'
              }`}
            >
              {isDeleting ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Trash2 size={16} />
              )}
              Delete Selected
            </button>
          </div>
        )}

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
              <Timeline
                conflicts={filteredConflicts}
                onDelete={handleDelete}
                isSelectionMode={isSelectionMode}
                selectedIds={selectedIds}
                onToggleSelect={handleToggleSelect}
              />
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
