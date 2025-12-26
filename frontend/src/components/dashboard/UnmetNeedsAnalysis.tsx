import React from 'react';
import { Heart, AlertTriangle } from 'lucide-react';

interface Props {
  data: Array<{
    need: string;
    conflict_count: number;
    percentage_of_conflicts: number;
  }>;
}

export const UnmetNeedsAnalysis: React.FC<Props> = ({ data }) => {
  if (data.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6 border border-gray-100">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-bold text-gray-800">Unmet Needs</h3>
          <Heart className="text-pink-500" size={24} />
        </div>
        <p className="text-gray-500 text-center py-8">No chronic needs identified</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 border border-gray-100">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-bold text-gray-800">Chronic Unmet Needs</h3>
        <Heart className="text-pink-500" size={24} />
      </div>

      <div className="space-y-4">
        {data.map((need, idx) => (
          <div key={idx} className="p-4 bg-gradient-to-r from-pink-50 to-red-50 rounded-lg border border-pink-200">
            <div className="flex items-start justify-between mb-2">
              <p className="font-bold text-gray-800 capitalize">
                {need.need.replace(/_/g, ' ')}
              </p>
              <span className="text-xs font-bold bg-pink-200 text-pink-700 px-2 py-1 rounded">
                {need.conflict_count}x
              </span>
            </div>
            <div className="w-full h-3 bg-pink-200 rounded-full overflow-hidden mb-2">
              <div
                className="h-full bg-gradient-to-r from-pink-400 to-red-500"
                style={{ width: `${need.percentage_of_conflicts}%` }}
              />
            </div>
            <p className="text-xs text-gray-600">
              Appears in {need.percentage_of_conflicts.toFixed(0)}% of conflicts
            </p>
          </div>
        ))}
      </div>

      {data.length > 0 && (
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex gap-2 items-start">
            <AlertTriangle size={16} className="text-blue-600 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-blue-700">
              These core needs keep appearing in conflicts. Addressing them proactively can reduce tension.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
