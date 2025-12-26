import React from 'react';
import { TrendingUp, BarChart2 } from 'lucide-react';

interface Props {
  data: any;
}

export const ConflictTrends: React.FC<Props> = ({ data }) => {
  const conflicts = data.metrics;
  const resolution_rate = conflicts.resolution_rate;

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 border border-gray-100">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-bold text-gray-800">Conflict Trends</h3>
        <TrendingUp className="text-blue-500" size={24} />
      </div>

      {/* Simple bar chart simulation */}
      <div className="space-y-4">
        <div>
          <div className="flex justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Resolved</span>
            <span className="text-sm font-bold text-green-600">{conflicts.resolved_conflicts}</span>
          </div>
          <div className="w-full h-8 bg-gray-200 rounded-lg overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-green-400 to-green-600 transition-all duration-500"
              style={{
                width: `${
                  conflicts.total_conflicts > 0
                    ? (conflicts.resolved_conflicts / conflicts.total_conflicts) * 100
                    : 0
                }%`
              }}
            />
          </div>
        </div>

        <div>
          <div className="flex justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Unresolved</span>
            <span className="text-sm font-bold text-red-600">{conflicts.unresolved_conflicts}</span>
          </div>
          <div className="w-full h-8 bg-gray-200 rounded-lg overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-red-400 to-red-600 transition-all duration-500"
              style={{
                width: `${
                  conflicts.total_conflicts > 0
                    ? (conflicts.unresolved_conflicts / conflicts.total_conflicts) * 100
                    : 0
                }%`
              }}
            />
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 pt-4 border-t mt-4">
          <div className="text-center">
            <p className="text-xs text-gray-600 mb-1">Total</p>
            <p className="text-2xl font-bold text-gray-800">{conflicts.total_conflicts}</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-600 mb-1">Resolution Rate</p>
            <p className="text-2xl font-bold text-blue-600">{resolution_rate.toFixed(0)}%</p>
          </div>
        </div>
      </div>
    </div>
  );
};
