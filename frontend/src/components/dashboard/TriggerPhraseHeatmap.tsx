import React from 'react';
import { Flame, AlertCircle } from 'lucide-react';

interface Props {
  data: {
    most_impactful: Array<{
      phrase: string;
      usage_count: number;
      escalation_rate: number;
    }>;
  };
}

export const TriggerPhraseHeatmap: React.FC<Props> = ({ data }) => {
  const phrases = data.most_impactful.slice(0, 5);

  if (phrases.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6 border border-gray-100">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-bold text-gray-800">Trigger Phrases</h3>
          <Flame className="text-orange-500" size={24} />
        </div>
        <p className="text-gray-500 text-center py-8">No trigger phrases identified yet</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 border border-gray-100">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-bold text-gray-800">Trigger Phrases</h3>
        <Flame className="text-orange-500" size={24} />
      </div>

      <div className="space-y-3">
        {phrases.map((phrase, idx) => (
          <div key={idx} className="p-3 bg-gray-50 rounded-lg border border-gray-200">
            <div className="flex items-start justify-between mb-2">
              <p className="font-semibold text-gray-800 text-sm flex-1">"{phrase.phrase}"</p>
              <span className="text-xs font-bold bg-orange-100 text-orange-700 px-2 py-1 rounded">
                {(phrase.escalation_rate * 100).toFixed(0)}%
              </span>
            </div>
            <div className="w-full h-2 bg-gray-200 rounded overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-orange-400 to-red-600"
                style={{ width: `${phrase.escalation_rate * 100}%` }}
              />
            </div>
            <p className="text-xs text-gray-600 mt-2">Used {phrase.usage_count}x</p>
          </div>
        ))}
      </div>

      {phrases.length > 0 && (
        <div className="mt-4 p-3 bg-orange-50 border border-orange-200 rounded-lg">
          <div className="flex gap-2 items-start">
            <AlertCircle size={16} className="text-orange-600 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-orange-700">
              Be aware of these phrases during conflicts - they often escalate tension
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
