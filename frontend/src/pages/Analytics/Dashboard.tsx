import React, { useEffect, useState } from 'react';
import { useDashboardData } from '../../hooks/useDashboardData';
import { HealthScore } from '../../components/dashboard/HealthScore';
import { RiskMetrics } from '../../components/dashboard/RiskMetrics';
import { MetricsOverview } from '../../components/dashboard/MetricsOverview';
import { ConflictTrends } from '../../components/dashboard/ConflictTrends';
import { TriggerPhraseHeatmap } from '../../components/dashboard/TriggerPhraseHeatmap';
import { UnmetNeedsAnalysis } from '../../components/dashboard/UnmetNeedsAnalysis';
import { RecommendationsPanel } from '../../components/dashboard/RecommendationsPanel';
import { InsightsPanel } from '../../components/dashboard/InsightsPanel';

const Dashboard: React.FC = () => {
  const relationshipId = "00000000-0000-0000-0000-000000000000";
  const { dashboardData, loading, error, refresh } = useDashboardData(relationshipId);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  useEffect(() => {
    refresh();
  }, []);

  const handleRefresh = async () => {
    await refresh();
    setLastRefresh(new Date());
  };

  if (loading && !dashboardData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-50 p-8 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-4 border-purple-200 border-t-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-600 font-medium">Loading relationship analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-50 p-8">
        <div className="max-w-6xl mx-auto bg-red-50 border border-red-200 rounded-lg p-8">
          <h2 className="text-2xl font-bold text-red-800 mb-2">Error Loading Dashboard</h2>
          <p className="text-red-600 mb-4">{error}</p>
          <button
            onClick={handleRefresh}
            className="bg-red-600 text-white px-6 py-2 rounded-lg hover:bg-red-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-50 p-8">
        <div className="max-w-6xl mx-auto bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
          <p className="text-gray-600">No data available. Please record conflicts to see analytics.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-50 p-4 md:p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
              Relationship Dashboard
            </h1>
            <p className="text-gray-600 mt-2">Real-time insights into your relationship patterns</p>
          </div>
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="bg-white border border-purple-200 text-purple-600 px-6 py-2 rounded-lg hover:bg-purple-50 transition-colors disabled:opacity-50"
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>

        {lastRefresh && (
          <p className="text-sm text-gray-500 text-center">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </p>
        )}

        {/* Top Row: Health Score & Risk Metrics */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <HealthScore data={dashboardData.health_score} />
          <RiskMetrics data={dashboardData.escalation_risk} />
          <MetricsOverview data={dashboardData.metrics} />
        </div>

        {/* Middle Row: Trends & Analysis */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ConflictTrends data={dashboardData} />
          <TriggerPhraseHeatmap data={dashboardData.trigger_phrases} />
        </div>

        {/* Bottom Row: Needs & Recommendations */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <UnmetNeedsAnalysis data={dashboardData.chronic_needs} />
          <RecommendationsPanel data={dashboardData.escalation_risk} />
        </div>

        {/* Insights Panel */}
        <InsightsPanel
          insights={dashboardData.insights}
          metrics={dashboardData.metrics}
          escalationRisk={dashboardData.escalation_risk}
        />
      </div>
    </div>
  );
};

export default Dashboard;
