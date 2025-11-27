import React from 'react';
import { Moon, ArrowRight, Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

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
    </div>
  );
};

export default Home;