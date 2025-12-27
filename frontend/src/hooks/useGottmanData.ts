import { useState, useCallback } from 'react';

interface FourHorsemen {
  criticism: number;
  contempt: number;
  defensiveness: number;
  stonewalling: number;
  total: number;
  trend?: string;
}

interface RepairMetrics {
  success_rate: number;
  total_attempts: number;
  successful: number;
}

interface PartnerPatterns {
  partner_a_dominant_horseman: string | null;
  partner_b_dominant_horseman: string | null;
  partner_a_i_to_you_ratio: number;
  partner_b_i_to_you_ratio: number;
}

interface CommunicationStats {
  partner_a: {
    i_statements: number;
    you_statements: number;
  };
  partner_b: {
    i_statements: number;
    you_statements: number;
  };
  interruptions: number;
  active_listening: number;
}

interface GottmanData {
  has_data: boolean;
  gottman_health_score: number | null;
  four_horsemen: FourHorsemen;
  repair_metrics: RepairMetrics;
  partner_patterns: PartnerPatterns;
  communication_stats?: CommunicationStats;
  conflicts_analyzed: number;
  last_calculated_at?: string;
  message?: string;
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const useGottmanData = (relationshipId: string) => {
  const [gottmanData, setGottmanData] = useState<GottmanData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backfillStatus, setBackfillStatus] = useState<{
    running: boolean;
    results?: {
      total: number;
      analyzed: number;
      failed: number;
      skipped: number;
    };
  }>({ running: false });

  const fetchGottmanData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/api/analytics/gottman/relationship/${relationshipId}`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch Gottman data: ${response.statusText}`);
      }

      const data = await response.json();
      setGottmanData(data);
    } catch (err) {
      console.error('Error fetching Gottman data:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch Gottman data');
    } finally {
      setLoading(false);
    }
  }, [relationshipId]);

  const runBackfill = useCallback(async () => {
    setBackfillStatus({ running: true });
    try {
      const response = await fetch(
        `${API_BASE}/api/analytics/gottman/backfill?relationship_id=${relationshipId}`,
        { method: 'POST' }
      );

      if (!response.ok) {
        throw new Error(`Backfill failed: ${response.statusText}`);
      }

      const data = await response.json();
      setBackfillStatus({ running: false, results: data.results });

      // Refresh data after backfill
      await fetchGottmanData();
    } catch (err) {
      console.error('Error running backfill:', err);
      setBackfillStatus({ running: false });
      setError(err instanceof Error ? err.message : 'Backfill failed');
    }
  }, [relationshipId, fetchGottmanData]);

  return {
    gottmanData,
    loading,
    error,
    backfillStatus,
    fetchGottmanData,
    runBackfill,
  };
};
