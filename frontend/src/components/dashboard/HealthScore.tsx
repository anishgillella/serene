import React from 'react';
import { Heart, TrendingUp, TrendingDown } from 'lucide-react';

interface Props {
  data: {
    value: number;
    trend: 'up' | 'down' | 'stable';
    breakdownFactors: {
      unresolved_issues: number;
      conflict_frequency: number;
      escalation_risk: number;
      resentment_level: number;
    };
  };
}

export const HealthScore: React.FC<Props> = ({ data }) => {
  const getTrendColor = (trend: string) => {
    if (trend === 'up') return 'text-green-600';
    if (trend === 'down') return 'text-red-600';
    return 'text-gray-600';
  };

  const getHealthColor = (score: number) => {
    if (score >= 80) return 'from-green-400 to-green-600';
    if (score >= 60) return 'from-blue-400 to-blue-600';
    if (score >= 40) return 'from-yellow-400 to-yellow-600';
    return 'from-red-400 to-red-600';
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 border border-gray-100">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-bold text-gray-800">Relationship Health</h3>
        <Heart className="text-pink-500" size={24} />
      </div>

      {/* Score Circle */}
      <div className="flex items-center justify-center mb-6">
        <div className="relative w-40 h-40">
          <svg className="w-full h-full transform -rotate-90">
            <circle
              cx="80"
              cy="80"
              r="70"
              stroke="#f0f0f0"
              strokeWidth="8"
              fill="none"
            />
            <circle
              cx="80"
              cy="80"
              r="70"
              stroke="url(#gradient)"
              strokeWidth="8"
              fill="none"
              strokeDasharray={`${(data.value / 100) * 440} 440`}
              className="transition-all duration-1000"
            />
            <defs>
              <linearGradient id="gradient">
                <stop offset="0%" className={`stop-color-from-${getHealthColor(data.value).split(' ')[1]}`} />
                <stop offset="100%" className={`stop-color-to-${getHealthColor(data.value).split(' ')[2]}`} />
              </linearGradient>
            </defs>
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-5xl font-bold text-gray-800">{data.value}</span>
            <span className="text-sm text-gray-500">/ 100</span>
          </div>
        </div>
      </div>

      {/* Trend */}
      <div className="flex items-center justify-center gap-2 mb-6">
        {data.trend === 'up' && <TrendingUp className={getTrendColor(data.trend)} size={20} />}
        {data.trend === 'down' && <TrendingDown className={getTrendColor(data.trend)} size={20} />}
        <span className={`font-semibold capitalize ${getTrendColor(data.trend)}`}>
          {data.trend} Trend
        </span>
      </div>

      {/* Breakdown */}
      <div className="space-y-3 pt-4 border-t">
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600">Unresolved Issues</span>
          <div className="flex items-center gap-2">
            <div className="w-16 h-2 bg-gray-200 rounded overflow-hidden">
              <div
                className="h-full bg-red-500"
                style={{
                  width: `${Math.min(data.breakdownFactors.unresolved_issues * 100, 100)}%`
                }}
              />
            </div>
            <span className="text-xs font-bold text-gray-700 w-6">
              {(data.breakdownFactors.unresolved_issues * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
