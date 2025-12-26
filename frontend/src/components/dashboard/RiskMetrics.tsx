import React from 'react';
import { AlertTriangle, Clock, Zap } from 'lucide-react';

interface Props {
  data: {
    risk_score: number;
    interpretation: string;
    unresolved_issues: number;
    days_until_predicted_conflict: number;
  };
}

export const RiskMetrics: React.FC<Props> = ({ data }) => {
  const getRiskColor = (interpretation: string) => {
    switch (interpretation) {
      case 'low':
        return 'bg-green-50 border-green-200 text-green-700';
      case 'medium':
        return 'bg-yellow-50 border-yellow-200 text-yellow-700';
      case 'high':
        return 'bg-orange-50 border-orange-200 text-orange-700';
      case 'critical':
        return 'bg-red-50 border-red-200 text-red-700';
      default:
        return 'bg-gray-50 border-gray-200 text-gray-700';
    }
  };

  const getRiskBgColor = (interpretation: string) => {
    switch (interpretation) {
      case 'low':
        return 'bg-green-500';
      case 'medium':
        return 'bg-yellow-500';
      case 'high':
        return 'bg-orange-500';
      case 'critical':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 border border-gray-100">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-bold text-gray-800">Escalation Risk</h3>
        <AlertTriangle className="text-orange-500" size={24} />
      </div>

      {/* Risk Score */}
      <div className={`rounded-lg p-4 mb-4 border ${getRiskColor(data.interpretation)}`}>
        <div className="flex items-end gap-4">
          <div>
            <p className="text-sm opacity-75 mb-1">Current Risk</p>
            <p className="text-4xl font-bold">{(data.risk_score * 100).toFixed(0)}%</p>
          </div>
          <div className="flex-1 h-16 bg-gray-200 rounded overflow-hidden">
            <div
              className={`h-full ${getRiskBgColor(data.interpretation)} transition-all duration-500`}
              style={{ width: `${data.risk_score * 100}%` }}
            />
          </div>
        </div>
        <p className="text-sm mt-3 font-semibold capitalize">{data.interpretation} Risk</p>
      </div>

      {/* Metrics */}
      <div className="space-y-3">
        {/* Unresolved Issues */}
        <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
          <div className="p-2 bg-red-100 rounded-lg">
            <AlertTriangle size={18} className="text-red-600" />
          </div>
          <div className="flex-1">
            <p className="text-xs text-gray-600">Unresolved Issues</p>
            <p className="font-bold text-lg">{data.unresolved_issues}</p>
          </div>
        </div>

        {/* Days Until Conflict */}
        <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Clock size={18} className="text-blue-600" />
          </div>
          <div className="flex-1">
            <p className="text-xs text-gray-600">Predicted Days Until</p>
            <p className="font-bold text-lg">{data.days_until_predicted_conflict} days</p>
          </div>
        </div>

        {/* Risk Level Indicator */}
        <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
          <div className="p-2 bg-purple-100 rounded-lg">
            <Zap size={18} className="text-purple-600" />
          </div>
          <div className="flex-1">
            <p className="text-xs text-gray-600">Risk Level</p>
            <p className="font-bold text-lg capitalize">{data.interpretation}</p>
          </div>
        </div>
      </div>
    </div>
  );
};
