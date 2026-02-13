import React, { useEffect, useState } from 'react';
import { useLocation, Navigate, useNavigate } from 'react-router-dom';
import Sidebar from './navigation/Sidebar';
import BottomNav from './navigation/BottomNav';

const TOKEN_KEY = 'serene_token';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const isFullWidthPage = ['/fight-capture', '/post-fight'].includes(location.pathname);

  const [authState, setAuthState] = useState<'loading' | 'authenticated' | 'unauthenticated'>('loading');
  const [userName, setUserName] = useState<string>('');

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setAuthState('unauthenticated');
      return;
    }

    // Verify token with backend
    const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    fetch(`${API_BASE}/api/auth/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
        'ngrok-skip-browser-warning': 'true',
      },
    })
      .then(res => {
        if (!res.ok) {
          localStorage.removeItem(TOKEN_KEY);
          setAuthState('unauthenticated');
          return null;
        }
        return res.json();
      })
      .then(data => {
        if (data) {
          setUserName(data.partner_name || data.user?.name || '');
          setAuthState('authenticated');
        }
      })
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        setAuthState('unauthenticated');
      });
  }, []);

  // Show loading spinner while verifying token
  if (authState === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-primary">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent" />
      </div>
    );
  }

  // Redirect to landing if not authenticated
  if (authState === 'unauthenticated') {
    return <Navigate to="/landing" replace />;
  }

  const handleLogout = () => {
    localStorage.removeItem(TOKEN_KEY);
    navigate('/landing');
  };

  return (
    <div className="min-h-screen bg-bg-primary text-text-primary font-sans">
      {/* Desktop Sidebar */}
      <Sidebar />

      {/* Top-right user info */}
      <div className="fixed top-4 right-4 z-50 flex items-center gap-3">
        {userName && (
          <span className="text-small text-text-secondary hidden md:inline">
            {userName}
          </span>
        )}
        <button
          onClick={handleLogout}
          className="text-tiny text-text-tertiary hover:text-text-primary transition-colors px-2 py-1 rounded-lg hover:bg-surface-hover"
        >
          Logout
        </button>
      </div>

      {/* Main Content Area */}
      <main className={`transition-all duration-300 md:ml-64 pb-20 md:pb-0 min-h-screen`}>
        <div className={`w-full p-4 md:p-8 ${isFullWidthPage ? 'max-w-full' : 'max-w-5xl mx-auto'}`}>
          {children}
        </div>
      </main>

      {/* Mobile Bottom Nav */}
      <BottomNav />
    </div>
  );
};

export default Layout;
