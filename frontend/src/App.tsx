import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import FightCapture from './pages/FightCapture';
import PostFightSession from './pages/PostFightSession';
import Analytics from './pages/Analytics';
import ConflictAnalysis from './pages/Analytics/ConflictAnalysis';
import TriggerPhrases from './pages/Analytics/TriggerPhrases';
import Timeline from './pages/Analytics/Timeline';
import Dashboard from './pages/Analytics/Dashboard';
import Upload from './pages/Upload';
import History from './pages/History';
import Calendar from './pages/Calendar';
import Onboarding from './pages/Onboarding';
import Profile from './pages/Profile';
import Layout from './components/Layout';
import { RelationshipProvider } from './contexts/RelationshipContext';
import { AnalyticsProvider } from './contexts/AnalyticsContext';

// Auth is disabled for now - will be enabled later
// TODO: Re-enable Auth0 authentication when ready

export function App() {
  return (
    <RelationshipProvider>
      <AnalyticsProvider>
        <Router>
          <Routes>
            <Route path="/*" element={
              <Layout>
                <Routes>
                  <Route path="/" element={<Home />} />
                  <Route path="/fight-capture" element={<FightCapture />} />
                  <Route path="/post-fight" element={<PostFightSession />} />
                  <Route path="/analytics" element={<Analytics />} />
                  <Route path="/analytics/dashboard" element={<Dashboard />} />
                  <Route path="/analytics/conflicts" element={<ConflictAnalysis />} />
                  <Route path="/analytics/triggers" element={<TriggerPhrases />} />
                  <Route path="/analytics/timeline" element={<Timeline />} />
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
      </AnalyticsProvider>
    </RelationshipProvider>
  );
}
