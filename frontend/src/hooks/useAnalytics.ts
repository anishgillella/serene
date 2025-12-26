import { useCallback } from 'react';
import { useAnalytics } from '../contexts/AnalyticsContext';

export const useAnalyticsData = (relationshipId: string) => {
  const { escalationRisk, triggerPhrases, conflictChains, unmetNeeds, healthScore, loading, error, refreshAnalytics } = useAnalytics();

  const refresh = useCallback(async () => {
    await refreshAnalytics(relationshipId);
  }, [relationshipId, refreshAnalytics]);

  return {
    escalationRisk,
    triggerPhrases,
    conflictChains,
    unmetNeeds,
    healthScore,
    loading,
    error,
    refresh,
  };
};
