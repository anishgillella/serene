import { useState, useCallback, useEffect } from 'react';

interface ConflictContextData {
  current_conflict?: {
    topic: string;
    resentment_level: number;
    unmet_needs: string[];
  };
  unresolved_issues?: Array<{
    conflict_id: string;
    topic: string;
    days_unresolved: number;
    resentment_level: number;
    unmet_needs: string[];
  }>;
  chronic_needs?: string[];
  high_impact_triggers?: Array<{
    phrase: string;
    category: string;
    escalation_rate: number;
  }>;
  escalation_risk?: {
    score: number;
    interpretation: string;
    is_critical: boolean;
  };
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const useConflictContext = (conflictId: string) => {
  const [context, setContext] = useState<ConflictContextData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchContext = useCallback(async () => {
    if (!conflictId) {
      setContext(null);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `${API_BASE}/api/mediator/context/${conflictId}`,
        {
          headers: { 'ngrok-skip-browser-warning': 'true' }
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch context: ${response.status}`);
      }

      const data = await response.json();
      setContext(data);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMsg);
      console.error('Error fetching conflict context:', err);
    } finally {
      setLoading(false);
    }
  }, [conflictId]);

  useEffect(() => {
    fetchContext();
  }, [fetchContext]);

  const isCritical = useCallback(() => {
    return context?.escalation_risk?.is_critical ?? false;
  }, [context]);

  const getChronicNeeds = useCallback(() => {
    return context?.chronic_needs ?? [];
  }, [context]);

  const getUnresolvedCount = useCallback(() => {
    return context?.unresolved_issues?.length ?? 0;
  }, [context]);

  const getTriggers = useCallback(() => {
    return context?.high_impact_triggers ?? [];
  }, [context]);

  const getEscalationRisk = useCallback(() => {
    return context?.escalation_risk?.score ?? 0;
  }, [context]);

  const getRiskInterpretation = useCallback(() => {
    return context?.escalation_risk?.interpretation ?? 'unknown';
  }, [context]);

  return {
    context,
    loading,
    error,
    refresh: fetchContext,
    isCritical,
    getChronicNeeds,
    getUnresolvedCount,
    getTriggers,
    getEscalationRisk,
    getRiskInterpretation
  };
};
