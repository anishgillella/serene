import { useState, useEffect, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface Digest {
  id: string;
  relationship_id: string;
  week_start: string;
  week_end: string;
  metrics: Record<string, any>;
  narrative: string | null;
  highlights: string[] | null;
  recommendations: string[] | null;
  is_read_partner_a: boolean;
  is_read_partner_b: boolean;
  created_at: string | null;
}

export function useDigests(relationshipId: string) {
  const [digests, setDigests] = useState<Digest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDigests = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/digests?relationship_id=${relationshipId}`,
        { headers: { 'ngrok-skip-browser-warning': 'true' } }
      );
      if (!res.ok) throw new Error('Failed to fetch digests');
      const data = await res.json();
      setDigests(data.digests || []);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [relationshipId]);

  useEffect(() => {
    fetchDigests();
  }, [fetchDigests]);

  return { digests, loading, error, refetch: fetchDigests };
}

export function useLatestDigest(relationshipId: string) {
  const [digest, setDigest] = useState<Digest | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetch_ = async () => {
      try {
        const res = await fetch(
          `${API_BASE}/api/digests/latest?relationship_id=${relationshipId}`,
          { headers: { 'ngrok-skip-browser-warning': 'true' } }
        );
        if (res.ok) {
          const data = await res.json();
          setDigest(data.has_digest ? data.digest : null);
        }
      } catch {
        // Silent fail for badge
      } finally {
        setLoading(false);
      }
    };
    fetch_();
  }, [relationshipId]);

  return { digest, loading };
}
