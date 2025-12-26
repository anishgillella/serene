import React from 'react';

interface Props {
  data: {
    risk_score: number;
    interpretation: string;
    unresolved_issues: number;
    days_until_predicted_conflict: number;
    recommendations: string[];
  };
}

export const EscalationRiskCard: React.FC<Props> = ({ data }) => {
  const getColor = (score: number) => {
    if (score < 0.25) return 'text-green-600';
    if (score < 0.50) return 'text-yellow-600';
    if (score < 0.75) return 'text-orange-600';
    return 'text-red-600';
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-8">
      <h2 className="text-2xl font-bold mb-6">Escalation Risk</h2>

      <div className="flex items-center justify-between mb-6">
        <div>
          <div className={`text-6xl font-bold ${getColor(data.risk_score)}`}>
            {(data.risk_score * 100).toFixed(0)}%
          </div>
          <p className="text-2xl text-gray-600 mt-2 capitalize">
            {data.interpretation}
          </p>
        </div>

        <div className="text-right">
          <p className="text-gray-600">Next conflict likely in</p>
          <p className="text-4xl font-bold text-gray-800">
            {data.days_until_predicted_conflict} days
          </p>
        </div>
      </div>

      <div className="bg-blue-50 p-4 rounded">
        <p className="text-sm text-blue-800">
          You have <strong>{data.unresolved_issues}</strong> unresolved issues.
          Address them to reduce escalation risk.
        </p>
      </div>
    </div>
  );
};
