import React from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';
import { useEffect, useState } from 'react';
import { Heart, HeartHandshake, TrendingUp, TrendingDown } from 'lucide-react';

interface RepairSuccessCardProps {
  successRate: number; // 0-100
  totalAttempts: number;
  successfulRepairs: number;
  delay?: number;
}

export const RepairSuccessCard: React.FC<RepairSuccessCardProps> = ({
  successRate,
  totalAttempts,
  successfulRepairs,
  delay = 0,
}) => {
  const [displayValue, setDisplayValue] = useState(0);

  const springValue = useSpring(0, {
    stiffness: 40,
    damping: 20,
  });

  useEffect(() => {
    springValue.set(successRate);
    const unsubscribe = springValue.on('change', (v) => {
      setDisplayValue(Math.round(v));
    });
    return () => unsubscribe();
  }, [successRate, springValue]);

  // Ring animation
  const circumference = 2 * Math.PI * 45;
  const strokeDashoffset = circumference - (displayValue / 100) * circumference;

  const getStatus = (rate: number) => {
    if (rate >= 60) return { label: 'Excellent', color: 'emerald', message: 'Your repairs are effective!' };
    if (rate >= 40) return { label: 'Good', color: 'amber', message: 'Room for improvement' };
    if (rate >= 20) return { label: 'Low', color: 'orange', message: 'Focus on repair skills' };
    return { label: 'Critical', color: 'red', message: 'Repairs often rejected' };
  };

  const status = getStatus(successRate);

  const colorClasses = {
    emerald: { ring: '#10B981', bg: 'bg-emerald-50', text: 'text-emerald-600' },
    amber: { ring: '#F59E0B', bg: 'bg-amber-50', text: 'text-amber-600' },
    orange: { ring: '#F97316', bg: 'bg-orange-50', text: 'text-orange-600' },
    red: { ring: '#EF4444', bg: 'bg-red-50', text: 'text-red-600' },
  };

  const colors = colorClasses[status.color as keyof typeof colorClasses];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-3xl p-6 shadow-glass"
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <div className="p-2.5 rounded-xl bg-rose-50">
          <HeartHandshake size={20} className="text-rose-500" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-warmGray-800">Repair Success</h3>
          <p className="text-xs text-warmGray-500">How often de-escalation works</p>
        </div>
      </div>

      {/* Ring */}
      <div className="flex justify-center mb-4">
        <div className="relative">
          <svg width="120" height="120" className="transform -rotate-90">
            {/* Background ring */}
            <circle
              cx="60"
              cy="60"
              r="45"
              fill="none"
              stroke="#E7E5E4"
              strokeWidth="10"
            />
            {/* Progress ring */}
            <motion.circle
              cx="60"
              cy="60"
              r="45"
              fill="none"
              stroke={colors.ring}
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray={circumference}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset }}
              transition={{ duration: 1, delay: delay + 0.3, ease: "easeOut" }}
            />
          </svg>

          {/* Center text */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-bold text-warmGray-800">{displayValue}%</span>
            <span className={`text-xs font-medium ${colors.text}`}>{status.label}</span>
          </div>
        </div>
      </div>

      {/* Message */}
      <motion.p
        className="text-center text-sm text-warmGray-600 mb-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: delay + 0.5 }}
      >
        {status.message}
      </motion.p>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3">
        <motion.div
          className="bg-warmGray-50/50 rounded-xl p-3 text-center"
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: delay + 0.4 }}
        >
          <p className="text-xl font-semibold text-warmGray-800">{totalAttempts}</p>
          <p className="text-xs text-warmGray-500">Attempts</p>
        </motion.div>
        <motion.div
          className="bg-warmGray-50/50 rounded-xl p-3 text-center"
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: delay + 0.5 }}
        >
          <p className="text-xl font-semibold text-emerald-600">{successfulRepairs}</p>
          <p className="text-xs text-warmGray-500">Successful</p>
        </motion.div>
      </div>

      {/* Tip */}
      {totalAttempts === 0 && (
        <motion.div
          className="mt-4 p-3 bg-lavender-100/50 rounded-xl"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: delay + 0.6 }}
        >
          <p className="text-xs text-purple-600 text-center">
            Repair attempts will be detected from your conflict transcripts
          </p>
        </motion.div>
      )}
    </motion.div>
  );
};

export default RepairSuccessCard;
