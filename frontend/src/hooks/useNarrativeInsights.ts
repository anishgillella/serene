import { useState, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const defaultHeaders: Record<string, string> = {
  'ngrok-skip-browser-warning': 'true',
  'Content-Type': 'application/json',
};

interface MetricSources {
  dashboard?: any;
  gottman?: any;
  sentiment?: any;
  growth?: any;
  frequency?: any;
  recovery?: any;
  attachment?: any;
  bid_response?: any;
}

export const useNarrativeInsights = (relationshipId: string, viewerRole?: string | null) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchNarrative = useCallback(async (metrics: MetricSources = {}) => {
    if (!relationshipId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(
        `${API_BASE}/api/analytics/advanced/narrative-insights`,
        {
          method: 'POST',
          headers: defaultHeaders,
          body: JSON.stringify({
            relationship_id: relationshipId,
            viewer_role: viewerRole || null,
            metrics,
          }),
        }
      );
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      setData(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [relationshipId, viewerRole]);

  return { data, loading, error, refresh: fetchNarrative };
};
