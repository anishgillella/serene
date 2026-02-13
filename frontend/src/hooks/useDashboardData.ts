import { useState, useCallback } from 'react';

interface DashboardData {
  health_score: number;
  health_score_previous?: number | null;
  escalation_risk: {
    risk_score: number;
    interpretation: string;
    unresolved_issues: number;
    days_until_predicted_conflict: number;
    recommendations: string[];
    factors?: {
      unresolved_issues?: number;
      resentment_accumulation?: number;
      time_since_conflict?: number;
      recurrence_pattern?: number;
      avg_resentment?: number;
      days_since_last?: number;
    };
  };
  trigger_phrases: {
    most_impactful: Array<{
      phrase: string;
      usage_count: number;
      escalation_rate: number;
    }>;
  };
  conflict_chains: Array<any>;
  chronic_needs: Array<{
    need: string;
    conflict_count: number;
    percentage_of_conflicts: number;
  }>;
  metrics: {
    total_conflicts: number;
    resolved_conflicts: number;
    unresolved_conflicts: number;
    resolution_rate: number;
    avg_resentment: number;
    days_since_last_conflict: number;
  };
  insights: string[];
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const useDashboardData = (relationshipId: string) => {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!relationshipId) {
      setDashboardData(null);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `${API_BASE}/api/analytics/dashboard?relationship_id=${relationshipId}`,
        {
          headers: { 'ngrok-skip-browser-warning': 'true' }
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch dashboard data: ${response.status}`);
      }

      const data = await response.json();
      setDashboardData(data);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMsg);
      console.error('Error fetching dashboard data:', err);
    } finally {
      setLoading(false);
    }
  }, [relationshipId]);

  return {
    dashboardData,
    loading,
    error,
    refresh,
  };
};
