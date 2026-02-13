import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Home from './pages/Home';
import FightCapture from './pages/FightCapture';
import PostFightSession from './pages/PostFightSession';
import Analytics from './pages/Analytics';
import Upload from './pages/Upload';
import History from './pages/History';
import Calendar from './pages/Calendar';
import Onboarding from './pages/Onboarding';
import Profile from './pages/Profile';
import PartnerChat from './pages/PartnerChat';
import Layout from './components/Layout';
import { RelationshipProvider } from './contexts/RelationshipContext';

// Lazy-load auth pages (not needed on initial load)
const Landing = lazy(() => import('./pages/Landing'));
const Login = lazy(() => import('./pages/Login'));
const Signup = lazy(() => import('./pages/Signup'));

function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent" />
    </div>
  );
}

export function App() {
  return (
    <RelationshipProvider>
      <Router>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            {/* Public routes — no Layout wrapper */}
            <Route path="/landing" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />

            {/* Authenticated routes — wrapped in Layout */}
            <Route path="/*" element={
              <Layout>
                <Routes>
                  <Route path="/" element={<Home />} />
                  <Route path="/fight-capture" element={<FightCapture />} />
                  <Route path="/post-fight" element={<PostFightSession />} />
                  <Route path="/analytics" element={<Analytics />} />
                  {/* Redirect old analytics sub-routes to main analytics page */}
                  <Route path="/analytics/dashboard" element={<Navigate to="/analytics" replace />} />
                  <Route path="/analytics/conflicts" element={<Navigate to="/analytics" replace />} />
                  <Route path="/analytics/triggers" element={<Navigate to="/analytics" replace />} />
                  <Route path="/analytics/timeline" element={<Navigate to="/analytics" replace />} />
                  <Route path="/upload" element={<Upload />} />
                  <Route path="/history" element={<History />} />
                  <Route path="/calendar" element={<Calendar />} />
                  <Route path="/onboarding" element={<Onboarding />} />
                  <Route path="/profile" element={<Profile />} />
                  <Route path="/chat" element={<PartnerChat />} />
                </Routes>
              </Layout>
            } />
          </Routes>
        </Suspense>
      </Router>
    </RelationshipProvider>
  );
}
