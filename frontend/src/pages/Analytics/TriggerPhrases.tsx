import React, { useEffect } from 'react';
import { useAnalyticsData } from '../../hooks/useAnalytics';
import { TriggerPhraseTable } from '../../components/analytics';

const TriggerPhrases: React.FC = () => {
  const relationshipId = "00000000-0000-0000-0000-000000000000";
  const { triggerPhrases, loading, error, refresh } = useAnalyticsData(relationshipId);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (loading) return <div className="p-6">Loading...</div>;
  if (error) return <div className="p-6 text-red-600">Error: {error}</div>;

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-3xl font-bold">Trigger Phrase Analysis</h1>
      {triggerPhrases?.most_impactful && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4">Most Impactful Phrases</h2>
          <TriggerPhraseTable phrases={triggerPhrases.most_impactful} />
        </div>
      )}
    </div>
  );
};

export default TriggerPhrases;
