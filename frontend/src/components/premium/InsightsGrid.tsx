import React from 'react';
import { motion } from 'framer-motion';
import {
  MessageCircle,
  Clock,
  Target,
  TrendingUp,
  Heart,
  AlertCircle,
  CheckCircle,
  XCircle
} from 'lucide-react';

interface InsightsGridProps {
  insights: string[];
  metrics: {
    total_conflicts: number;
    resolved_conflicts: number;
    unresolved_conflicts: number;
    resolution_rate: number;
    avg_resentment: number;
    days_since_last_conflict: number;
  };
  delay?: number;
}

export const InsightsGrid: React.FC<InsightsGridProps> = ({
  insights,
  metrics,
  delay = 0,
}) => {
  const getResolutionStatus = () => {
    if (metrics.resolution_rate >= 70) return { color: 'emerald', icon: <CheckCircle size={18} /> };
    if (metrics.resolution_rate >= 40) return { color: 'amber', icon: <AlertCircle size={18} /> };
    return { color: 'rose', icon: <XCircle size={18} /> };
  };

  const status = getResolutionStatus();

  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08,
        delayChildren: delay,
      },
    },
  };

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 },
  };

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="grid grid-cols-2 lg:grid-cols-4 gap-4"
    >
      {/* Total Conflicts */}
      <motion.div
        variants={item}
        whileHover={{ y: -2, scale: 1.02 }}
        className="bg-white/60 backdrop-blur-lg rounded-2xl p-4 border border-white/40 shadow-subtle"
      >
        <div className="flex items-center gap-2 mb-2">
          <div className="p-1.5 rounded-lg bg-rose-50">
            <MessageCircle size={14} className="text-rose-500" />
          </div>
          <span className="text-xs font-medium text-warmGray-500">Total Conflicts</span>
        </div>
        <p className="text-2xl font-semibold text-warmGray-800">{metrics.total_conflicts}</p>
      </motion.div>

      {/* Resolved */}
      <motion.div
        variants={item}
        whileHover={{ y: -2, scale: 1.02 }}
        className="bg-white/60 backdrop-blur-lg rounded-2xl p-4 border border-white/40 shadow-subtle"
      >
        <div className="flex items-center gap-2 mb-2">
          <div className="p-1.5 rounded-lg bg-emerald-50">
            <CheckCircle size={14} className="text-emerald-500" />
          </div>
          <span className="text-xs font-medium text-warmGray-500">Resolved</span>
        </div>
        <p className="text-2xl font-semibold text-warmGray-800">{metrics.resolved_conflicts}</p>
      </motion.div>

      {/* Resolution Rate */}
      <motion.div
        variants={item}
        whileHover={{ y: -2, scale: 1.02 }}
        className="bg-white/60 backdrop-blur-lg rounded-2xl p-4 border border-white/40 shadow-subtle"
      >
        <div className="flex items-center gap-2 mb-2">
          <div className={`p-1.5 rounded-lg bg-${status.color}-50`}>
            <span className={`text-${status.color}-500`}>{status.icon}</span>
          </div>
          <span className="text-xs font-medium text-warmGray-500">Resolution Rate</span>
        </div>
        <div className="flex items-baseline gap-1">
          <p className="text-2xl font-semibold text-warmGray-800">{Math.round(metrics.resolution_rate)}</p>
          <span className="text-sm text-warmGray-400">%</span>
        </div>
        {/* Mini progress bar */}
        <div className="mt-2 h-1.5 bg-warmGray-100 rounded-full overflow-hidden">
          <motion.div
            className={`h-full bg-${status.color}-500 rounded-full`}
            initial={{ width: 0 }}
            animate={{ width: `${metrics.resolution_rate}%` }}
            transition={{ duration: 1, delay: delay + 0.3, ease: "easeOut" }}
          />
        </div>
      </motion.div>

      {/* Days Since Last */}
      <motion.div
        variants={item}
        whileHover={{ y: -2, scale: 1.02 }}
        className="bg-white/60 backdrop-blur-lg rounded-2xl p-4 border border-white/40 shadow-subtle"
      >
        <div className="flex items-center gap-2 mb-2">
          <div className="p-1.5 rounded-lg bg-blue-50">
            <Clock size={14} className="text-blue-500" />
          </div>
          <span className="text-xs font-medium text-warmGray-500">Days Since Last</span>
        </div>
        <div className="flex items-baseline gap-1">
          <p className="text-2xl font-semibold text-warmGray-800">{metrics.days_since_last_conflict}</p>
          <span className="text-sm text-warmGray-400">days</span>
        </div>
      </motion.div>

      {/* Insights text cards - full width */}
      {insights.length > 0 && (
        <motion.div
          variants={item}
          className="col-span-2 lg:col-span-4 bg-gradient-to-r from-lavender-100/50 to-peach-100/50 backdrop-blur-lg rounded-2xl p-5 border border-white/40"
        >
          <div className="flex items-center gap-2 mb-3">
            <Target size={16} className="text-purple-500" />
            <span className="text-sm font-medium text-warmGray-700">Key Insights</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {insights.slice(0, 4).map((insight, idx) => (
              <motion.p
                key={idx}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: delay + 0.4 + idx * 0.1 }}
                className="text-sm text-warmGray-600 flex items-center gap-2"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
                {insight}
              </motion.p>
            ))}
          </div>
        </motion.div>
      )}
    </motion.div>
  );
};

export default InsightsGrid;
