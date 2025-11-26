import React, { useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer,
  LineChart, Line, ComposedChart, Tooltip, Area, CartesianGrid
} from 'recharts';
import AnalyticsCard from '../components/AnalyticsCard';
import VoiceButton from '../components/VoiceButton';
import { Heart, Activity, Zap, TrendingUp, AlertTriangle, Calendar } from 'lucide-react';

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
    if (score >= 80) return 'text-emerald-500';
    if (score >= 60) return 'text-blue-500';
    return 'text-rose-500';
  };

  const getTensionColor = (level: string) => {
    switch (level) {
      case 'High': return 'bg-rose-100 text-rose-700 border-rose-200';
      case 'Medium': return 'bg-amber-100 text-amber-700 border-amber-200';
      default: return 'bg-emerald-100 text-emerald-700 border-emerald-200';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-rose-50 via-white to-blue-50 p-4 md:p-8 font-sans text-slate-800">
      <div className="max-w-5xl mx-auto space-y-6">

        {/* Header */}
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold text-slate-800 flex items-center justify-center gap-3">
            <Activity className="text-rose-500" />
            Relationship Pulse
          </h2>
          <p className="text-slate-500 mt-2">Real-time insights powered by your interactions</p>
        </div>

        {/* Top Row: Health Score & Forecast */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

          {/* Health Score Card */}
          <AnalyticsCard title="Relationship Health" className="md:col-span-1 bg-white/80">
            <div className="flex flex-col items-center justify-center py-4">
              <div className="relative w-32 h-32 flex items-center justify-center">
                <svg className="w-full h-full transform -rotate-90">
                  <circle cx="64" cy="64" r="56" stroke="#f1f5f9" strokeWidth="12" fill="none" />
                  <circle
                    cx="64" cy="64" r="56"
                    stroke="currentColor"
                    strokeWidth="12"
                    fill="none"
                    strokeDasharray={351}
                    strokeDashoffset={351 - (351 * data.health_score.value) / 100}
                    className={`${getHealthColor(data.health_score.value)} transition-all duration-1000 ease-out`}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className={`text-4xl font-bold ${getHealthColor(data.health_score.value)}`}>
                    {data.health_score.value}
                  </span>
                </div>
              </div>
              <div className="mt-4 text-center">
                <div className="font-bold text-slate-700">{data.health_score.status}</div>
                <div className="text-xs text-slate-400 uppercase tracking-wide flex items-center gap-1 justify-center mt-1">
                  <TrendingUp size={12} /> {data.health_score.trend} Trend
                </div>
              </div>
            </div>
          </AnalyticsCard>

          {/* Tension Forecast & Stats */}
          <div className="md:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-6">

            {/* Tension Forecast */}
            <AnalyticsCard title="Tension Forecast" className="bg-gradient-to-br from-white to-slate-50">
              <div className="flex items-start gap-4">
                <div className={`p-3 rounded-2xl ${getTensionColor(data.tension_forecast.level)}`}>
                  <Zap size={24} />
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-lg font-bold text-slate-800">{data.tension_forecast.level} Risk</span>
                  </div>
                  <p className="text-sm text-slate-600 leading-relaxed">
                    {data.tension_forecast.message}
                  </p>
                  {data.tension_forecast.next_high_risk_date && (
                    <div className="mt-3 text-xs font-semibold text-rose-500 bg-rose-50 inline-block px-2 py-1 rounded-lg">
                      Next potential spike: {new Date(data.tension_forecast.next_high_risk_date).toLocaleDateString()}
                    </div>
                  )}
                </div>
              </div>
            </AnalyticsCard>

            {/* Quick Stats Grid */}
            <div className="grid grid-rows-2 gap-4">
              <AnalyticsCard title="Intimacy (30d)" value={data.stats.intimacy_30d} color="bg-violet-50/50">
                <Heart className="absolute top-4 right-4 text-violet-300" size={20} />
              </AnalyticsCard>
              <AnalyticsCard title="Conflicts (30d)" value={data.stats.conflicts_30d} subValue={`${data.stats.unresolved} unresolved`} color="bg-orange-50/50">
                <AlertTriangle className="absolute top-4 right-4 text-orange-300" size={20} />
              </AnalyticsCard>
            </div>
          </div>
        </div>

        {/* Middle Row: Trends Chart */}
        <AnalyticsCard title="Interaction Trends (Last 30 Days)" className="bg-white/70 h-80">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data.trends} margin={{ top: 20, right: 20, bottom: 20, left: 0 }}>
              <defs>
                <linearGradient id="colorIntimacy" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12 }} dy={10} />
              <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#fff', borderRadius: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                cursor={{ fill: '#f1f5f9' }}
              />
              <Area type="monotone" dataKey="intimacy" stroke="#8b5cf6" fillOpacity={1} fill="url(#colorIntimacy)" strokeWidth={3} />
              <Bar dataKey="conflicts" barSize={20} fill="#f43f5e" radius={[4, 4, 0, 0]} />
            </ComposedChart>
          </ResponsiveContainer>
        </AnalyticsCard>

        {/* Bottom Row: Cycle Heatmap */}
        <AnalyticsCard title="Conflict Heatmap by Cycle Day" className="bg-white/70">
          <div className="space-y-4">
            <div className="flex justify-between text-xs text-slate-400 font-medium uppercase tracking-wider px-1">
              <span>Period</span>
              <span>Follicular</span>
              <span>Ovulation</span>
              <span>Luteal</span>
              <span>PMS</span>
            </div>

            <div className="grid grid-cols-30 gap-1 h-12">
              {data.cycle_correlation.map((count, i) => {
                // Calculate intensity based on count (0-5 scale)
                const intensity = Math.min(count * 200, 900); // Just a visual scaling
                const hasData = count > 0;

                return (
                  <div key={i} className="flex flex-col items-center group relative">
                    <div
                      className={`w-full h-full rounded-sm transition-all ${hasData ? `bg-rose-${Math.min(count * 200 + 300, 600)}` : 'bg-slate-100'
                        } hover:scale-125 hover:z-10`}
                    />
                    {/* Tooltip */}
                    <div className="absolute bottom-full mb-2 hidden group-hover:block bg-slate-800 text-white text-[10px] px-2 py-1 rounded whitespace-nowrap z-20">
                      Day {i + 1}: {count} conflicts
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="text-center text-xs text-slate-400 mt-2">
              Higher color intensity indicates more frequent conflicts on this cycle day.
            </div>
          </div>
        </AnalyticsCard>

        {/* Voice Command Hint */}
        <div className="flex flex-col items-center mt-8 space-y-4">
          <VoiceButton size="lg" />
          <p className="text-sm text-slate-500 bg-white/50 px-4 py-2 rounded-full border border-white/50">
            Try asking: "What's my relationship health score?"
          </p>
        </div>

      </div>
    </div>
  );
};

export default Analytics;