import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

interface AnalyticsContextType {
  escalationRisk: any;
  triggerPhrases: any;
  conflictChains: any;
  unmetNeeds: any;
  healthScore: any;
  loading: boolean;
  error: string | null;
  refreshAnalytics: (relationshipId: string) => Promise<void>;
}

const AnalyticsContext = createContext<AnalyticsContextType | undefined>(undefined);

export const AnalyticsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [escalationRisk, setEscalationRisk] = useState(null);
  const [triggerPhrases, setTriggerPhrases] = useState(null);
  const [conflictChains, setConflictChains] = useState(null);
  const [unmetNeeds, setUnmetNeeds] = useState(null);
  const [healthScore, setHealthScore] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshAnalytics = useCallback(async (relationshipId: string) => {
    setLoading(true);
    setError(null);
    try {
      const [riskRes, phrasesRes, chainsRes, needsRes, healthRes] = await Promise.all([
        fetch(`/api/analytics/escalation-risk?relationship_id=${relationshipId}`),
        fetch(`/api/analytics/trigger-phrases?relationship_id=${relationshipId}`),
        fetch(`/api/analytics/conflict-chains?relationship_id=${relationshipId}`),
        fetch(`/api/analytics/unmet-needs?relationship_id=${relationshipId}`),
        fetch(`/api/analytics/health-score?relationship_id=${relationshipId}`),
      ]);

      if (!riskRes.ok || !phrasesRes.ok || !chainsRes.ok || !needsRes.ok || !healthRes.ok) {
        throw new Error('Failed to fetch analytics data');
      }

      const [riskData, phrasesData, chainsData, needsData, healthData] = await Promise.all([
        riskRes.json(),
        phrasesRes.json(),
        chainsRes.json(),
        needsRes.json(),
        healthRes.json(),
      ]);

      setEscalationRisk(riskData);
      setTriggerPhrases(phrasesData);
      setConflictChains(chainsData);
      setUnmetNeeds(needsData);
      setHealthScore(healthData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  const value: AnalyticsContextType = {
    escalationRisk,
    triggerPhrases,
    conflictChains,
    unmetNeeds,
    healthScore,
    loading,
    error,
    refreshAnalytics,
  };

  return <AnalyticsContext.Provider value={value}>{children}</AnalyticsContext.Provider>;
};

export const useAnalytics = () => {
  const context = useContext(AnalyticsContext);
  if (!context) {
    throw new Error('useAnalytics must be used within AnalyticsProvider');
  }
  return context;
};
