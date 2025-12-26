import React, { useEffect } from 'react';
import { useAnalyticsData } from '../../hooks/useAnalytics';
import { EscalationRiskCard, UnresolvedIssuesList, ChronicNeedsList } from '../../components/analytics';

const ConflictAnalysis: React.FC = () => {
  const relationshipId = "00000000-0000-0000-0000-000000000000";
  const { escalationRisk, unmetNeeds, loading, error, refresh } = useAnalyticsData(relationshipId);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (loading) return <div className="p-6">Loading analysis...</div>;
  if (error) return <div className="p-6 text-red-600">Error: {error}</div>;

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-3xl font-bold">Relationship Health & Patterns</h1>
      {escalationRisk && <EscalationRiskCard data={escalationRisk} />}
      <UnresolvedIssuesList issues={escalationRisk?.unresolved_issues} />
      <ChronicNeedsList needs={unmetNeeds} />
      <div className="bg-blue-50 p-6 rounded-lg">
        <h2 className="font-bold mb-4">Recommended Actions</h2>
        <ul className="space-y-2">
          {escalationRisk?.recommendations?.map((rec: string, idx: number) => (
            <li key={idx} className="flex items-start">
              <span className="mr-3">→</span>
              <span>{rec}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default ConflictAnalysis;
