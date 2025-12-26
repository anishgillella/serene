import { useState, useCallback } from 'react';

interface DashboardData {
  health_score: {
    value: number;
    trend: 'up' | 'down' | 'stable';
    breakdownFactors: {
      unresolved_issues: number;
      conflict_frequency: number;
      escalation_risk: number;
      resentment_level: number;
    };
  };
  escalation_risk: {
    risk_score: number;
    interpretation: string;
    unresolved_issues: number;
    days_until_predicted_conflict: number;
    recommendations: string[];
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

  const getHealthStatus = useCallback(() => {
    if (!dashboardData) return 'unknown';
    const score = dashboardData.health_score.value;
    if (score >= 80) return 'excellent';
    if (score >= 60) return 'good';
    if (score >= 40) return 'fair';
    return 'poor';
  }, [dashboardData]);

  const getRiskLevel = useCallback(() => {
    return dashboardData?.escalation_risk.interpretation ?? 'unknown';
  }, [dashboardData]);

  const getResolutionTrend = useCallback(() => {
    if (!dashboardData) return 'stable';
    return dashboardData.health_score.trend;
  }, [dashboardData]);

  return {
    dashboardData,
    loading,
    error,
    refresh,
    getHealthStatus,
    getRiskLevel,
    getResolutionTrend
  };
};
