import React from 'react';
import { Sparkles, TrendingUp, AlertCircle } from 'lucide-react';

interface Props {
  insights: string[];
  metrics: any;
  escalationRisk: any;
}

export const InsightsPanel: React.FC<Props> = ({ insights, metrics, escalationRisk }) => {
  const generateInsights = () => {
    const customInsights = [];

    if (metrics.total_conflicts === 0) {
      customInsights.push('✨ No conflicts recorded yet - great start to your relationship!');
    } else if (metrics.resolution_rate >= 80) {
      customInsights.push('🎉 Excellent! You resolve conflicts at a very high rate');
    } else if (metrics.resolution_rate >= 60) {
      customInsights.push('📈 Good progress! Your resolution rate is improving');
    } else {
      customInsights.push('📌 Try to focus on resolving pending conflicts');
    }

    if (metrics.avg_resentment >= 8) {
      customInsights.push('💔 Resentment is building - consider having a validating conversation');
    } else if (metrics.avg_resentment <= 3) {
      customInsights.push('💚 Low resentment levels indicate good emotional health');
    }

    if (escalationRisk.interpretation === 'critical') {
      customInsights.push('⚠️ Critical escalation risk - strongly consider mediation support');
    } else if (escalationRisk.interpretation === 'high') {
      customInsights.push('📌 High escalation risk - schedule a conversation this week');
    }

    if (metrics.days_since_last_conflict > 30) {
      customInsights.push('✅ Over a month without conflict - you\'re doing great!');
    }

    return customInsights.length > 0 ? customInsights : insights;
  };

  const allInsights = generateInsights();

  return (
    <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg shadow-lg p-8 border border-purple-200">
      <div className="flex items-center gap-3 mb-6">
        <Sparkles className="text-purple-600" size={28} />
        <h2 className="text-2xl font-bold text-gray-800">Key Insights</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {allInsights.map((insight, idx) => {
          const getInsightColor = (insight: string) => {
            if (insight.includes('⚠️') || insight.includes('Critical')) return 'bg-red-50 border-red-200';
            if (insight.includes('📌')) return 'bg-orange-50 border-orange-200';
            if (insight.includes('💔')) return 'bg-pink-50 border-pink-200';
            if (insight.includes('✅') || insight.includes('✨') || insight.includes('🎉')) return 'bg-green-50 border-green-200';
            return 'bg-blue-50 border-blue-200';
          };

          return (
            <div
              key={idx}
              className={`p-4 rounded-lg border flex gap-3 items-start ${getInsightColor(insight)}`}
            >
              <span className="text-xl flex-shrink-0">
                {insight.match(/^[\p{Emoji}]/u)?.[0] || '💭'}
              </span>
              <p className="text-sm text-gray-700 font-medium">{insight.replace(/^[\p{Emoji}]\s+/, '')}</p>
            </div>
          );
        })}
      </div>

      {/* Tips Section */}
      <div className="mt-6 pt-6 border-t border-purple-200">
        <h3 className="font-bold text-gray-800 mb-3">💡 Tips for Better Communication</h3>
        <ul className="space-y-2 text-sm text-gray-700">
          <li>• Be aware of trigger phrases and try to avoid them during conflicts</li>
          <li>• Address chronic unmet needs proactively rather than waiting for them to resurface</li>
          <li>• Take breaks when escalation risk is high</li>
          <li>• Use Luna's mediation support when tensions rise</li>
        </ul>
      </div>
    </div>
  );
};
