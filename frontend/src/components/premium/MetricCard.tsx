import React from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';
import { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: number | string;
  suffix?: string;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: string;
  icon?: React.ReactNode;
  color?: 'rose' | 'emerald' | 'amber' | 'blue' | 'lavender';
  delay?: number;
  animate?: boolean;
}

const colorVariants = {
  rose: {
    bg: 'bg-rose-50',
    icon: 'text-rose-500',
    glow: 'shadow-[0_0_30px_rgba(244,63,94,0.15)]',
  },
  emerald: {
    bg: 'bg-emerald-50',
    icon: 'text-emerald-500',
    glow: 'shadow-[0_0_30px_rgba(16,185,129,0.15)]',
  },
  amber: {
    bg: 'bg-amber-50',
    icon: 'text-amber-500',
    glow: 'shadow-[0_0_30px_rgba(245,158,11,0.15)]',
  },
  blue: {
    bg: 'bg-blue-50',
    icon: 'text-blue-500',
    glow: 'shadow-[0_0_30px_rgba(59,130,246,0.15)]',
  },
  lavender: {
    bg: 'bg-lavender-100',
    icon: 'text-purple-500',
    glow: 'shadow-[0_0_30px_rgba(139,92,246,0.15)]',
  },
};

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  suffix = '',
  trend,
  trendValue,
  icon,
  color = 'rose',
  delay = 0,
  animate = true,
}) => {
  const numericValue = typeof value === 'number' ? value : parseFloat(value) || 0;
  const [displayValue, setDisplayValue] = useState(0);

  const springValue = useSpring(0, {
    stiffness: 50,
    damping: 20,
  });

  useEffect(() => {
    if (animate && typeof value === 'number') {
      springValue.set(numericValue);
      const unsubscribe = springValue.on('change', (v) => {
        setDisplayValue(Math.round(v));
      });
      return () => unsubscribe();
    } else {
      setDisplayValue(numericValue);
    }
  }, [numericValue, animate, springValue]);

  const colors = colorVariants[color];

  const getTrendIcon = () => {
    if (trend === 'up') return <TrendingUp size={14} className="text-emerald-500" />;
    if (trend === 'down') return <TrendingDown size={14} className="text-rose-500" />;
    return <Minus size={14} className="text-warmGray-400" />;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        duration: 0.5,
        delay,
        ease: [0.25, 0.46, 0.45, 0.94],
      }}
      whileHover={{
        y: -4,
        transition: { duration: 0.2, ease: "easeOut" }
      }}
      className={`
        relative overflow-hidden
        bg-white/70 backdrop-blur-xl
        border border-white/50
        rounded-2xl p-5
        shadow-subtle hover:shadow-lifted
        transition-shadow duration-300
        ${colors.glow}
      `}
    >
      {/* Subtle gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-white/40 via-transparent to-transparent pointer-events-none" />

      <div className="relative z-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-warmGray-500">{label}</span>
          {icon && (
            <div className={`p-2 rounded-xl ${colors.bg}`}>
              <span className={colors.icon}>{icon}</span>
            </div>
          )}
        </div>

        {/* Value */}
        <div className="flex items-baseline gap-1.5">
          <motion.span
            className="text-3xl font-semibold text-warmGray-800 tracking-tight"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3, delay: delay + 0.2 }}
          >
            {typeof value === 'number' ? displayValue : value}
          </motion.span>
          {suffix && (
            <span className="text-lg text-warmGray-400">{suffix}</span>
          )}
        </div>

        {/* Trend */}
        {trend && (
          <motion.div
            className="flex items-center gap-1.5 mt-2"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: delay + 0.3 }}
          >
            {getTrendIcon()}
            {trendValue && (
              <span className={`text-xs font-medium ${
                trend === 'up' ? 'text-emerald-600' :
                trend === 'down' ? 'text-rose-600' :
                'text-warmGray-500'
              }`}>
                {trendValue}
              </span>
            )}
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};

// Compact variant for grids
export const MetricCardCompact: React.FC<MetricCardProps> = ({
  label,
  value,
  suffix = '',
  icon,
  color = 'rose',
  delay = 0,
}) => {
  const colors = colorVariants[color];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, delay }}
      whileHover={{ scale: 1.02 }}
      className="bg-white/50 backdrop-blur-sm rounded-xl p-4 border border-white/40"
    >
      <div className="flex items-center gap-3">
        {icon && (
          <div className={`p-2 rounded-lg ${colors.bg}`}>
            <span className={colors.icon}>{icon}</span>
          </div>
        )}
        <div>
          <p className="text-xs font-medium text-warmGray-500">{label}</p>
          <p className="text-xl font-semibold text-warmGray-800">
            {value}{suffix}
          </p>
        </div>
      </div>
    </motion.div>
  );
};

export default MetricCard;
