import React from 'react';
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, LineChart, Line } from 'recharts';
import AnalyticsCard from '../components/AnalyticsCard';
import VoiceButton from '../components/VoiceButton';
const Analytics = () => {
  const conflictData = [{
    name: 'Week 1',
    conflicts: 3
  }, {
    name: 'Week 2',
    conflicts: 2
  }, {
    name: 'Week 3',
    conflicts: 4
  }, {
    name: 'Week 4',
    conflicts: 1
  }];
  const intimacyData = [{
    name: 'Week 1',
    value: 2
  }, {
    name: 'Week 2',
    value: 3
  }, {
    name: 'Week 3',
    value: 1
  }, {
    name: 'Week 4',
    value: 4
  }];
  return <div className="py-4">
      <div className="text-center mb-6">
        <h2 className="text-xl font-semibold text-gray-800">
          Analytics Dashboard
        </h2>
        <p className="text-sm text-gray-600">
          Track your relationship progress
        </p>
      </div>
      <AnalyticsCard title="Conflict Frequency" value="" color="bg-lavender/70">
        <ResponsiveContainer width="100%" height={120}>
          <BarChart data={conflictData}>
            <XAxis dataKey="name" tick={{
            fontSize: 10
          }} />
            <YAxis tick={{
            fontSize: 10
          }} />
            <Bar dataKey="conflicts" fill="#f9a8d4" />
          </BarChart>
        </ResponsiveContainer>
      </AnalyticsCard>
      <AnalyticsCard title="Intimacy Frequency Trend" value="" color="bg-mint/70">
        <ResponsiveContainer width="100%" height={120}>
          <LineChart data={intimacyData}>
            <XAxis dataKey="name" tick={{
            fontSize: 10
          }} />
            <YAxis tick={{
            fontSize: 10
          }} />
            <Line type="monotone" dataKey="value" stroke="#60a5fa" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </AnalyticsCard>
      <div className="grid grid-cols-2 gap-3">
        <AnalyticsCard title="Fights This Month" value="10" color="bg-blush/70" />
        <AnalyticsCard title="Intimacy Events" value="12" color="bg-white/70" />
      </div>
      <div className="mt-4">
        <AnalyticsCard title="Hot Zones & Predicted Tension" value="" color="bg-white/70">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>Monday</span>
            <span>Wednesday</span>
            <span>Friday</span>
            <span>Sunday</span>
          </div>
          <div className="w-full h-4 bg-gray-100 rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-green-200 via-rose-300 to-green-200"></div>
          </div>
          <div className="text-xs text-center mt-1 text-gray-500">
            Higher tension predicted on Wednesday evening
          </div>
        </AnalyticsCard>
      </div>
      <div className="flex justify-center mt-6">
        <VoiceButton size="md" />
      </div>
      <p className="text-center text-xs text-gray-500 mt-2">
        Ask: "Give me my weekly summary"
      </p>
    </div>;
};
export default Analytics;