import React from 'react';
import { motion } from 'framer-motion';
import { Clock, TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface RecoveryTimeProps {
  data: {
    has_data: boolean;
    per_conflict: Array<{
      conflict_id: string;
      ended_at: string;
      next_positive_date: string | null;
      recovery_days: number | null;
    }>;
    average_recovery_days: number | null;
    trend: string;
  } | null;
  delay?: number;
}

export const RecoveryTimeCard: React.FC<RecoveryTimeProps> = ({
  data,
  delay = 0,
}) => {
  if (!data?.has_data || data.average_recovery_days === null) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay }}
        className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-5 shadow-subtle"
      >
        <div className="flex items-center gap-2 mb-2">
          <div className="p-2 rounded-xl bg-blue-50">
            <Clock size={18} className="text-blue-500" />
          </div>
          <h3 className="text-base font-semibold text-warmGray-700">Recovery Time</h3>
        </div>
        <p className="text-sm text-warmGray-400">
          Need daily check-ins after conflicts to measure recovery.
        </p>
      </motion.div>
    );
  }

  const TrendIcon = data.trend === 'improving' ? TrendingDown :
                    data.trend === 'worsening' ? TrendingUp : Minus;
  const trendColor = data.trend === 'improving' ? 'text-emerald-500' :
                     data.trend === 'worsening' ? 'text-red-500' : 'text-warmGray-400';
  const trendLabel = data.trend === 'improving' ? 'Getting faster' :
                     data.trend === 'worsening' ? 'Getting slower' : 'Stable';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-5 shadow-subtle hover:shadow-lifted transition-shadow"
    >
      <div className="flex items-center gap-2 mb-3">
        <div className="p-2 rounded-xl bg-blue-50">
          <Clock size={18} className="text-blue-500" />
        </div>
        <h3 className="text-base font-semibold text-warmGray-700">Recovery Time</h3>
      </div>

      <div className="flex items-baseline gap-2 mb-2">
        <motion.span
          className="text-3xl font-bold text-warmGray-800"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: delay + 0.2 }}
        >
          {data.average_recovery_days}
        </motion.span>
        <span className="text-sm text-warmGray-500">days avg</span>
      </div>

      <div className={`flex items-center gap-1 text-sm ${trendColor}`}>
        <TrendIcon size={14} />
        <span className="font-medium">{trendLabel}</span>
      </div>

      <p className="text-xs text-warmGray-400 mt-2">
        Average days from conflict end to first positive check-in
      </p>
    </motion.div>
  );
};

export default RecoveryTimeCard;
