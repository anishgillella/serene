import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity,
  BarChart3,
  Heart,
  RefreshCw,
  Sparkles,
  Shield,
  Target,
  Zap,
  TrendingUp,
} from 'lucide-react';
import { useRelationshipId, usePartnerNames } from '../contexts/RelationshipContext';
import { usePartnerContext } from '../contexts/PartnerContext';
import { useDashboardData } from '../hooks/useDashboardData';
import { useGottmanData } from '../hooks/useGottmanData';
import { useNarrativeInsights } from '../hooks/useNarrativeInsights';
import {
  useSentimentShift,
  useCommunicationGrowth,
  useFightFrequency,
  useRecoveryTime,
  useAttachmentStyles,
  useBidResponseRatio,
} from '../hooks/useNewMetrics';

// Premium components
import {
  AnimatedBackground,
  GlassCard,
  GlassCardFeatured,
  AnimatedHealthRing,
  PremiumTabsFullWidth,
  MetricCard,
  RiskGauge,
  RecommendationsList,
  TriggerPhrasesCard,
  ChronicNeedsCard,
  GottmanRadar,
  RepairSuccessCard,
  CommunicationQuality,
  MessagingInsights,
  SentimentShiftCard,
  CommunicationGrowthCard,
  FightFrequencyChart,
  RecoveryTimeCard,
  AttachmentStyleCard,
  BidResponseCard,
  NarrativeInsightCard,
  SkeletonCard,
} from '../components/premium';

type TabId = 'doing' | 'fight' | 'triggers' | 'growing';

const tabs = [
  { id: 'doing', label: 'How We\'re Doing', icon: <Heart size={18} /> },
  { id: 'fight', label: 'How We Fight', icon: <Shield size={18} /> },
  { id: 'triggers', label: 'What Triggers Us', icon: <Target size={18} /> },
  { id: 'growing', label: 'Are We Growing', icon: <TrendingUp size={18} /> },
];

const Analytics: React.FC = () => {
  const relationshipId = useRelationshipId();
  const { partnerA, partnerB } = usePartnerNames();
  const { partnerRole } = usePartnerContext();

  const { dashboardData, loading, error, refresh } = useDashboardData(relationshipId);
  const {
    gottmanData,
    loading: gottmanLoading,
    fetchGottmanData,
    runBackfill,
    backfillStatus
  } = useGottmanData(relationshipId);
  const { data: narrativeData, loading: narrativeLoading, refresh: refreshNarrative } = useNarrativeInsights(relationshipId, partnerRole);
  const { data: sentimentData, loading: sentimentLoading, error: sentimentError, refresh: refreshSentiment } = useSentimentShift(relationshipId);
  const { data: commGrowthData, loading: commGrowthLoading, error: commGrowthError, refresh: refreshCommGrowth } = useCommunicationGrowth(relationshipId);
  const { data: fightFreqData, loading: fightFreqLoading, error: fightFreqError, refresh: refreshFightFreq } = useFightFrequency(relationshipId);
  const { data: recoveryData, loading: recoveryLoading, error: recoveryError, refresh: refreshRecovery } = useRecoveryTime(relationshipId);
  const { data: attachmentData, loading: attachmentLoading, error: attachmentError, refresh: refreshAttachment } = useAttachmentStyles(relationshipId);
  const { data: bidResponseData, loading: bidResponseLoading, error: bidResponseError, refresh: refreshBidResponse } = useBidResponseRatio(relationshipId);

  const [activeTab, setActiveTab] = useState<TabId>('doing');
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  // Collect all fetched metrics into a bundle for the narrative endpoint
  const buildMetricsPayload = () => ({
    dashboard: dashboardData || {},
    gottman: gottmanData || {},
    sentiment: sentimentData || {},
    growth: commGrowthData || {},
    frequency: fightFreqData || {},
    recovery: recoveryData || {},
    attachment: attachmentData || {},
    bid_response: bidResponseData || {},
  });

  // Initial load: fetch all metrics (narrative waits for data)
  useEffect(() => {
    refresh();
    fetchGottmanData();
    refreshSentiment();
    refreshCommGrowth();
    refreshFightFreq();
    refreshRecovery();
    refreshAttachment();
    refreshBidResponse();
  }, []);

  // Once primary data is loaded, fire narrative with the metrics payload
  useEffect(() => {
    if (dashboardData && !narrativeData && !narrativeLoading) {
      refreshNarrative(buildMetricsPayload());
    }
  }, [dashboardData, gottmanData, sentimentData, commGrowthData, fightFreqData, recoveryData, attachmentData, bidResponseData]);

  const handleRefresh = async () => {
    await Promise.all([
      refresh(),
      fetchGottmanData(),
      refreshSentiment(),
      refreshCommGrowth(),
      refreshFightFreq(),
      refreshRecovery(),
      refreshAttachment(),
      refreshBidResponse(),
    ]);
    setLastRefresh(new Date());
    // Narrative uses fresh data — small delay to let state settle
    setTimeout(() => refreshNarrative(buildMetricsPayload()), 100);
  };

  // Calculate health score and trend
  const getHealthData = () => {
    if (!dashboardData) return { value: 0, trend: 'stable' as const, delta: null as number | null };
    const value = typeof dashboardData.health_score === 'number'
      ? dashboardData.health_score
      : 50;
    const resolutionRate = dashboardData.metrics?.resolution_rate ?? 50;
    const trend = resolutionRate > 50 ? 'up' as const :
                  resolutionRate < 30 ? 'down' as const : 'stable' as const;
    const prev = dashboardData.health_score_previous;
    const delta = typeof prev === 'number' ? value - prev : null;
    return { value, trend, delta };
  };

  // Compute fight frequency delta from periods
  const getFightFreqDelta = (): string | null => {
    if (!fightFreqData?.has_data || !fightFreqData.periods || fightFreqData.periods.length < 2) return null;
    const periods = fightFreqData.periods;
    const latest = periods[periods.length - 1].fight_count;
    const prev = periods[periods.length - 2].fight_count;
    const diff = latest - prev;
    if (diff === 0) return null;
    return diff > 0 ? `+${diff} vs last period` : `${diff} vs last period`;
  };

  // Loading state
  if (loading && !dashboardData) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground />
        <div className="relative z-10 flex items-center justify-center min-h-screen">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center"
          >
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
              className="w-16 h-16 mx-auto mb-6"
            >
              <Heart className="w-full h-full text-rose-400" strokeWidth={1.5} />
            </motion.div>
            <p className="text-warmGray-600 font-medium">Loading your relationship insights...</p>
          </motion.div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground />
        <div className="relative z-10 flex items-center justify-center min-h-screen p-8">
          <GlassCard className="max-w-md w-full p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-rose-100 flex items-center justify-center">
              <Activity className="text-rose-500" size={32} />
            </div>
            <h2 className="text-xl font-semibold text-warmGray-800 mb-2">Unable to Load Data</h2>
            <p className="text-warmGray-500 mb-6">{error}</p>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleRefresh}
              className="px-6 py-2.5 bg-rose-500 text-white rounded-xl font-medium hover:bg-rose-600 transition-colors"
            >
              Try Again
            </motion.button>
          </GlassCard>
        </div>
      </div>
    );
  }

  // No data state
  if (!dashboardData) {
    return (
      <div className="min-h-screen relative">
        <AnimatedBackground />
        <div className="relative z-10 flex items-center justify-center min-h-screen p-8">
          <GlassCard className="max-w-md w-full p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-lavender-100 flex items-center justify-center">
              <Sparkles className="text-purple-500" size={32} />
            </div>
            <h2 className="text-xl font-semibold text-warmGray-800 mb-2">No Data Yet</h2>
            <p className="text-warmGray-500">Start recording conversations to see your relationship analytics.</p>
          </GlassCard>
        </div>
      </div>
    );
  }

  const healthData = getHealthData();
  const fightFreqDelta = getFightFreqDelta();

  return (
    <div className="min-h-screen relative">
      {/* Animated background */}
      <AnimatedBackground />

      {/* Content */}
      <div className="relative z-10 px-4 py-8 md:px-8 lg:px-12">
        <div className="max-w-7xl mx-auto">

          {/* Header */}
          <motion.header
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-8"
          >
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <motion.h1
                  className="text-display-sm md:text-display text-warmGray-900 mb-2"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.5, delay: 0.1 }}
                >
                  Relationship Insights
                </motion.h1>
                <motion.p
                  className="text-warmGray-500"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.5, delay: 0.2 }}
                >
                  Understanding your patterns, nurturing your connection
                </motion.p>
              </div>

              <motion.button
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleRefresh}
                disabled={loading}
                className="flex items-center gap-2 px-5 py-2.5 bg-white/70 backdrop-blur-lg border border-white/50 rounded-xl font-medium text-warmGray-700 hover:bg-white/90 transition-all shadow-subtle disabled:opacity-50"
              >
                <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
                {loading ? 'Refreshing...' : 'Refresh'}
              </motion.button>
            </div>

            {lastRefresh && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-xs text-warmGray-400 mt-2"
              >
                Last updated: {lastRefresh.toLocaleTimeString()}
              </motion.p>
            )}
          </motion.header>

          {/* Tab Navigation */}
          <div className="mb-8">
            <PremiumTabsFullWidth
              tabs={tabs}
              activeTab={activeTab}
              onTabChange={(id) => setActiveTab(id as TabId)}
            />
          </div>

          {/* Tab Content */}
          <AnimatePresence mode="wait">

            {/* ============================================================ */}
            {/* HOW WE'RE DOING — slim overview                              */}
            {/* ============================================================ */}
            {activeTab === 'doing' && (
              <motion.div
                key="doing"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className="space-y-6"
              >
                {/* Narrative Digest */}
                <NarrativeInsightCard
                  title="Weekly Digest"
                  insight={narrativeData?.overview_digest ?? null}
                  loading={narrativeLoading}
                  delay={0}
                />

                {/* Health Score + Risk */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <GlassCardFeatured className="p-8" delay={0.1}>
                    <div className="flex flex-col items-center">
                      <h3 className="text-lg font-semibold text-warmGray-700 mb-6">
                        Relationship Health
                      </h3>
                      <AnimatedHealthRing
                        value={healthData.value}
                        trend={healthData.trend}
                        size={220}
                      />
                      {healthData.delta !== null && (
                        <p className={`text-sm mt-4 font-medium ${healthData.delta >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                          {healthData.delta >= 0 ? '+' : ''}{healthData.delta} vs last week
                        </p>
                      )}
                      <p className="text-sm text-warmGray-500 mt-3 text-center max-w-[250px]">
                        Based on conflict resolution, communication patterns, and emotional balance
                      </p>
                    </div>
                  </GlassCardFeatured>

                  <RiskGauge
                    riskScore={dashboardData.escalation_risk?.risk_score ?? 0}
                    interpretation={dashboardData.escalation_risk?.interpretation ?? 'unknown'}
                    daysUntilPredicted={dashboardData.escalation_risk?.days_until_predicted_conflict ?? 0}
                    unresolvedIssues={dashboardData.escalation_risk?.unresolved_issues ?? 0}
                    delay={0.2}
                  />
                </div>

                {/* Cross-metric correlations */}
                {narrativeData?.cross_metric_correlations && narrativeData.cross_metric_correlations.length > 0 && (
                  <GlassCard className="p-6" delay={0.3}>
                    <div className="flex items-center gap-3 mb-4">
                      <div className="p-2 rounded-xl bg-purple-50">
                        <Sparkles size={18} className="text-purple-500" />
                      </div>
                      <h3 className="text-lg font-semibold text-warmGray-800">Connections</h3>
                    </div>
                    <div className="space-y-3">
                      {narrativeData.cross_metric_correlations.map((corr: string, idx: number) => (
                        <motion.div
                          key={idx}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.4 + idx * 0.1 }}
                          className="flex items-start gap-3 p-3 rounded-xl bg-warmGray-50/50"
                        >
                          <div className="w-1.5 h-1.5 rounded-full bg-purple-400 mt-2 flex-shrink-0" />
                          <p className="text-sm text-warmGray-600">{corr}</p>
                        </motion.div>
                      ))}
                    </div>
                  </GlassCard>
                )}
              </motion.div>
            )}

            {/* ============================================================ */}
            {/* HOW WE FIGHT — conflict quality                              */}
            {/* ============================================================ */}
            {activeTab === 'fight' && (
              <motion.div
                key="fight"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className="space-y-6"
              >
                {/* Narrative */}
                <NarrativeInsightCard
                  title="Fight Quality"
                  insight={narrativeData?.fight_quality_insight ?? null}
                  loading={narrativeLoading}
                  delay={0}
                />

                {/* Backfill Banner - show if no data */}
                {gottmanData && !gottmanData.has_data && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-gradient-to-r from-purple-50 to-rose-50 rounded-2xl p-6 border border-purple-100"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-lg font-semibold text-warmGray-800 mb-1">
                          Analyze Your Communication
                        </h3>
                        <p className="text-sm text-warmGray-600">
                          Run Gottman analysis on your {dashboardData?.metrics?.total_conflicts || 0} conflicts to get Four Horsemen insights
                        </p>
                      </div>
                      <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={runBackfill}
                        disabled={backfillStatus.running}
                        className="px-5 py-2.5 bg-purple-600 text-white rounded-xl font-medium hover:bg-purple-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                      >
                        {backfillStatus.running ? (
                          <>
                            <RefreshCw size={16} className="animate-spin" />
                            Analyzing...
                          </>
                        ) : (
                          <>
                            <Zap size={16} />
                            Run Analysis
                          </>
                        )}
                      </motion.button>
                    </div>
                    {backfillStatus.results && (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="mt-4 p-3 bg-white/50 rounded-xl text-sm text-warmGray-600"
                      >
                        Analyzed {backfillStatus.results.analyzed} of {backfillStatus.results.total} conflicts
                        {backfillStatus.results.failed > 0 && ` (${backfillStatus.results.failed} failed)`}
                      </motion.div>
                    )}
                  </motion.div>
                )}

                {/* Gottman Radar + Repair Success */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {gottmanLoading ? (
                    <SkeletonCard lines={5} />
                  ) : (
                    <GottmanRadar
                      criticism={gottmanData?.four_horsemen?.criticism ?? 0}
                      contempt={gottmanData?.four_horsemen?.contempt ?? 0}
                      defensiveness={gottmanData?.four_horsemen?.defensiveness ?? 0}
                      stonewalling={gottmanData?.four_horsemen?.stonewalling ?? 0}
                      delay={0.1}
                    />
                  )}

                  <RepairSuccessCard
                    successRate={gottmanData?.repair_metrics?.success_rate ?? 0}
                    totalAttempts={gottmanData?.repair_metrics?.total_attempts ?? 0}
                    successfulRepairs={gottmanData?.repair_metrics?.successful ?? 0}
                    delay={0.2}
                  />
                </div>

                {/* Communication Quality */}
                <CommunicationQuality
                  partnerA={{
                    iStatements: gottmanData?.communication_stats?.partner_a?.i_statements ?? 0,
                    youStatements: gottmanData?.communication_stats?.partner_a?.you_statements ?? 0,
                    name: partnerA
                  }}
                  partnerB={{
                    iStatements: gottmanData?.communication_stats?.partner_b?.i_statements ?? 0,
                    youStatements: gottmanData?.communication_stats?.partner_b?.you_statements ?? 0,
                    name: partnerB
                  }}
                  interruptions={gottmanData?.communication_stats?.interruptions ?? 0}
                  activeListening={gottmanData?.communication_stats?.active_listening ?? 0}
                  delay={0.3}
                />

                {/* Bid-Response + Sentiment Shift */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {bidResponseLoading ? (
                    <SkeletonCard lines={4} />
                  ) : bidResponseError ? (
                    <GlassCard className="p-6">
                      <p className="text-sm text-warmGray-500">Failed to load bid-response data.</p>
                      <button onClick={() => refreshBidResponse()} className="text-sm text-purple-600 mt-2 hover:underline">Retry</button>
                    </GlassCard>
                  ) : (
                    <BidResponseCard
                      data={bidResponseData}
                      partnerAName={partnerA}
                      partnerBName={partnerB}
                      delay={0.4}
                    />
                  )}

                  {sentimentLoading ? (
                    <SkeletonCard lines={4} />
                  ) : sentimentError ? (
                    <GlassCard className="p-6">
                      <p className="text-sm text-warmGray-500">Failed to load sentiment data.</p>
                      <button onClick={() => refreshSentiment()} className="text-sm text-purple-600 mt-2 hover:underline">Retry</button>
                    </GlassCard>
                  ) : (
                    <SentimentShiftCard data={sentimentData} delay={0.5} />
                  )}
                </div>

                {/* Metric Cards Row */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <MetricCard
                    label="Total Conflicts"
                    value={dashboardData.metrics?.total_conflicts ?? 0}
                    icon={<Activity size={18} />}
                    color="rose"
                    delay={0.5}
                    trendValue={fightFreqDelta ?? undefined}
                  />
                  <MetricCard
                    label="Resolved"
                    value={dashboardData.metrics?.resolved_conflicts ?? 0}
                    icon={<Heart size={18} />}
                    color="emerald"
                    delay={0.55}
                  />
                  <MetricCard
                    label="Unresolved"
                    value={dashboardData.metrics?.unresolved_conflicts ?? 0}
                    icon={<Target size={18} />}
                    color="amber"
                    delay={0.6}
                  />
                  <MetricCard
                    label="Resolution Rate"
                    value={Math.round(dashboardData.metrics?.resolution_rate ?? 0)}
                    suffix="%"
                    trend={dashboardData.metrics?.resolution_rate > 50 ? 'up' : 'down'}
                    icon={<BarChart3 size={18} />}
                    color="emerald"
                    delay={0.65}
                  />
                </div>

                {/* Gottman Health Score Bar */}
                {gottmanData?.has_data && (
                  <GlassCard className="p-6" delay={0.7}>
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-lg font-semibold text-warmGray-800">Gottman Health Score</h3>
                        <p className="text-sm text-warmGray-500 mt-1">
                          Based on {gottmanData.conflicts_analyzed} analyzed conflicts
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-4xl font-bold text-warmGray-800">
                          {Math.round(gottmanData.gottman_health_score || 0)}
                        </p>
                        <p className="text-sm text-warmGray-500">/ 100</p>
                      </div>
                    </div>
                    <div className="mt-4 h-3 bg-warmGray-100 rounded-full overflow-hidden">
                      <motion.div
                        className={`h-full rounded-full ${
                          (gottmanData.gottman_health_score || 0) >= 70 ? 'bg-emerald-500' :
                          (gottmanData.gottman_health_score || 0) >= 50 ? 'bg-amber-500' :
                          (gottmanData.gottman_health_score || 0) >= 30 ? 'bg-orange-500' : 'bg-red-500'
                        }`}
                        initial={{ width: 0 }}
                        animate={{ width: `${gottmanData.gottman_health_score || 0}%` }}
                        transition={{ duration: 1, ease: "easeOut" }}
                      />
                    </div>
                  </GlassCard>
                )}

                {/* Recommendations */}
                <RecommendationsList
                  recommendations={dashboardData.escalation_risk?.recommendations || []}
                  delay={0.8}
                />
              </motion.div>
            )}

            {/* ============================================================ */}
            {/* WHAT TRIGGERS US — patterns                                  */}
            {/* ============================================================ */}
            {activeTab === 'triggers' && (
              <motion.div
                key="triggers"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className="space-y-6"
              >
                {/* Narrative */}
                <NarrativeInsightCard
                  title="Trigger Patterns"
                  insight={narrativeData?.trigger_insight ?? null}
                  loading={narrativeLoading}
                  delay={0}
                />

                {/* Trigger Phrases + Chronic Needs */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <TriggerPhrasesCard
                    data={dashboardData.trigger_phrases || { most_impactful: [] }}
                    delay={0.1}
                  />
                  <ChronicNeedsCard
                    data={dashboardData.chronic_needs || []}
                    delay={0.2}
                  />
                </div>

                {/* Attachment Styles (full width) */}
                {attachmentLoading ? (
                  <SkeletonCard lines={5} />
                ) : attachmentError ? (
                  <GlassCard className="p-6">
                    <p className="text-sm text-warmGray-500">Failed to load attachment style data.</p>
                    <button onClick={() => refreshAttachment()} className="text-sm text-purple-600 mt-2 hover:underline">Retry</button>
                  </GlassCard>
                ) : (
                  <AttachmentStyleCard
                    data={attachmentData}
                    partnerAName={partnerA}
                    partnerBName={partnerB}
                    delay={0.3}
                  />
                )}

                {/* Conflict Chains */}
                <GlassCard className="p-6" delay={0.4}>
                  <div className="flex items-center gap-3 mb-5">
                    <div className="p-2.5 rounded-xl bg-blue-50">
                      <BarChart3 size={20} className="text-blue-500" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-warmGray-800">Conflict Chains</h3>
                      <p className="text-xs text-warmGray-500">Related conflicts that share root causes</p>
                    </div>
                  </div>

                  {dashboardData.conflict_chains && dashboardData.conflict_chains.length > 0 ? (
                    <div className="space-y-3">
                      {dashboardData.conflict_chains.map((chain: any, idx: number) => (
                        <motion.div
                          key={idx}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.5 + idx * 0.1 }}
                          className="p-4 rounded-xl bg-warmGray-50/50 hover:bg-warmGray-50 transition-colors"
                        >
                          <p className="font-medium text-warmGray-800">{chain.root_cause || 'Unknown cause'}</p>
                          <p className="text-sm text-warmGray-500 mt-1">{chain.timeline || 'No timeline'}</p>
                          <div className="flex gap-4 mt-2">
                            <span className="text-xs text-warmGray-400">
                              {chain.conflicts_in_chain || 0} conflicts
                            </span>
                            <span className={`text-xs font-medium ${chain.is_resolved ? 'text-emerald-600' : 'text-amber-600'}`}>
                              {chain.is_resolved ? 'Resolved' : 'Ongoing'}
                            </span>
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-12">
                      <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-warmGray-100 flex items-center justify-center">
                        <BarChart3 size={24} className="text-warmGray-400" />
                      </div>
                      <p className="text-warmGray-500">No conflict chains detected yet</p>
                      <p className="text-xs text-warmGray-400 mt-1">Chains are identified when conflicts share similar root causes</p>
                    </div>
                  )}
                </GlassCard>
              </motion.div>
            )}

            {/* ============================================================ */}
            {/* ARE WE GROWING — trends + messaging                          */}
            {/* ============================================================ */}
            {activeTab === 'growing' && (
              <motion.div
                key="growing"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className="space-y-6"
              >
                {/* Narrative */}
                <NarrativeInsightCard
                  title="Growth Trajectory"
                  insight={narrativeData?.growth_insight ?? null}
                  loading={narrativeLoading}
                  delay={0}
                />

                {/* Communication Growth + Fight Frequency */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {commGrowthLoading ? (
                    <SkeletonCard lines={5} />
                  ) : commGrowthError ? (
                    <GlassCard className="p-6">
                      <p className="text-sm text-warmGray-500">Failed to load communication growth data.</p>
                      <button onClick={() => refreshCommGrowth()} className="text-sm text-purple-600 mt-2 hover:underline">Retry</button>
                    </GlassCard>
                  ) : (
                    <CommunicationGrowthCard data={commGrowthData} delay={0.1} />
                  )}

                  {fightFreqLoading ? (
                    <SkeletonCard lines={5} />
                  ) : fightFreqError ? (
                    <GlassCard className="p-6">
                      <p className="text-sm text-warmGray-500">Failed to load fight frequency data.</p>
                      <button onClick={() => refreshFightFreq()} className="text-sm text-purple-600 mt-2 hover:underline">Retry</button>
                    </GlassCard>
                  ) : (
                    <FightFrequencyChart data={fightFreqData} delay={0.2} />
                  )}
                </div>

                {/* Recovery Time (full width) */}
                {recoveryLoading ? (
                  <SkeletonCard lines={4} />
                ) : recoveryError ? (
                  <GlassCard className="p-6">
                    <p className="text-sm text-warmGray-500">Failed to load recovery time data.</p>
                    <button onClick={() => refreshRecovery()} className="text-sm text-purple-600 mt-2 hover:underline">Retry</button>
                  </GlassCard>
                ) : (
                  <RecoveryTimeCard data={recoveryData} delay={0.3} />
                )}

                {/* Messaging Insights (moved from standalone tab) */}
                <MessagingInsights
                  relationshipId={relationshipId}
                  partnerNames={{ partner_a: partnerA, partner_b: partnerB }}
                  delay={0.4}
                />
              </motion.div>
            )}

          </AnimatePresence>

        </div>
      </div>
    </div>
  );
};

export default Analytics;
