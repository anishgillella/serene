import React, { useEffect, useState } from 'react';
import { Moon, ArrowRight, Sparkles, MessageSquare, Clock } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const API_BASE = 'http://localhost:8000';

interface Conflict {
  id: string;
  title: string;
  started_at: string;
  status: string;
  metadata: {
    summary?: string;
    topics?: string[];
  };
}

const RecentConflicts = () => {
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchConflicts = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/conflicts`);
        if (res.ok) {
          const data = await res.json();
          // Get last 3 conflicts
          setConflicts(data.conflicts.slice(0, 3));
        }
      } catch (error) {
        console.error('Error fetching conflicts:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchConflicts();
  }, []);

  if (loading) {
    return (
      <div className="mb-12">
        <h2 className="text-h2 text-text-primary mb-6">Recent Conflicts</h2>
        <div className="space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="bg-surface-elevated rounded-2xl p-6 border border-border-subtle animate-pulse">
              <div className="h-4 bg-surface-hover rounded w-3/4 mb-3"></div>
              <div className="h-3 bg-surface-hover rounded w-1/2"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (conflicts.length === 0) {
    return null;
  }

  const getStatusColor = (status: string) => {
    if (status === 'completed' || status === 'resolved') return 'text-green-600 bg-green-50';
    if (status === 'active') return 'text-amber-600 bg-amber-50';
    return 'text-slate-600 bg-slate-50';
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="mb-12">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-h2 text-text-primary">Recent Conflicts</h2>
        <button
          onClick={() => navigate('/history')}
          className="text-small text-accent hover:text-accent-dark transition-colors flex items-center gap-1"
        >
          View All
          <ArrowRight size={16} />
        </button>
      </div>

      <div className="space-y-4">
        {conflicts.map((conflict) => (
          <div
            key={conflict.id}
            onClick={() => navigate(`/history`)}
            className="bg-surface-elevated rounded-2xl p-6 border border-border-subtle shadow-soft hover:shadow-subtle transition-all cursor-pointer group"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <h3 className="text-h3 text-text-primary mb-1 group-hover:text-accent transition-colors">
                  {conflict.title || 'Untitled Conflict'}
                </h3>
                <div className="flex items-center gap-3 text-tiny text-text-tertiary">
                  <span className="flex items-center gap-1">
                    <Clock size={12} />
                    {formatDate(conflict.started_at)}
                  </span>
                  <span className={`px-2 py-0.5 rounded-full ${getStatusColor(conflict.status)}`}>
                    {conflict.status}
                  </span>
                </div>
              </div>
            </div>

            {conflict.metadata?.summary && (
              <p className="text-small text-text-secondary line-clamp-2 mb-3">
                {conflict.metadata.summary}
              </p>
            )}

            {conflict.metadata?.topics && conflict.metadata.topics.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {conflict.metadata.topics.slice(0, 3).map((topic, i) => (
                  <span
                    key={i}
                    className="px-2 py-1 rounded-lg bg-surface-hover text-tiny text-text-secondary"
                  >
                    {topic}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

const Home = () => {
  const navigate = useNavigate();
  const currentHour = new Date().getHours();

  let greeting = 'Good morning';
  if (currentHour >= 12 && currentHour < 18) greeting = 'Good afternoon';
  if (currentHour >= 18) greeting = 'Good evening';

  return (
    <div className="max-w-4xl mx-auto animate-fade-in">
      {/* Welcome Section */}
      <div className="mb-12 text-center md:text-left">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/10 text-accent text-tiny font-medium mb-4 animate-slide-up">
          <Sparkles size={12} />
          <span>Your relationship companion</span>
        </div>
        <h1 className="text-4xl md:text-5xl font-medium text-text-primary mb-3 tracking-tight">
          {greeting}, Adrian.
        </h1>
        <p className="text-body text-text-secondary max-w-xl">
          Luna is here to help you navigate conflicts, track your journey, and build a stronger connection.
        </p>
      </div>

      {/* Quick Actions Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
        {/* Primary Action: Capture */}
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

        {/* Secondary Actions */}
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
            onClick={() => navigate('/history')}
            className="bg-surface-elevated rounded-3xl p-6 border border-border-subtle shadow-soft hover:shadow-subtle transition-all cursor-pointer flex items-center justify-between group"
          >
            <div>
              <h3 className="text-h3 text-text-primary mb-1">View History</h3>
              <p className="text-small text-text-secondary">Review past insights</p>
            </div>
            <div className="w-10 h-10 rounded-full bg-surface-hover flex items-center justify-center group-hover:bg-accent/10 group-hover:text-accent transition-colors">
              <ArrowRight size={20} />
            </div>
          </div>
        </div>
      </div>

      {/* Recent Conflicts Section */}
      <RecentConflicts />
    </div>
  );
};

export default Home;