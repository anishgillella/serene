import { useState, useCallback } from 'react';

interface MediationResponse {
  suggestions: Array<{
    type: string;
    message: string;
  }>;
  risk_warnings: Array<{
    type: string;
    message: string;
    severity: 'low' | 'medium' | 'high';
  }>;
  context_applied: string[];
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const useLunaMediator = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastEnhancement, setLastEnhancement] = useState<MediationResponse | null>(null);

  const enhanceResponse = useCallback(
    async (
      conflictId: string,
      response: string,
      userMessage?: string
    ): Promise<MediationResponse | null> => {
      try {
        setLoading(true);
        setError(null);

        const result = await fetch(`${API_BASE}/api/mediator/enhance-response`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'ngrok-skip-browser-warning': 'true'
          },
          body: JSON.stringify({
            conflict_id: conflictId,
            response,
            user_message: userMessage
          })
        });

        if (!result.ok) {
          throw new Error(`Failed to enhance response: ${result.status}`);
        }

        const enhancement = await result.json();
        setLastEnhancement(enhancement);
        return enhancement;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Unknown error';
        setError(errorMsg);
        console.error('Error enhancing Luna response:', err);
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const hasRiskWarnings = useCallback(() => {
    return lastEnhancement ? lastEnhancement.risk_warnings.length > 0 : false;
  }, [lastEnhancement]);

  const hasSuggestions = useCallback(() => {
    return lastEnhancement ? lastEnhancement.suggestions.length > 0 : false;
  }, [lastEnhancement]);

  const getCriticalWarnings = useCallback(() => {
    return lastEnhancement
      ? lastEnhancement.risk_warnings.filter(w => w.severity === 'high')
      : [];
  }, [lastEnhancement]);

  return {
    enhanceResponse,
    loading,
    error,
    lastEnhancement,
    hasRiskWarnings,
    hasSuggestions,
    getCriticalWarnings
  };
};
