import React from 'react';

interface Need {
  need: string;
  conflict_count: number;
  percentage_of_conflicts: number;
}

interface Props {
  needs?: Need[];
}

export const ChronicNeedsList: React.FC<Props> = ({ needs = [] }) => {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-bold mb-4">Chronic Unmet Needs</h2>
      <div className="space-y-4">
        {needs.map((need, idx) => (
          <div key={idx} className="p-4 border-l-4 border-purple-500">
            <p className="font-bold capitalize">{need.need.replace(/_/g, ' ')}</p>
            <p className="text-sm text-gray-600">
              Appears in {need.conflict_count} conflicts ({need.percentage_of_conflicts.toFixed(0)}%)
            </p>
            <div className="w-full bg-gray-200 rounded h-2 mt-2">
              <div
                className="bg-purple-500 h-2 rounded"
                style={{ width: `${need.percentage_of_conflicts}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
