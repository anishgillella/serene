import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Moon, Shield, Brain, Heart } from 'lucide-react';

const Landing = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-bg-primary font-sans">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 md:px-12 py-6 max-w-6xl mx-auto">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-accent/10 flex items-center justify-center">
            <Moon size={18} className="text-accent fill-accent" />
          </div>
          <span className="text-h3 font-medium text-text-primary tracking-tight">Serene</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/login')}
            className="px-4 py-2 text-small text-text-secondary hover:text-text-primary transition-colors"
          >
            Log in
          </button>
          <button
            onClick={() => navigate('/signup')}
            className="px-5 py-2 bg-accent text-white text-small font-medium rounded-xl hover:bg-accent-light transition-colors"
          >
            Sign up
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 pt-16 pb-24 text-center animate-fade-in">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-accent/10 text-accent text-tiny font-medium mb-8 animate-slide-up">
          <Heart size={12} className="fill-accent" />
          <span>AI-powered relationship support</span>
        </div>

        <h1 className="text-5xl md:text-6xl font-medium text-text-primary tracking-tight mb-6 leading-tight">
          Navigate conflict<br />with clarity & care
        </h1>

        <p className="text-lg text-text-secondary max-w-2xl mx-auto mb-10 leading-relaxed">
          Serene helps couples understand each other during disagreements. Record, reflect, and receive personalised insights from Luna, your AI relationship companion.
        </p>

        <div className="flex items-center justify-center gap-4">
          <button
            onClick={() => navigate('/signup')}
            className="px-8 py-3.5 bg-accent text-white font-medium rounded-2xl hover:bg-accent-light transition-all shadow-subtle hover:shadow-lifted"
          >
            Get Started
          </button>
          <button
            onClick={() => navigate('/login')}
            className="px-8 py-3.5 bg-surface-elevated text-text-primary font-medium rounded-2xl border border-border-subtle hover:border-accent transition-all shadow-soft"
          >
            Log in
          </button>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-5xl mx-auto px-6 pb-32">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-surface-elevated rounded-3xl p-8 border border-border-subtle shadow-soft animate-slide-up">
            <div className="w-12 h-12 rounded-2xl bg-accent/10 flex items-center justify-center mb-5">
              <Shield size={24} className="text-accent" />
            </div>
            <h3 className="text-h3 text-text-primary mb-2">Conflict Mediation</h3>
            <p className="text-small text-text-secondary leading-relaxed">
              Record disagreements in real time. Luna listens to both sides and provides fair, impartial analysis.
            </p>
          </div>

          <div className="bg-surface-elevated rounded-3xl p-8 border border-border-subtle shadow-soft animate-slide-up" style={{ animationDelay: '100ms' }}>
            <div className="w-12 h-12 rounded-2xl bg-accent/10 flex items-center justify-center mb-5">
              <Brain size={24} className="text-accent" />
            </div>
            <h3 className="text-h3 text-text-primary mb-2">AI Insights</h3>
            <p className="text-small text-text-secondary leading-relaxed">
              Get personalised analysis of communication patterns, emotional triggers, and attachment styles.
            </p>
          </div>

          <div className="bg-surface-elevated rounded-3xl p-8 border border-border-subtle shadow-soft animate-slide-up" style={{ animationDelay: '200ms' }}>
            <div className="w-12 h-12 rounded-2xl bg-accent/10 flex items-center justify-center mb-5">
              <Heart size={24} className="text-accent" />
            </div>
            <h3 className="text-h3 text-text-primary mb-2">Repair Plans</h3>
            <p className="text-small text-text-secondary leading-relaxed">
              Receive tailored repair plans with concrete steps to reconnect and strengthen your relationship.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border-subtle py-8">
        <div className="max-w-5xl mx-auto px-6 flex items-center justify-between text-tiny text-text-tertiary">
          <span>Serene</span>
          <div className="flex items-center gap-6">
            <button onClick={() => navigate('/login')} className="hover:text-text-primary transition-colors">
              Log in
            </button>
            <button onClick={() => navigate('/signup')} className="hover:text-text-primary transition-colors">
              Sign up
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
