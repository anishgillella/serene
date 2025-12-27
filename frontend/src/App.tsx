import React from 'react';
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
import Layout from './components/Layout';
import { RelationshipProvider } from './contexts/RelationshipContext';

// Auth is disabled for now - will be enabled later
// TODO: Re-enable Auth0 authentication when ready

export function App() {
  return (
    <RelationshipProvider>
      <Router>
        <Routes>
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
              </Routes>
            </Layout>
          } />
        </Routes>
      </Router>
    </RelationshipProvider>
  );
}
