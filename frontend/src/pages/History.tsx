import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ClockIcon, CalendarIcon, ChevronRightIcon, LoaderIcon, AlertCircleIcon, FileTextIcon, MessageSquareIcon, ChevronDownIcon, ChevronUpIcon } from 'lucide-react';

interface Conflict {
  id: string;
  relationship_id: string;
  started_at: string;
  ended_at: string | null;
  status: string;
  metadata?: any;
}

interface ConflictWithConversations extends Conflict {
}

const History = () => {
  const navigate = useNavigate();
  const [conflicts, setConflicts] = useState<ConflictWithConversations[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const apiUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

  useEffect(() => {
    loadConflicts();
  }, []);

  const loadConflicts = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`${apiUrl}/api/conflicts`);
      
      if (!response.ok) {
        // Only throw error for actual server errors (5xx)
        if (response.status >= 500) {
          throw new Error('Server error loading conflicts');
        }
        // For 404 or other client errors, treat as empty list (no conflicts exist yet)
        setConflicts([]);
        setLoading(false);
        return;
      }
      
      const data = await response.json();
      // Handle empty response gracefully - empty array is valid
      const conflictsList = data.conflicts || [];
      
      // Sort by started_at descending (most recent first)
      const sortedConflicts = conflictsList.sort((a: Conflict, b: Conflict) => {
        const dateA = new Date(a.started_at).getTime();
        const dateB = new Date(b.started_at).getTime();
        return dateB - dateA;
      });
      
      // No conversations to load - Private Rant removed
      setConflicts(sortedConflicts.map(conflict => ({ ...conflict, conversations: [], messageCount: 0 })));
    } catch (err: any) {
      // Only show error for actual network/server errors
      console.error('Error loading conflicts:', err);
      setError(err.message || 'Failed to load conflict history');
    } finally {
      setLoading(false);
    }
  };



  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Ongoing';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatDuration = (started: string, ended: string | null) => {
    if (!ended) return 'In progress';
    const start = new Date(started);
    const end = new Date(ended);
    const diffMs = end.getTime() - start.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffSecs = Math.floor((diffMs % 60000) / 1000);
    
    if (diffMins > 0) {
      return `${diffMins}m ${diffSecs}s`;
    }
    return `${diffSecs}s`;
  };

  const handleConflictClick = (conflictId: string) => {
    console.log('🖱️ Clicking conflict:', conflictId);
    // Pass both in state and URL params for reliability
    navigate(`/post-fight?conflict_id=${conflictId}`, { 
      state: { conflict_id: conflictId } 
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-50 via-white to-blue-50">
      {/* Header */}
      <div className="bg-white/80 backdrop-blur-sm border-b border-pink-200 p-4">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-2xl font-semibold text-gray-800 flex items-center gap-2">
            <FileTextIcon size={24} className="text-rose-500" />
            Conflict History
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            View and access all your previous conflict sessions
          </p>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto p-6">
        {loading && (
          <div className="flex items-center justify-center py-12">
            <LoaderIcon size={24} className="animate-spin text-rose-500 mr-3" />
            <span className="text-gray-600">Loading conflicts...</span>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex items-center gap-3">
            <AlertCircleIcon size={20} className="text-red-600" />
            <div>
              <p className="text-red-800 font-medium">Error loading conflicts</p>
              <p className="text-red-600 text-sm">{error}</p>
            </div>
            <button
              onClick={loadConflicts}
              className="ml-auto px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm"
            >
              Retry
            </button>
          </div>
        )}

        {!loading && !error && conflicts.length === 0 && (
          <div className="text-center py-12">
            <FileTextIcon size={48} className="text-gray-300 mx-auto mb-4" />
            <p className="text-gray-600 text-lg mb-2">No conflicts found</p>
            <p className="text-gray-500 text-sm">
              Start a new fight capture session to begin tracking conflicts
            </p>
          </div>
        )}

        {!loading && !error && conflicts.length > 0 && (
          <div className="space-y-3">
            {conflicts.map((conflict) => {
              return (
                <div
                  key={conflict.id}
                  className="bg-white/80 backdrop-blur-sm rounded-xl border border-pink-200 hover:border-rose-300 hover:shadow-md transition-all group"
                >
                  {/* Conflict Header */}
                  <div 
                    onClick={() => handleConflictClick(conflict.id)}
                    className="p-4 cursor-pointer"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <div className={`w-2 h-2 rounded-full ${
                            conflict.status === 'active' ? 'bg-green-500' : 
                            conflict.status === 'completed' ? 'bg-blue-500' : 
                            'bg-gray-400'
                          }`} />
                          <span className="text-xs font-medium text-gray-600 uppercase">
                            {conflict.status || 'unknown'}
                          </span>
                          {conflict.ended_at && (
                            <span className="text-xs text-gray-500">
                              • {formatDuration(conflict.started_at, conflict.ended_at)}
                            </span>
                          )}
                        </div>
                        
                        <div className="flex items-center gap-4 text-sm text-gray-600 mb-2">
                          <div className="flex items-center gap-1">
                            <CalendarIcon size={14} />
                            <span>{formatDate(conflict.started_at)}</span>
                          </div>
                          {conflict.ended_at && (
                            <div className="flex items-center gap-1">
                              <ClockIcon size={14} />
                              <span>Ended: {formatDate(conflict.ended_at)}</span>
                            </div>
                          )}
                        </div>
                        
                        <div className="text-xs text-gray-500 font-mono">
                          ID: {conflict.id.substring(0, 8)}...
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <ChevronRightIcon 
                          size={20} 
                          className="text-gray-400 group-hover:text-rose-500 transition-colors" 
                        />
                      </div>
                    </div>
                  </div>

                </div>
              );
            })}
          </div>
        )}

        {/* Stats */}
        {!loading && !error && conflicts.length > 0 && (
          <div className="mt-8 bg-white/60 backdrop-blur-sm rounded-xl p-4 border border-pink-200">
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-2xl font-bold text-gray-800">{conflicts.length}</div>
                <div className="text-xs text-gray-600">Total Conflicts</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-green-600">
                  {conflicts.filter(c => c.status === 'completed').length}
                </div>
                <div className="text-xs text-gray-600">Completed</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-blue-600">
                  {conflicts.filter(c => c.status === 'active').length}
                </div>
                <div className="text-xs text-gray-600">Active</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default History;

