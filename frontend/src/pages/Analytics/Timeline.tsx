import React, { useEffect } from 'react';
import { useAnalyticsData } from '../../hooks/useAnalytics';

const Timeline: React.FC = () => {
  const relationshipId = "00000000-0000-0000-0000-000000000000";
  const { conflictChains, loading, error, refresh } = useAnalyticsData(relationshipId);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (loading) return <div className="p-6">Loading...</div>;
  if (error) return <div className="p-6 text-red-600">Error: {error}</div>;

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-3xl font-bold">Conflict Timeline</h1>
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Conflict Chains</h2>
        {conflictChains?.chains?.map((chain: any, idx: number) => (
          <div key={idx} className="mb-4 p-4 border-l-4 border-blue-500">
            <p className="font-bold">{chain.root_cause}</p>
            <p className="text-sm text-gray-600">{chain.timeline}</p>
            <p className="text-sm mt-2">Conflicts: {chain.conflicts_in_chain}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Timeline;
