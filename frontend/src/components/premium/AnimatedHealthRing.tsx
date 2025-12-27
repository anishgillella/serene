import React, { useEffect, useState } from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';

interface AnimatedHealthRingProps {
  value: number; // 0-100
  size?: number;
  strokeWidth?: number;
  trend?: 'up' | 'down' | 'stable';
}

export const AnimatedHealthRing: React.FC<AnimatedHealthRingProps> = ({
  value,
  size = 200,
  strokeWidth = 12,
  trend = 'stable',
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  // Animated spring value
  const springValue = useSpring(0, {
    stiffness: 50,
    damping: 20,
    mass: 1,
  });

  // Transform spring value to dash offset
  const dashOffset = useTransform(
    springValue,
    [0, 100],
    [circumference, 0]
  );

  // Animated counter
  const displayValue = useTransform(springValue, (v) => Math.round(v));
  const [counter, setCounter] = useState(0);

  useEffect(() => {
    setIsVisible(true);
    springValue.set(value);

    const unsubscribe = displayValue.on('change', (v) => {
      setCounter(v);
    });

    return () => unsubscribe();
  }, [value, springValue, displayValue]);

  // Color based on health score
  const getColor = (score: number) => {
    if (score >= 80) return { stroke: '#10B981', glow: 'rgba(16, 185, 129, 0.3)' };
    if (score >= 60) return { stroke: '#3B82F6', glow: 'rgba(59, 130, 246, 0.3)' };
    if (score >= 40) return { stroke: '#F59E0B', glow: 'rgba(245, 158, 11, 0.3)' };
    return { stroke: '#F43F5E', glow: 'rgba(244, 63, 94, 0.3)' };
  };

  const colors = getColor(value);

  const getStatusLabel = (score: number) => {
    if (score >= 80) return 'Thriving';
    if (score >= 60) return 'Healthy';
    if (score >= 40) return 'Needs Attention';
    return 'Critical';
  };

  const getTrendIcon = () => {
    if (trend === 'up') return '↑';
    if (trend === 'down') return '↓';
    return '→';
  };

  const getTrendColor = () => {
    if (trend === 'up') return 'text-emerald-500';
    if (trend === 'down') return 'text-rose-500';
    return 'text-warmGray-400';
  };

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      {/* Glow effect */}
      <motion.div
        className="absolute inset-0 rounded-full blur-xl"
        style={{ backgroundColor: colors.glow }}
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: isVisible ? 0.5 : 0, scale: isVisible ? 1 : 0.8 }}
        transition={{ duration: 1, delay: 0.3 }}
      />

      {/* Background ring */}
      <svg
        width={size}
        height={size}
        className="absolute transform -rotate-90"
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-warmGray-100"
        />
      </svg>

      {/* Animated progress ring */}
      <svg
        width={size}
        height={size}
        className="absolute transform -rotate-90"
      >
        <defs>
          <linearGradient id="healthGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={colors.stroke} />
            <stop offset="100%" stopColor={colors.stroke} stopOpacity={0.6} />
          </linearGradient>
        </defs>
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="url(#healthGradient)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          style={{ strokeDashoffset: dashOffset }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        />
      </svg>

      {/* Center content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.div
          className="flex items-baseline"
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <span className="text-5xl font-semibold text-warmGray-800 tracking-tight">
            {counter}
          </span>
          <span className="text-lg text-warmGray-400 ml-1">%</span>
        </motion.div>

        <motion.div
          className="flex items-center gap-1.5 mt-2"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.4 }}
        >
          <span className="text-sm font-medium text-warmGray-500">
            {getStatusLabel(value)}
          </span>
          <span className={`text-sm font-semibold ${getTrendColor()}`}>
            {getTrendIcon()}
          </span>
        </motion.div>
      </div>

      {/* Decorative pulse ring */}
      <motion.div
        className="absolute rounded-full border-2"
        style={{
          width: size + 20,
          height: size + 20,
          borderColor: colors.stroke,
        }}
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{
          opacity: [0, 0.3, 0],
          scale: [0.95, 1.05, 0.95],
        }}
        transition={{
          duration: 3,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />
    </div>
  );
};

export default AnimatedHealthRing;
