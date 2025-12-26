import React from 'react';

interface Phrase {
  phrase: string;
  speaker?: string;
  usage_count: number;
  avg_emotional_intensity: number;
  escalation_rate: number;
  phrase_category: string;
}

interface Props {
  phrases: Phrase[];
}

export const TriggerPhraseTable: React.FC<Props> = ({ phrases }) => {
  return (
    <table className="w-full border-collapse">
      <thead>
        <tr className="border-b">
          <th className="text-left p-2">Phrase</th>
          <th className="text-center p-2">Used</th>
          <th className="text-center p-2">Intensity</th>
          <th className="text-center p-2">Escalates</th>
        </tr>
      </thead>
      <tbody>
        {phrases.map((phrase, idx) => (
          <tr key={idx} className="border-b hover:bg-gray-50">
            <td className="p-2">"{phrase.phrase}"</td>
            <td className="text-center p-2">{phrase.usage_count}x</td>
            <td className="text-center p-2">
              <div className="w-20 bg-gray-200 rounded h-2 inline-block">
                <div
                  className="bg-red-500 h-2 rounded"
                  style={{
                    width: `${(phrase.avg_emotional_intensity / 10) * 100}%`
                  }}
                />
              </div>
            </td>
            <td className="text-center p-2">
              {(phrase.escalation_rate * 100).toFixed(0)}%
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};
