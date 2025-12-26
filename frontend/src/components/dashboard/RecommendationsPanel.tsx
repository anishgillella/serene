import React from 'react';
import { Lightbulb, CheckCircle } from 'lucide-react';

interface Props {
  data: {
    recommendations: string[];
    interpretation: string;
  };
}

export const RecommendationsPanel: React.FC<Props> = ({ data }) => {
  const getRecommendationColor = (rec: string) => {
    if (rec.includes('mediation') || rec.includes('urgent')) return 'bg-red-50 border-red-200';
    if (rec.includes('proactive') || rec.includes('week')) return 'bg-orange-50 border-orange-200';
    if (rec.includes('monitoring')) return 'bg-yellow-50 border-yellow-200';
    return 'bg-blue-50 border-blue-200';
  };

  const getIcon = (rec: string) => {
    if (rec.includes('Luna')) return '🤖';
    if (rec.includes('issue')) return '📋';
    if (rec.includes('resentment')) return '💔';
    if (rec.includes('recur')) return '⏰';
    return '✅';
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 border border-gray-100">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-bold text-gray-800">Recommended Actions</h3>
        <Lightbulb className="text-yellow-500" size={24} />
      </div>

      {/* Risk Level Header */}
      <div className="mb-4 p-3 bg-gradient-to-r from-purple-100 to-pink-100 rounded-lg border border-purple-200">
        <p className="text-xs text-gray-600 mb-1">Current Risk Level</p>
        <p className="text-lg font-bold text-gray-800 capitalize">{data.interpretation}</p>
      </div>

      {/* Recommendations */}
      <div className="space-y-3">
        {data.recommendations.length > 0 ? (
          data.recommendations.map((rec, idx) => (
            <div
              key={idx}
              className={`p-3 rounded-lg border flex gap-3 items-start ${getRecommendationColor(rec)}`}
            >
              <span className="text-lg flex-shrink-0">{getIcon(rec)}</span>
              <p className="text-sm text-gray-800 font-medium">{rec}</p>
            </div>
          ))
        ) : (
          <p className="text-gray-500 text-center py-6">No specific recommendations at this time</p>
        )}
      </div>

      {/* General guidance */}
      <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
        <div className="flex gap-2 items-start">
          <CheckCircle size={16} className="text-green-600 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-green-700">
            Luna can provide personalized guidance based on your relationship patterns
          </p>
        </div>
      </div>
    </div>
  );
};
