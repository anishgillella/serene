import { useState, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const defaultHeaders = { 'ngrok-skip-browser-warning': 'true' };

export const useNarrativeInsights = (relationshipId: string, viewerRole?: string | null) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch_ = useCallback(async () => {
    if (!relationshipId) return;
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams({ relationship_id: relationshipId });
      if (viewerRole) {
        params.append('viewer_role', viewerRole);
      }
      const res = await fetch(
        `${API_BASE}/api/analytics/advanced/narrative-insights?${params}`,
        { headers: defaultHeaders }
      );
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      setData(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [relationshipId, viewerRole]);

  return { data, loading, error, refresh: fetch_ };
};
