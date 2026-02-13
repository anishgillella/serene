import React from 'react';
import { motion } from 'framer-motion';
import { Calendar } from 'lucide-react';

interface FightFrequencyProps {
  data: {
    has_data: boolean;
    period: string;
    periods: Array<{
      period_start: string;
      fight_count: number;
      resolved_count: number;
      avg_duration_minutes: number;
    }>;
    average_days_between: number | null;
  } | null;
  delay?: number;
}

export const FightFrequencyChart: React.FC<FightFrequencyProps> = ({
  data,
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
        <h3 className="text-base font-semibold text-warmGray-700 mb-2">Fight Frequency</h3>
        <p className="text-sm text-warmGray-400">No conflict data available yet.</p>
      </motion.div>
    );
  }

  const { periods, average_days_between, period: periodType } = data;
  const maxCount = Math.max(...periods.map(p => p.fight_count), 1);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-5 shadow-subtle"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-semibold text-warmGray-700">Fight Frequency</h3>
        {average_days_between !== null && (
          <div className="flex items-center gap-1.5 text-sm text-warmGray-500">
            <Calendar size={14} />
            <span>{average_days_between} days avg between</span>
          </div>
        )}
      </div>

      {/* Bar chart */}
      <div className="flex items-end gap-1.5 h-32 mb-2">
        {periods.map((p, idx) => {
          const totalHeight = (p.fight_count / maxCount) * 100;

          return (
            <div key={idx} className="flex-1 flex flex-col items-center gap-0.5 h-full justify-end">
              <span className="text-[10px] text-warmGray-500 font-medium">{p.fight_count}</span>
              <div className="relative w-full flex flex-col items-center justify-end flex-1">
                {/* Total bar (unresolved portion shown in amber) */}
                <motion.div
                  className="w-full rounded-t-sm bg-amber-300 relative overflow-hidden"
                  initial={{ height: 0 }}
                  animate={{ height: `${Math.max(totalHeight, 3)}%` }}
                  transition={{ duration: 0.5, delay: delay + 0.03 * idx }}
                >
                  {/* Resolved overlay */}
                  <motion.div
                    className="absolute bottom-0 left-0 right-0 bg-emerald-400 rounded-t-sm"
                    initial={{ height: 0 }}
                    animate={{ height: `${p.fight_count > 0 ? (p.resolved_count / p.fight_count) * 100 : 0}%` }}
                    transition={{ duration: 0.5, delay: delay + 0.03 * idx + 0.2 }}
                  />
                </motion.div>
              </div>
            </div>
          );
        })}
      </div>

      {/* X-axis labels */}
      <div className="flex justify-between">
        <span className="text-[10px] text-warmGray-400">
          {periods[0] ? new Date(periods[0].period_start).toLocaleDateString('en-US', {
            month: 'short', day: periodType === 'weekly' ? 'numeric' : undefined
          }) : ''}
        </span>
        <span className="text-[10px] text-warmGray-400">
          {periods[periods.length - 1] ? new Date(periods[periods.length - 1].period_start).toLocaleDateString('en-US', {
            month: 'short', day: periodType === 'weekly' ? 'numeric' : undefined
          }) : ''}
        </span>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-3 text-xs text-warmGray-500">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-sm bg-emerald-400" />
          <span>Resolved</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-sm bg-amber-300" />
          <span>Unresolved</span>
        </div>
      </div>
    </motion.div>
  );
};

export default FightFrequencyChart;
