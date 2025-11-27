import React, { useEffect, useState } from 'react';
import {
  Bar, XAxis, YAxis, ResponsiveContainer,
  ComposedChart, Tooltip, Area, CartesianGrid,
  PieChart, Pie, Cell, Legend
} from 'recharts';
import AnalyticsCard from '../components/AnalyticsCard';
import VoiceButton from '../components/VoiceButton';
import { Heart, Activity, Zap, TrendingUp, AlertTriangle } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

interface AnalyticsData {
  health_score: {
    value: number;
    trend: 'improving' | 'declining' | 'stable';
    status: string;
  };
  trends: Array<{
    name: string;
    conflicts: number;
    intimacy: number;
    date_start: string;
    date_end: string;
  }>;
  cycle_correlation: number[];
  tension_forecast: {
    level: 'Low' | 'Medium' | 'High';
    message: string;
    next_high_risk_date: string | null;
  };
  stats: {
    conflicts_30d: number;
    intimacy_30d: number;
    unresolved: number;
  };
  resolution_breakdown: Array<{
    name: string;
    value: number;
    color: string;
  }>;
  day_of_week_activity: Array<{
    day: string;
    conflicts: number;
    intimacy: number;
  }>;
  conflict_themes: Array<{
    name: string;
    value: number;
  }>;
  sex_conflict_ratio_2w: {
    value: number;
    conflicts: number;
    intimacy: number;
    status: string;
  };
  magic_ratio: {
    value: number;
    status: string;
    target: number;
  };
}

const Analytics = () => {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/analytics/dashboard?partner_id=partner_b`);
        if (res.ok) {
          setData(await res.json());
        }
      } catch (error) {
        console.error('Error fetching analytics:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-rose-200 border-t-rose-500"></div>
      </div>
    );
  }

  if (!data) return <div className="text-center p-8 text-slate-500">Failed to load analytics data.</div>;

  const getHealthColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-blue-600';
    return 'text-accent';
  };

  const getTensionColor = (level: string) => {
    switch (level) {
      case 'High': return 'bg-red-50 text-red-700 border-red-100';
      case 'Medium': return 'bg-amber-50 text-amber-700 border-amber-100';
      default: return 'bg-green-50 text-green-700 border-green-100';
    }
  };

  return (
    <div className="min-h-screen bg-bg-primary p-4 md:p-8 font-sans text-text-primary">
      <div className="max-w-5xl mx-auto space-y-6">

        {/* Header */}
        <div className="text-center mb-8">
          <h2 className="text-h2 text-text-primary flex items-center justify-center gap-3 mb-2">
            <Activity className="text-accent" strokeWidth={1.5} />
            Relationship Pulse
          </h2>
          <p className="text-body text-text-secondary">Real-time insights powered by your interactions</p>
        </div>

        {/* Top Row: Health Score & Forecast */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

          {/* Health Score Card */}
          <AnalyticsCard title="Relationship Health" className="md:col-span-1">
            <div className="flex flex-col items-center justify-center py-4">
              <div className="relative w-32 h-32 flex items-center justify-center">
                <svg className="w-full h-full transform -rotate-90">
                  <circle cx="64" cy="64" r="56" stroke="#E4E4E7" strokeWidth="8" fill="none" />
                  <circle
                    cx="64" cy="64" r="56"
                    stroke="currentColor"
                    strokeWidth="8"
                    fill="none"
                    strokeDasharray={351}
                    strokeDashoffset={351 - (351 * data.health_score.value) / 100}
                    className={`${getHealthColor(data.health_score.value)} transition-all duration-1000 ease-out`}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className={`text-4xl font-light ${getHealthColor(data.health_score.value)}`}>
                    {data.health_score.value}
                  </span>
                </div>
              </div>
              <div className="mt-4 text-center">
                <div className="text-h3 text-text-primary mb-1">{data.health_score.status}</div>
                <div className="text-tiny text-text-tertiary uppercase tracking-wider flex items-center gap-1 justify-center">
                  <TrendingUp size={12} /> {data.health_score.trend} Trend
                </div>
              </div>
            </div>
          </AnalyticsCard>

          {/* Tension Forecast & Stats */}
          <div className="md:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-6">

            {/* Tension Forecast */}
            <AnalyticsCard title="Tension Forecast" className="bg-surface-elevated">
              <div className="flex items-start gap-4">
                <div className={`p-3 rounded-xl border ${getTensionColor(data.tension_forecast.level)} bg-opacity-20`}>
                  <Zap size={24} strokeWidth={1.5} />
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-h3 text-text-primary">{data.tension_forecast.level} Risk</span>
                  </div>
                  <p className="text-body text-text-secondary leading-relaxed">
                    {data.tension_forecast.message}
                  </p>
                  {data.tension_forecast.next_high_risk_date && (
                    <div className="mt-3 text-tiny font-medium text-accent bg-surface-hover border border-border-subtle inline-block px-2 py-1 rounded-lg">
                      Next potential spike: {new Date(data.tension_forecast.next_high_risk_date).toLocaleDateString()}
                    </div>
                  )}
                </div>
              </div>
            </AnalyticsCard>

            {/* Quick Stats Grid */}
            <div className="grid grid-rows-2 gap-4">
              <AnalyticsCard title="Intimacy (30d)" value={data.stats.intimacy_30d} color="bg-surface-elevated">
                <Heart className="absolute top-4 right-4 text-accent-light" size={20} strokeWidth={1.5} />
              </AnalyticsCard>
              <AnalyticsCard title="Conflicts (30d)" value={data.stats.conflicts_30d} subValue={`${data.stats.unresolved} unresolved`} color="bg-surface-elevated">
                <AlertTriangle className="absolute top-4 right-4 text-amber-300" size={20} strokeWidth={1.5} />
              </AnalyticsCard>
            </div>
          </div>
        </div>

        {/* Middle Row: Trends Chart */}
        <AnalyticsCard title="Interaction Trends (Last 30 Days)" className="bg-surface-elevated h-80">
          {data.trends.some(t => t.conflicts > 0 || t.intimacy > 0) ? (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={data.trends} margin={{ top: 20, right: 20, bottom: 20, left: 0 }}>
                <defs>
                  <linearGradient id="colorIntimacy" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#A78295" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#A78295" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E4E4E7" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#8E8E8E', fontSize: 12 }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#8E8E8E', fontSize: 12 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#FFFFFF', borderRadius: '12px', border: '1px solid #E4E4E7', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05)' }}
                  cursor={{ fill: '#F5F5F4' }}
                />
                <Area type="monotone" dataKey="intimacy" stroke="#A78295" fillOpacity={1} fill="url(#colorIntimacy)" strokeWidth={2} />
                <Bar dataKey="conflicts" barSize={20} fill="#D4D4D8" radius={[4, 4, 0, 0]} />
              </ComposedChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-text-tertiary">
              <Activity size={48} strokeWidth={1} className="mb-4 opacity-50" />
              <p>No interaction data recorded in the last 30 days.</p>
            </div>
          )}
        </AnalyticsCard>



        {/* New Row: Resolution & Weekly Activity */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Resolution Status Pie Chart */}
          <AnalyticsCard title="Conflict Resolution Status" className="md:col-span-1 bg-surface-elevated">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.resolution_breakdown}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {data.resolution_breakdown.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} strokeWidth={0} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#FFFFFF', borderRadius: '12px', border: '1px solid #E4E4E7' }}
                  />
                  <Legend verticalAlign="bottom" height={36} iconType="circle" />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </AnalyticsCard>

          {/* Day of Week Activity Bar Chart */}
          <AnalyticsCard title="Activity by Day of Week" className="md:col-span-2 bg-surface-elevated">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={data.day_of_week_activity} margin={{ top: 20, right: 20, bottom: 20, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E4E4E7" />
                  <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: '#8E8E8E', fontSize: 12 }} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#8E8E8E', fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#FFFFFF', borderRadius: '12px', border: '1px solid #E4E4E7', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05)' }}
                    cursor={{ fill: '#F5F5F4' }}
                  />
                  <Bar dataKey="conflicts" name="Conflicts" barSize={20} fill="#D4D4D8" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="intimacy" name="Intimacy" barSize={20} fill="#A78295" radius={[4, 4, 0, 0]} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </AnalyticsCard>
        </div>



        {/* New Row: Themes, Balance, Ratio */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

          {/* Conflict Themes */}
          <AnalyticsCard title="Common Conflict Themes" className="md:col-span-1 bg-surface-elevated">
            <div className="h-64 flex flex-col justify-center space-y-4">
              {data.conflict_themes && data.conflict_themes.length > 0 ? (
                data.conflict_themes.map((theme, i) => (
                  <div key={i} className="space-y-1">
                    <div className="flex justify-between text-small text-text-primary">
                      <span>{theme.name}</span>
                      <span className="text-text-tertiary">{theme.value}</span>
                    </div>
                    <div className="h-2 bg-surface-hover rounded-full overflow-hidden">
                      <div
                        className="h-full bg-rose-400 rounded-full"
                        style={{ width: `${(theme.value / Math.max(...data.conflict_themes.map(t => t.value))) * 100}%` }}
                      />
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center text-text-tertiary">No themes detected yet</div>
              )}
            </div>
          </AnalyticsCard>

          {/* Sex:Conflict Ratio (2 Weeks) */}
          <AnalyticsCard title="Sex:Conflict Ratio (2 Weeks)" className="md:col-span-1 bg-surface-elevated">
            <div className="h-64 flex flex-col items-center justify-center text-center">
              <div className="text-5xl font-light text-text-primary mb-2">
                {data.sex_conflict_ratio_2w.value}:1
              </div>
              <div className={`text-h3 mb-4 ${data.sex_conflict_ratio_2w.status === 'Healthy' ? 'text-green-600' : 'text-amber-600'
                }`}>
                {data.sex_conflict_ratio_2w.status}
              </div>
              <div className="flex gap-4 text-small text-text-secondary">
                <div className="flex flex-col items-center">
                  <span className="text-h3 text-rose-400">{data.sex_conflict_ratio_2w.intimacy}</span>
                  <span className="text-tiny text-text-tertiary">Intimacy</span>
                </div>
                <div className="h-8 w-px bg-border-subtle"></div>
                <div className="flex flex-col items-center">
                  <span className="text-h3 text-slate-400">{data.sex_conflict_ratio_2w.conflicts}</span>
                  <span className="text-tiny text-text-tertiary">Conflicts</span>
                </div>
              </div>
            </div>
          </AnalyticsCard>

          {/* Magic Ratio */}
          <AnalyticsCard title="The Magic Ratio" className="md:col-span-1 bg-surface-elevated">
            <div className="h-64 flex flex-col items-center justify-center text-center">
              <div className="text-5xl font-light text-text-primary mb-2">
                {data.magic_ratio.value}:1
              </div>
              <div className={`text-h3 mb-4 ${data.magic_ratio.status === 'Healthy' ? 'text-green-600' :
                data.magic_ratio.status === 'Balanced' ? 'text-blue-600' : 'text-amber-600'
                }`}>
                {data.magic_ratio.status}
              </div>
              <p className="text-body text-text-secondary px-4">
                Intimacy events vs. Conflicts (30d). <br />
                <span className="text-tiny text-text-tertiary">Based on Dr. Gottman's "5:1 Ratio" for relationship stability.</span>
              </p>
            </div>
          </AnalyticsCard>

        </div>

        {/* Voice Command Hint */}
        <div className="flex flex-col items-center mt-8 space-y-4">
          <VoiceButton size="lg" />
          <p className="text-small text-text-secondary bg-surface-elevated px-4 py-2 rounded-full border border-border-subtle shadow-soft">
            Try asking: "What's my relationship health score?"
          </p>
        </div>

      </div >
    </div >
  );
};

export default Analytics;