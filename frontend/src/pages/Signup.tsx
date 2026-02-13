import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Moon } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'serene_token';

const Signup = () => {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Something went wrong');
      }

      localStorage.setItem(TOKEN_KEY, data.token);
      if (data.relationship_id) {
        localStorage.setItem('serene_relationship_id', data.relationship_id);
      }
      // Full reload so Layout picks up the new token cleanly
      window.location.href = '/';
    } catch (err: any) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center px-4">
      <div className="w-full max-w-md animate-fade-in">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-4">
            <div className="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center">
              <Moon size={22} className="text-accent fill-accent" />
            </div>
          </div>
          <h1 className="text-h1 text-text-primary">Create your account</h1>
          <p className="text-body text-text-secondary mt-2">Start your journey with Serene</p>
        </div>

        {/* Form */}
        <div className="bg-surface-elevated rounded-2xl p-8 border border-border-subtle shadow-soft">
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="px-4 py-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-small">
                {error}
              </div>
            )}

            <div>
              <label className="block text-small font-medium text-text-primary mb-1.5">Name</label>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                required
                className="w-full px-4 py-3 rounded-xl bg-bg-primary border border-border-subtle text-text-primary placeholder-text-tertiary focus:outline-none focus:border-accent transition-colors"
                placeholder="Your full name"
              />
            </div>

            <div>
              <label className="block text-small font-medium text-text-primary mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 rounded-xl bg-bg-primary border border-border-subtle text-text-primary placeholder-text-tertiary focus:outline-none focus:border-accent transition-colors"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label className="block text-small font-medium text-text-primary mb-1.5">Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                minLength={6}
                className="w-full px-4 py-3 rounded-xl bg-bg-primary border border-border-subtle text-text-primary placeholder-text-tertiary focus:outline-none focus:border-accent transition-colors"
                placeholder="At least 6 characters"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-accent text-white font-medium rounded-xl hover:bg-accent-light transition-colors disabled:opacity-50"
            >
              {loading ? 'Creating account...' : 'Create account'}
            </button>
          </form>
        </div>

        <p className="text-center text-small text-text-secondary mt-6">
          Already have an account?{' '}
          <Link to="/login" className="text-accent hover:text-accent-light font-medium transition-colors">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
};

export default Signup;
