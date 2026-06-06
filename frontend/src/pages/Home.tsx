import React, { useEffect } from 'react';
import {
  Moon,
  ArrowRight,
  Sparkles,
  BookOpen,
  Bell,
  Heart,
  Shield,
  Activity,
  Link2,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useRelationship, useRelationshipId } from '../contexts/RelationshipContext';
import { useLatestDigest } from '../hooks/useDigests';
import { useUnreadAlertCount } from '../hooks/useAlerts';
import { useDashboardData } from '../hooks/useDashboardData';
import { useGottmanData } from '../hooks/useGottmanData';
import { AnimatedHealthRing } from '../components/premium';

const RelationshipInsights = () => {
  const navigate = useNavigate();
  const relationshipId = useRelationshipId();
  const { dashboardData, loading, error, refresh } = useDashboardData(relationshipId);
  const { gottmanData, loading: gottmanLoading, fetchGottmanData } = useGottmanData(relationshipId);

  useEffect(() => {
    refresh();
    fetchGottmanData();
  }, [refresh, fetchGottmanData]);

  if (loading && !dashboardData) {
    return (
      <div className="mb-12">
        <h2 className="text-h2 text-text-primary mb-2">Your Relationship</h2>
        <p className="text-small text-text-secondary mb-6">Loading patterns and health signals...</p>
        <div className="bg-surface-elevated rounded-2xl p-8 border border-border-subtle animate-pulse">
          <div className="h-32 bg-surface-hover rounded-xl mb-6" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-20 bg-surface-hover rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error && !dashboardData) {
    return (
      <div className="mb-12">
        <h2 className="text-h2 text-text-primary mb-6">Your Relationship</h2>
        <div className="bg-surface-elevated rounded-2xl p-6 border border-border-subtle text-center">
          <p className="text-small text-text-secondary mb-4">{error}</p>
          <button
            onClick={refresh}
            className="text-small text-accent hover:text-accent-dark transition-colors"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="mb-12">
        <h2 className="text-h2 text-text-primary mb-2">Your Relationship</h2>
        <p className="text-body text-text-secondary mb-6">
          Start a session with Luna to build your relationship picture — we track patterns, not just moments.
        </p>
        <div
          onClick={() => navigate('/fight-capture')}
          className="bg-surface-elevated rounded-2xl p-6 border border-dashed border-border-subtle cursor-pointer hover:border-accent/40 transition-all flex items-center justify-between"
        >
          <span className="text-small text-text-secondary">No data yet — capture your first disagreement</span>
          <ArrowRight size={18} className="text-accent" />
        </div>
      </div>
    );
  }

  const metrics = dashboardData.metrics;
  const episodes =
    metrics.disagreement_episodes ??
    metrics.total_conflicts;
  const openThreads = metrics.open_threads ?? metrics.unresolved_conflicts;
  const daysCalm = metrics.days_since_last_conflict ?? 0;
  const repairRate = Math.round(metrics.resolution_rate ?? 0);
  const healthScore = dashboardData.health_score ?? 50;
  const healthPrev = dashboardData.health_score_previous;
  const healthDelta =
    typeof healthPrev === 'number' ? healthScore - healthPrev : null;
  const healthTrend =
    healthDelta !== null && healthDelta > 2
      ? 'up'
      : healthDelta !== null && healthDelta < -2
        ? 'down'
        : 'stable';

  const topNeed = dashboardData.chronic_needs?.[0];
  const topInsight = dashboardData.insights?.[0];
  const repairSuccess = gottmanData?.repair_metrics?.success_rate;

  const hasActivity = episodes > 0 || (gottmanData?.has_data ?? false);

  return (
    <div className="mb-12">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-h2 text-text-primary">Your Relationship</h2>
        <button
          onClick={() => navigate('/analytics')}
          className="text-small text-accent hover:text-accent-dark transition-colors flex items-center gap-1"
        >
          Full insights
          <ArrowRight size={16} />
        </button>
      </div>
      <p className="text-small text-text-secondary mb-6 max-w-2xl">
        We group related disagreements into episodes — one argument that spirals isn&apos;t counted as three separate fights.
      </p>

      <div className="bg-surface-elevated rounded-3xl p-6 md:p-8 border border-border-subtle shadow-soft">
        <div className="flex flex-col md:flex-row gap-8 items-center md:items-start">
          <div className="flex flex-col items-center shrink-0">
            <AnimatedHealthRing value={healthScore} size={140} strokeWidth={10} trend={healthTrend} />
            <p className="text-tiny text-text-tertiary mt-3 text-center">Relationship health</p>
            {healthDelta !== null && (
              <p
                className={`text-tiny mt-1 ${
                  healthDelta > 0 ? 'text-green-600' : healthDelta < 0 ? 'text-amber-600' : 'text-text-tertiary'
                }`}
              >
                {healthDelta > 0 ? '+' : ''}
                {healthDelta} vs last period
              </p>
            )}
          </div>

          <div className="flex-1 w-full grid grid-cols-2 gap-4">
            <InsightStat
              icon={<Activity size={18} />}
              label="Episodes tracked"
              value={hasActivity ? String(episodes) : '—'}
              hint="Grouped disagreements"
            />
            <InsightStat
              icon={<Shield size={18} />}
              label="Repair rate"
              value={hasActivity ? `${repairRate}%` : '—'}
              hint="Resolved vs captured"
            />
            <InsightStat
              icon={<Heart size={18} />}
              label="Days of calm"
              value={daysCalm > 0 ? String(daysCalm) : hasActivity ? '0' : '—'}
              hint="Since last tension"
            />
            <InsightStat
              icon={<Link2 size={18} />}
              label="Open threads"
              value={hasActivity ? String(openThreads) : '—'}
              hint="Still need attention"
            />
          </div>
        </div>

        {(topInsight || topNeed || (gottmanData?.has_data && repairSuccess != null)) && (
          <div className="mt-6 pt-6 border-t border-border-subtle space-y-3">
            {topInsight && (
              <p className="text-small text-text-primary">{topInsight}</p>
            )}
            {topNeed && (
              <p className="text-small text-text-secondary">
                Recurring need: <span className="text-text-primary font-medium">{formatNeed(topNeed.need)}</span>
                {topNeed.percentage_of_conflicts > 0 && (
                  <span className="text-text-tertiary"> · shows up in {Math.round(topNeed.percentage_of_conflicts)}% of episodes</span>
                )}
              </p>
            )}
            {!gottmanLoading && gottmanData?.has_data && repairSuccess != null && (
              <p className="text-small text-text-secondary">
                Gottman repair success: <span className="text-text-primary font-medium">{Math.round(repairSuccess)}%</span>
              </p>
            )}
            {dashboardData.escalation_risk?.interpretation && (
              <p className="text-tiny text-text-tertiary capitalize">
                Tension level: {dashboardData.escalation_risk.interpretation}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const InsightStat = ({
  icon,
  label,
  value,
  hint,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  hint: string;
}) => (
  <div className="bg-surface-hover/50 rounded-2xl p-4 border border-border-subtle">
    <div className="flex items-center gap-2 text-accent mb-2">{icon}</div>
    <p className="text-tiny text-text-tertiary mb-1">{label}</p>
    <p className="text-2xl font-medium text-text-primary">{value}</p>
    <p className="text-tiny text-text-tertiary mt-1">{hint}</p>
  </div>
);

const formatNeed = (need: string) =>
  need.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

const Home = () => {
  const navigate = useNavigate();
  const { partnerAName } = useRelationship();
  const displayName = partnerAName || 'there';
  const currentHour = new Date().getHours();

  let greeting = 'Good morning';
  if (currentHour >= 12 && currentHour < 18) greeting = 'Good afternoon';
  if (currentHour >= 18) greeting = 'Good evening';

  return (
    <div className="max-w-4xl mx-auto animate-fade-in">
      <div className="mb-12 text-center md:text-left">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/10 text-accent text-tiny font-medium mb-4 animate-slide-up">
          <Sparkles size={12} />
          <span>Your relationship companion</span>
        </div>
        <h1 className="text-4xl md:text-5xl font-medium text-text-primary mb-3 tracking-tight">
          {greeting}, {displayName}.
        </h1>
        <p className="text-body text-text-secondary max-w-xl">
          Luna helps you understand patterns in your connection — not just count disagreements.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
        <div
          onClick={() => navigate('/fight-capture')}
          className="group relative overflow-hidden bg-surface-elevated rounded-3xl p-8 border border-border-subtle shadow-soft hover:shadow-lifted transition-all cursor-pointer"
        >
          <div className="absolute top-0 right-0 p-8 opacity-10 group-hover:opacity-20 transition-opacity">
            <Moon size={120} className="text-accent rotate-12" />
          </div>

          <div className="relative z-10">
            <div className="w-12 h-12 rounded-2xl bg-accent/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
              <Moon size={24} className="text-accent fill-accent" />
            </div>
            <h3 className="text-h2 text-text-primary mb-2">Start Session</h3>
            <p className="text-body text-text-secondary mb-6">
              Having a disagreement? Let Luna mediate and help you understand each other.
            </p>
            <div className="flex items-center gap-2 text-accent font-medium group-hover:gap-3 transition-all">
              <span>Begin Capture</span>
              <ArrowRight size={18} />
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div
            onClick={() => navigate('/calendar')}
            className="bg-surface-elevated rounded-3xl p-6 border border-border-subtle shadow-soft hover:shadow-subtle transition-all cursor-pointer flex items-center justify-between group"
          >
            <div>
              <h3 className="text-h3 text-text-primary mb-1">Check Calendar</h3>
              <p className="text-small text-text-secondary">Log events or view cycles</p>
            </div>
            <div className="w-10 h-10 rounded-full bg-surface-hover flex items-center justify-center group-hover:bg-accent/10 group-hover:text-accent transition-colors">
              <ArrowRight size={20} />
            </div>
          </div>

          <div
            onClick={() => navigate('/analytics')}
            className="bg-surface-elevated rounded-3xl p-6 border border-border-subtle shadow-soft hover:shadow-subtle transition-all cursor-pointer flex items-center justify-between group"
          >
            <div>
              <h3 className="text-h3 text-text-primary mb-1">Relationship Insights</h3>
              <p className="text-small text-text-secondary">Gottman metrics, triggers, growth</p>
            </div>
            <div className="w-10 h-10 rounded-full bg-surface-hover flex items-center justify-center group-hover:bg-accent/10 group-hover:text-accent transition-colors">
              <ArrowRight size={20} />
            </div>
          </div>
        </div>
      </div>

      <DigestAlertBanner />
      <RelationshipInsights />
    </div>
  );
};

const DigestAlertBanner = () => {
  const navigate = useNavigate();
  const { relationshipId } = useRelationship();
  const rid = relationshipId || '00000000-0000-0000-0000-000000000000';
  const { digest, loading: digestLoading } = useLatestDigest(rid);
  const { count: alertCount, loading: alertLoading } = useUnreadAlertCount(rid);

  if (digestLoading && alertLoading) return null;
  if (!digest && alertCount === 0) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-12">
      {digest && (
        <div
          onClick={() => navigate('/digests')}
          className="bg-surface-elevated rounded-2xl p-5 border border-accent/20 hover:border-accent/40 cursor-pointer transition-all flex items-center gap-4"
        >
          <div className="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center flex-shrink-0">
            <BookOpen size={20} className="text-accent" />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-small font-medium text-text-primary">New Weekly Digest</h4>
            <p className="text-tiny text-text-secondary truncate">
              {digest.narrative ? digest.narrative.slice(0, 80) + '...' : 'Your weekly summary is ready'}
            </p>
          </div>
          <ArrowRight size={16} className="text-text-tertiary flex-shrink-0" />
        </div>
      )}
      {alertCount > 0 && (
        <div
          onClick={() => navigate('/notifications')}
          className="bg-surface-elevated rounded-2xl p-5 border border-amber-500/20 hover:border-amber-500/40 cursor-pointer transition-all flex items-center gap-4"
        >
          <div className="w-10 h-10 rounded-full bg-amber-500/10 flex items-center justify-center flex-shrink-0 relative">
            <Bell size={20} className="text-amber-500" />
            <span className="absolute -top-1 -right-1 w-5 h-5 bg-amber-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
              {alertCount}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-small font-medium text-text-primary">
              {alertCount} Active Alert{alertCount !== 1 ? 's' : ''}
            </h4>
            <p className="text-tiny text-text-secondary">Tap to view and manage</p>
          </div>
          <ArrowRight size={16} className="text-text-tertiary flex-shrink-0" />
        </div>
      )}
    </div>
  );
};

export default Home;
