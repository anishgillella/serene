import React from 'react';
import { BarChart3, CheckCircle, XCircle } from 'lucide-react';

interface Props {
  data: {
    total_conflicts: number;
    resolved_conflicts: number;
    unresolved_conflicts: number;
    resolution_rate: number;
    avg_resentment: number;
    days_since_last_conflict: number;
  };
}

export const MetricsOverview: React.FC<Props> = ({ data }) => {
  return (
    <div className="bg-white rounded-lg shadow-lg p-6 border border-gray-100">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-bold text-gray-800">Quick Metrics</h3>
        <BarChart3 className="text-blue-500" size={24} />
      </div>

      <div className="space-y-4">
        {/* Total Conflicts */}
        <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
          <div>
            <p className="text-xs text-gray-600 mb-1">Total Conflicts</p>
            <p className="text-2xl font-bold text-blue-600">{data.total_conflicts}</p>
          </div>
          <BarChart3 className="text-blue-300" size={32} />
        </div>

        {/* Resolution Rate */}
        <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
          <div>
            <p className="text-xs text-gray-600 mb-1">Resolution Rate</p>
            <p className="text-2xl font-bold text-green-600">{data.resolution_rate.toFixed(0)}%</p>
          </div>
          <CheckCircle className="text-green-300" size={32} />
        </div>

        {/* Avg Resentment */}
        <div className="flex justify-between items-center p-3 bg-orange-50 rounded-lg">
          <div>
            <p className="text-xs text-gray-600 mb-1">Avg Resentment</p>
            <p className="text-2xl font-bold text-orange-600">{data.avg_resentment.toFixed(1)}/10</p>
          </div>
          <div className="flex gap-1">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className={`w-1.5 h-6 rounded ${
                  i < Math.round(data.avg_resentment / 2)
                    ? 'bg-orange-500'
                    : 'bg-orange-200'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Days Since Last */}
        <div className="flex justify-between items-center p-3 bg-purple-50 rounded-lg">
          <div>
            <p className="text-xs text-gray-600 mb-1">Days Since Last</p>
            <p className="text-2xl font-bold text-purple-600">{data.days_since_last_conflict}</p>
          </div>
          <p className="text-sm text-gray-500">days ago</p>
        </div>
      </div>
    </div>
  );
};
