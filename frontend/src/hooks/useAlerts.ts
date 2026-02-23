import { useState, useEffect, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface Alert {
  id: string;
  relationship_id: string;
  alert_type: string;
  severity: string;
  title: string;
  message: string;
  context: Record<string, any> | null;
  is_dismissed: boolean;
  dismissed_by: string | null;
  snoozed_until: string | null;
  delivered_in_chat: boolean;
  created_at: string | null;
}

export function useAlerts(relationshipId: string) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/alerts?relationship_id=${relationshipId}`,
        { headers: { 'ngrok-skip-browser-warning': 'true' } }
      );
      if (!res.ok) throw new Error('Failed to fetch alerts');
      const data = await res.json();
      setAlerts(data.alerts || []);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [relationshipId]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  const dismissAlert = useCallback(async (alertId: string) => {
    try {
      await fetch(`${API_BASE}/api/alerts/${alertId}/dismiss`, {
        method: 'POST',
        headers: { 'ngrok-skip-browser-warning': 'true' },
      });
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    } catch (e) {
      console.error('Error dismissing alert:', e);
    }
  }, []);

  const snoozeAlert = useCallback(async (alertId: string, hours: number = 4) => {
    try {
      await fetch(`${API_BASE}/api/alerts/${alertId}/snooze?hours=${hours}`, {
        method: 'POST',
        headers: { 'ngrok-skip-browser-warning': 'true' },
      });
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    } catch (e) {
      console.error('Error snoozing alert:', e);
    }
  }, []);

  return { alerts, loading, error, refetch: fetchAlerts, dismissAlert, snoozeAlert };
}

export function useUnreadAlertCount(relationshipId: string) {
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetch_ = async () => {
      try {
        const res = await fetch(
          `${API_BASE}/api/alerts/unread-count?relationship_id=${relationshipId}`,
          { headers: { 'ngrok-skip-browser-warning': 'true' } }
        );
        if (res.ok) {
          const data = await res.json();
          setCount(data.count || 0);
        }
      } catch {
        // Silent fail for badge
      } finally {
        setLoading(false);
      }
    };
    fetch_();
  }, [relationshipId]);

  return { count, loading };
}
