import React, { useState } from 'react';
import { Bell, History } from 'lucide-react';
import { useRelationship } from '../contexts/RelationshipContext';
import { useAlerts } from '../hooks/useAlerts';
import AlertCard from '../components/alerts/AlertCard';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const Notifications: React.FC = () => {
  const { relationshipId } = useRelationship();
  const rid = relationshipId || '00000000-0000-0000-0000-000000000000';
  const { alerts, loading, error, dismissAlert, snoozeAlert } = useAlerts(rid);
  const [showHistory, setShowHistory] = useState(false);
  const [historyAlerts, setHistoryAlerts] = useState<any[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const handleShowHistory = async () => {
    if (showHistory) {
      setShowHistory(false);
      return;
    }
    setHistoryLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/alerts/history?relationship_id=${rid}`,
        { headers: { 'ngrok-skip-browser-warning': 'true' } }
      );
      if (res.ok) {
        const data = await res.json();
        setHistoryAlerts(data.alerts || []);
      }
    } catch (e) {
      console.error('Error fetching alert history:', e);
    } finally {
      setHistoryLoading(false);
      setShowHistory(true);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <Bell size={24} className="text-accent" />
          <h1 className="text-h1 text-text-primary">Notifications</h1>
          {alerts.length > 0 && (
            <span className="px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 text-tiny font-medium">
              {alerts.length} active
            </span>
          )}
        </div>
        <button
          onClick={handleShowHistory}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-small text-text-secondary hover:bg-surface-hover transition-colors"
        >
          <History size={16} />
          {showHistory ? 'Hide History' : 'History'}
        </button>
      </div>

      {/* Active Alerts */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-surface-elevated rounded-2xl p-5 border border-border-subtle animate-pulse">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-full bg-surface-hover" />
                <div className="flex-1">
                  <div className="h-4 bg-surface-hover rounded w-1/2 mb-2" />
                  <div className="h-3 bg-surface-hover rounded w-3/4" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="text-center py-12 text-text-secondary">
          <p>Error loading alerts: {error}</p>
        </div>
      ) : alerts.length === 0 ? (
        <div className="text-center py-16">
          <Bell size={48} className="text-text-tertiary mx-auto mb-4" />
          <h3 className="text-h3 text-text-primary mb-2">All clear</h3>
          <p className="text-small text-text-secondary">
            No active alerts right now. Luna will notify you if she detects patterns that need attention.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {alerts.map((alert) => (
            <AlertCard
              key={alert.id}
              alert={alert}
              onDismiss={dismissAlert}
              onSnooze={snoozeAlert}
            />
          ))}
        </div>
      )}

      {/* History */}
      {showHistory && (
        <div className="mt-8">
          <h2 className="text-h3 text-text-primary mb-4">Alert History</h2>
          {historyLoading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-accent mx-auto" />
            </div>
          ) : historyAlerts.length === 0 ? (
            <p className="text-small text-text-secondary text-center py-8">No alert history yet.</p>
          ) : (
            <div className="space-y-3 opacity-75">
              {historyAlerts.map((alert) => (
                <AlertCard
                  key={alert.id}
                  alert={alert}
                  onDismiss={() => {}}
                  onSnooze={() => {}}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Notifications;
