import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import FightCapture from './pages/FightCapture';
import PostFightSession from './pages/PostFightSession';
import Analytics from './pages/Analytics';
import Upload from './pages/Upload';
import History from './pages/History';
import Calendar from './pages/Calendar';
import Layout from './components/Layout';
export function App() {
  return <Router>
      <Routes>
        <Route path="/*" element={
          <Layout>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/fight-capture" element={<FightCapture />} />
              <Route path="/post-fight" element={<PostFightSession />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/upload" element={<Upload />} />
              <Route path="/history" element={<History />} />
              <Route path="/calendar" element={<Calendar />} />
            </Routes>
          </Layout>
        } />
      </Routes>
    </Router>;
}