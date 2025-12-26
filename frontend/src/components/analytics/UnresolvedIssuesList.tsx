import React from 'react';

interface Issue {
  conflict_id: string;
  topic: string;
  days_unresolved: number;
  resentment_level: number;
}

interface Props {
  issues?: Issue[];
}

export const UnresolvedIssuesList: React.FC<Props> = ({ issues = [] }) => {
  if (!issues.length) {
    return <div className="p-4 bg-green-50 rounded">All issues resolved!</div>;
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-bold mb-4">Unresolved Issues</h2>
      <div className="space-y-3">
        {issues.map((issue, idx) => (
          <div key={idx} className="p-3 bg-gray-50 rounded border-l-4 border-yellow-500">
            <p className="font-bold">{issue.topic}</p>
            <p className="text-sm text-gray-600">
              Unresolved for {issue.days_unresolved} days
            </p>
            <p className="text-sm">Resentment: {issue.resentment_level}/10</p>
          </div>
        ))}
      </div>
    </div>
  );
};
