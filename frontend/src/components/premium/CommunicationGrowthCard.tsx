import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface CommunicationGrowthProps {
  data: {
    has_data: boolean;
    monthly_data: Array<{
      month: string;
      conflicts_count: number;
      i_statement_ratio: number;
      interruptions_per_conflict: number;
      active_listening_per_conflict: number;
      repair_success_rate: number;
    }>;
    growth_percentages: Array<{
      month: string;
      i_statement_ratio: number;
      interruptions_per_conflict: number;
      active_listening_per_conflict: number;
      repair_success_rate: number;
    }>;
  } | null;
  delay?: number;
}

const GrowthBadge: React.FC<{ value: number; inverted?: boolean }> = ({ value, inverted = false }) => {
  const isGood = inverted ? value < 0 : value > 0;
  const isNeutral = Math.abs(value) < 1;

  if (isNeutral) return <span className="text-xs text-warmGray-400 flex items-center gap-0.5"><Minus size={12} /> 0%</span>;

  return (
    <span className={`text-xs font-medium flex items-center gap-0.5 ${isGood ? 'text-emerald-600' : 'text-red-600'}`}>
      {isGood ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
      {value > 0 ? '+' : ''}{value}%
    </span>
  );
};

export const CommunicationGrowthCard: React.FC<CommunicationGrowthProps> = ({
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
        <h3 className="text-base font-semibold text-warmGray-700 mb-2">Communication Growth</h3>
        <p className="text-sm text-warmGray-400">Need at least 2 months of data.</p>
      </motion.div>
    );
  }

  const { monthly_data, growth_percentages } = data;
  const latestGrowth = growth_percentages[growth_percentages.length - 1];

  const metrics = [
    { label: 'I-Statement Ratio', key: 'i_statement_ratio', suffix: '%', inverted: false },
    { label: 'Interruptions/Fight', key: 'interruptions_per_conflict', suffix: '', inverted: true },
    { label: 'Active Listening/Fight', key: 'active_listening_per_conflict', suffix: '', inverted: false },
    { label: 'Repair Success', key: 'repair_success_rate', suffix: '%', inverted: false },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-5 shadow-subtle"
    >
      <h3 className="text-base font-semibold text-warmGray-700 mb-4">Communication Growth</h3>

      <div className="grid grid-cols-2 gap-3">
        {metrics.map((metric, idx) => {
          const latest = monthly_data[monthly_data.length - 1];
          const value = latest?.[metric.key as keyof typeof latest] ?? 0;
          const growth = latestGrowth?.[metric.key as keyof typeof latestGrowth] as number ?? 0;

          return (
            <motion.div
              key={metric.key}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: delay + 0.1 * idx }}
              className="p-3 rounded-xl bg-warmGray-50/50"
            >
              <p className="text-xs text-warmGray-500 mb-1">{metric.label}</p>
              <div className="flex items-baseline justify-between">
                <span className="text-lg font-bold text-warmGray-800">
                  {typeof value === 'number' ? value.toFixed(1) : value}{metric.suffix}
                </span>
                <GrowthBadge value={growth} inverted={metric.inverted} />
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Monthly trend bars */}
      <div className="mt-4">
        <p className="text-xs text-warmGray-400 mb-2">Monthly trend (I-statement ratio)</p>
        <div className="flex items-end gap-1 h-16">
          {monthly_data.map((m, idx) => {
            const maxRatio = Math.max(...monthly_data.map(d => d.i_statement_ratio), 1);
            const height = (m.i_statement_ratio / maxRatio) * 100;

            return (
              <motion.div
                key={idx}
                className="flex-1 bg-rose-300 rounded-t-sm hover:bg-rose-400 transition-colors"
                initial={{ height: 0 }}
                animate={{ height: `${Math.max(height, 4)}%` }}
                transition={{ duration: 0.4, delay: delay + 0.05 * idx }}
                title={`${new Date(m.month).toLocaleDateString('en-US', { month: 'short' })}: ${m.i_statement_ratio}%`}
              />
            );
          })}
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-[10px] text-warmGray-400">
            {monthly_data[0] ? new Date(monthly_data[0].month).toLocaleDateString('en-US', { month: 'short' }) : ''}
          </span>
          <span className="text-[10px] text-warmGray-400">
            {monthly_data[monthly_data.length - 1] ? new Date(monthly_data[monthly_data.length - 1].month).toLocaleDateString('en-US', { month: 'short' }) : ''}
          </span>
        </div>
      </div>
    </motion.div>
  );
};

export default CommunicationGrowthCard;
