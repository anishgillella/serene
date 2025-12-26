import React, { useEffect, useState } from 'react';
import { AlertTriangle, TrendingUp, AlertCircle } from 'lucide-react';

interface MediationContext {
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

interface Props {
  conflictId: string;
  isExpanded?: boolean;
  onClose?: () => void;
}

export const MediatorContextPanel: React.FC<Props> = ({ conflictId, isExpanded = false, onClose }) => {
  const [context, setContext] = useState<MediationContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(isExpanded);

  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    const fetchContext = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${API_BASE}/api/mediator/context/${conflictId}`, {
          headers: { 'ngrok-skip-browser-warning': 'true' }
        });

        if (!response.ok) throw new Error('Failed to fetch context');

        const data = await response.json();
        setContext(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        console.error('Error fetching mediation context:', err);
      } finally {
        setLoading(false);
      }
    };

    if (conflictId) {
      fetchContext();
    }
  }, [conflictId, API_BASE]);

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 bg-purple-600 text-white p-3 rounded-full shadow-lg hover:bg-purple-700 transition-colors"
        title="Show relationship context"
      >
        <AlertCircle size={24} />
      </button>
    );
  }

  const getRiskColor = (score: number) => {
    if (score < 0.25) return 'text-green-600 bg-green-50';
    if (score < 0.50) return 'text-yellow-600 bg-yellow-50';
    if (score < 0.75) return 'text-orange-600 bg-orange-50';
    return 'text-red-600 bg-red-50';
  };

  return (
    <div className="fixed bottom-4 right-4 w-80 max-h-96 bg-white rounded-lg shadow-xl border border-gray-200 overflow-hidden flex flex-col">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-pink-600 text-white p-4 flex items-center justify-between">
        <h3 className="font-bold text-sm">Luna's Context</h3>
        <button
          onClick={() => {
            setIsOpen(false);
            onClose?.();
          }}
          className="text-white hover:bg-white/20 p-1 rounded transition-colors"
        >
          ✕
        </button>
      </div>

      {/* Content */}
      <div className="overflow-y-auto flex-1 p-4 space-y-4">
        {loading && <div className="text-center text-gray-500">Loading context...</div>}

        {error && <div className="text-sm text-red-600 bg-red-50 p-2 rounded">{error}</div>}

        {context && !loading && (
          <>
            {/* Escalation Risk */}
            {context.escalation_risk && (
              <div className={`p-3 rounded-lg ${getRiskColor(context.escalation_risk.score)}`}>
                <div className="flex items-center gap-2 mb-1">
                  {context.escalation_risk.is_critical && <AlertTriangle size={18} />}
                  <span className="font-bold text-sm">
                    {context.escalation_risk.interpretation.toUpperCase()} RISK
                  </span>
                </div>
                <div className="text-lg font-bold">
                  {(context.escalation_risk.score * 100).toFixed(0)}%
                </div>
                {context.escalation_risk.is_critical && (
                  <p className="text-xs mt-2 font-semibold">
                    ⚠️ Suggest a break or professional help
                  </p>
                )}
              </div>
            )}

            {/* Current Conflict */}
            {context.current_conflict && (
              <div className="bg-blue-50 p-3 rounded-lg border-l-4 border-blue-500">
                <p className="text-xs text-gray-600 uppercase tracking-wide">Current Topic</p>
                <p className="font-bold text-sm text-gray-800">{context.current_conflict.topic}</p>
                <p className="text-xs text-gray-600 mt-1">
                  Resentment: {context.current_conflict.resentment_level}/10
                </p>
              </div>
            )}

            {/* Chronic Needs */}
            {context.chronic_needs && context.chronic_needs.length > 0 && (
              <div className="bg-purple-50 p-3 rounded-lg border-l-4 border-purple-500">
                <p className="text-xs text-gray-600 uppercase tracking-wide font-semibold mb-2">
                  Chronic Unmet Needs
                </p>
                <div className="space-y-1">
                  {context.chronic_needs.map((need, idx) => (
                    <p key={idx} className="text-sm text-gray-700">
                      • {need.replace(/_/g, ' ')}
                    </p>
                  ))}
                </div>
              </div>
            )}

            {/* High Impact Triggers */}
            {context.high_impact_triggers && context.high_impact_triggers.length > 0 && (
              <div className="bg-orange-50 p-3 rounded-lg border-l-4 border-orange-500">
                <p className="text-xs text-gray-600 uppercase tracking-wide font-semibold mb-2">
                  Escalation Triggers
                </p>
                <div className="space-y-1">
                  {context.high_impact_triggers.slice(0, 3).map((trigger, idx) => (
                    <p key={idx} className="text-xs text-gray-700">
                      "{trigger.phrase}" ({(trigger.escalation_rate * 100).toFixed(0)}%)
                    </p>
                  ))}
                </div>
              </div>
            )}

            {/* Unresolved Issues */}
            {context.unresolved_issues && context.unresolved_issues.length > 0 && (
              <div className="bg-yellow-50 p-3 rounded-lg border-l-4 border-yellow-500">
                <p className="text-xs text-gray-600 uppercase tracking-wide font-semibold mb-2">
                  {context.unresolved_issues.length} Unresolved Issues
                </p>
                <div className="space-y-1">
                  {context.unresolved_issues.slice(0, 2).map((issue, idx) => (
                    <p key={idx} className="text-xs text-gray-700">
                      • {issue.topic} ({issue.days_unresolved}d unresolved)
                    </p>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Footer */}
      <div className="bg-gray-50 p-3 border-t text-xs text-gray-600 text-center">
        Luna uses this context to give better advice
      </div>
    </div>
  );
};
