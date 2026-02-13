import React from 'react';
import { motion } from 'framer-motion';
import { TrendingDown, TrendingUp, Minus } from 'lucide-react';

interface SentimentShiftProps {
  data: {
    has_data: boolean;
    per_conflict: Array<{
      conflict_id: string;
      started_at: string;
      start_intensity: number;
      end_intensity: number;
      shift_score: number;
    }>;
    aggregate: {
      avg_shift: number;
      trend_direction: string;
      total_analyzed: number;
    };
  } | null;
  compact?: boolean;
  delay?: number;
}

export const SentimentShiftCard: React.FC<SentimentShiftProps> = ({
  data,
  compact = false,
  delay = 0,
}) => {
  if (!data?.has_data) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay }}
        className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-5 shadow-subtle"
      >
        <h3 className="text-base font-semibold text-warmGray-700 mb-2">Sentiment Shift</h3>
        <p className="text-sm text-warmGray-400">No emotional data available yet.</p>
      </motion.div>
    );
  }

  const { per_conflict, aggregate } = data;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-5 shadow-subtle"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-semibold text-warmGray-700">Sentiment Shift</h3>
        <div className="flex items-center gap-1.5 text-sm">
          {aggregate.trend_direction === 'improving' ? (
            <TrendingDown size={16} className="text-emerald-500" />
          ) : aggregate.trend_direction === 'declining' ? (
            <TrendingUp size={16} className="text-red-500" />
          ) : (
            <Minus size={16} className="text-warmGray-400" />
          )}
          <span className={
            aggregate.trend_direction === 'improving' ? 'text-emerald-600 font-medium' :
            aggregate.trend_direction === 'declining' ? 'text-red-600 font-medium' :
            'text-warmGray-500'
          }>
            {aggregate.avg_shift > 0 ? '+' : ''}{aggregate.avg_shift} avg
          </span>
        </div>
      </div>

      <p className="text-xs text-warmGray-400 mb-3">
        {aggregate.total_analyzed} conflicts analyzed. Positive = de-escalation.
      </p>

      {!compact && (
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {per_conflict.map((c, idx) => {
            const barWidth = Math.min(Math.abs(c.shift_score) * 10, 100);
            const isPositive = c.shift_score > 0;

            return (
              <motion.div
                key={c.conflict_id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: delay + 0.05 * idx }}
                className="flex items-center gap-3"
              >
                <span className="text-xs text-warmGray-400 w-16 flex-shrink-0 truncate">
                  {new Date(c.started_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                </span>
                <div className="flex-1 flex items-center gap-2">
                  <div className="flex-1 h-5 bg-warmGray-100 rounded-full overflow-hidden relative">
                    <motion.div
                      className={`h-full rounded-full ${isPositive ? 'bg-emerald-400' : 'bg-red-400'}`}
                      initial={{ width: 0 }}
                      animate={{ width: `${barWidth}%` }}
                      transition={{ duration: 0.6, delay: delay + 0.05 * idx }}
                    />
                  </div>
                  <span className={`text-xs font-medium w-10 text-right ${isPositive ? 'text-emerald-600' : 'text-red-600'}`}>
                    {c.shift_score > 0 ? '+' : ''}{c.shift_score}
                  </span>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </motion.div>
  );
};

export default SentimentShiftCard;
