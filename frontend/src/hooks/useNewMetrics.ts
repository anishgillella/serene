import { useState, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const defaultHeaders = { 'ngrok-skip-browser-warning': 'true' };

// ============================================================================
// 1. Sentiment Shift
// ============================================================================
export const useSentimentShift = (relationshipId: string) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch_ = useCallback(async () => {
    if (!relationshipId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(
        `${API_BASE}/api/analytics/advanced/sentiment-shift?relationship_id=${relationshipId}`,
        { headers: defaultHeaders }
      );
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      setData(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [relationshipId]);

  return { data, loading, error, refresh: fetch_ };
};

// ============================================================================
// 2. Communication Growth
// ============================================================================
export const useCommunicationGrowth = (relationshipId: string) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch_ = useCallback(async (months = 6) => {
    if (!relationshipId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(
        `${API_BASE}/api/analytics/advanced/communication-growth?relationship_id=${relationshipId}&months=${months}`,
        { headers: defaultHeaders }
      );
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      setData(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [relationshipId]);

  return { data, loading, error, refresh: fetch_ };
};

// ============================================================================
// 3. Fight Frequency
// ============================================================================
export const useFightFrequency = (relationshipId: string) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch_ = useCallback(async (period = 'weekly', periods = 12) => {
    if (!relationshipId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(
        `${API_BASE}/api/analytics/advanced/fight-frequency?relationship_id=${relationshipId}&period=${period}&periods=${periods}`,
        { headers: defaultHeaders }
      );
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      setData(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [relationshipId]);

  return { data, loading, error, refresh: fetch_ };
};

// ============================================================================
// 4. Recovery Time
// ============================================================================
export const useRecoveryTime = (relationshipId: string) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch_ = useCallback(async () => {
    if (!relationshipId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(
        `${API_BASE}/api/analytics/advanced/recovery-time?relationship_id=${relationshipId}`,
        { headers: defaultHeaders }
      );
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      setData(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [relationshipId]);

  return { data, loading, error, refresh: fetch_ };
};

// ============================================================================
// 5. Attachment Styles
// ============================================================================
export const useAttachmentStyles = (relationshipId: string) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch_ = useCallback(async (refresh = false) => {
    if (!relationshipId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(
        `${API_BASE}/api/analytics/advanced/attachment-styles?relationship_id=${relationshipId}&refresh=${refresh}`,
        { headers: defaultHeaders }
      );
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      setData(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [relationshipId]);

  return { data, loading, error, refresh: fetch_ };
};

// ============================================================================
// 6. Bid Response Ratio
// ============================================================================
export const useBidResponseRatio = (relationshipId: string) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch_ = useCallback(async () => {
    if (!relationshipId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(
        `${API_BASE}/api/analytics/advanced/bid-response-ratio?relationship_id=${relationshipId}`,
        { headers: defaultHeaders }
      );
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      setData(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [relationshipId]);

  return { data, loading, error, refresh: fetch_ };
};

// ============================================================================
// 7. Repair Compliance (conflict-scoped)
// ============================================================================
export const useRepairCompliance = (conflictId: string) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch_ = useCallback(async () => {
    if (!conflictId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(
        `${API_BASE}/api/analytics/repair-compliance/${conflictId}`,
        { headers: defaultHeaders }
      );
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      setData(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [conflictId]);

  const updateStep = useCallback(async (stepId: string, completed: boolean, notes?: string) => {
    if (!conflictId) return;
    try {
      const params = new URLSearchParams({
        step_id: stepId,
        completed: String(completed),
      });
      if (notes) params.append('notes', notes);

      const res = await fetch(
        `${API_BASE}/api/analytics/repair-compliance/${conflictId}/update?${params}`,
        { method: 'POST', headers: defaultHeaders }
      );
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      const result = await res.json();
      // Refresh data after update
      await fetch_();
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [conflictId, fetch_]);

  return { data, loading, error, refresh: fetch_, updateStep };
};
