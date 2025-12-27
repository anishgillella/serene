import React, { useEffect, useState } from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';
import { AlertTriangle, Shield, ShieldAlert, ShieldCheck } from 'lucide-react';

interface RiskGaugeProps {
  riskScore: number; // 0-1
  interpretation: string;
  daysUntilPredicted: number;
  unresolvedIssues: number;
  delay?: number;
}

export const RiskGauge: React.FC<RiskGaugeProps> = ({
  riskScore,
  interpretation,
  daysUntilPredicted,
  unresolvedIssues,
  delay = 0,
}) => {
  const percentage = Math.round(riskScore * 100);
  const [displayPercentage, setDisplayPercentage] = useState(0);

  const springValue = useSpring(0, {
    stiffness: 40,
    damping: 20,
  });

  useEffect(() => {
    springValue.set(percentage);
    const unsubscribe = springValue.on('change', (v) => {
      setDisplayPercentage(Math.round(v));
    });
    return () => unsubscribe();
  }, [percentage, springValue]);

  const getConfig = (level: string) => {
    switch (level) {
      case 'low':
        return {
          color: '#10B981',
          bgColor: 'bg-emerald-50',
          textColor: 'text-emerald-600',
          icon: <ShieldCheck size={24} />,
          label: 'Low Risk',
          message: 'Your relationship is in a healthy place',
        };
      case 'medium':
        return {
          color: '#F59E0B',
          bgColor: 'bg-amber-50',
          textColor: 'text-amber-600',
          icon: <Shield size={24} />,
          label: 'Moderate Risk',
          message: 'Some attention needed',
        };
      case 'high':
        return {
          color: '#F97316',
          bgColor: 'bg-orange-50',
          textColor: 'text-orange-600',
          icon: <ShieldAlert size={24} />,
          label: 'High Risk',
          message: 'Consider addressing issues soon',
        };
      case 'critical':
        return {
          color: '#EF4444',
          bgColor: 'bg-red-50',
          textColor: 'text-red-600',
          icon: <AlertTriangle size={24} />,
          label: 'Critical',
          message: 'Immediate attention recommended',
        };
      default:
        return {
          color: '#6B7280',
          bgColor: 'bg-gray-50',
          textColor: 'text-gray-600',
          icon: <Shield size={24} />,
          label: 'Unknown',
          message: 'Calculating...',
        };
    }
  };

  const config = getConfig(interpretation);

  // Arc path calculation
  const createArc = (percentage: number) => {
    const angle = (percentage / 100) * 180;
    const radians = (angle - 90) * (Math.PI / 180);
    const x = 100 + 80 * Math.cos(radians);
    const y = 100 + 80 * Math.sin(radians);
    const largeArc = angle > 90 ? 1 : 0;

    return `M 20 100 A 80 80 0 ${largeArc} 1 ${x} ${y}`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-3xl p-6 shadow-glass"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-warmGray-800">Escalation Risk</h3>
        <motion.div
          className={`p-2.5 rounded-xl ${config.bgColor}`}
          whileHover={{ scale: 1.05 }}
        >
          <span className={config.textColor}>{config.icon}</span>
        </motion.div>
      </div>

      {/* Gauge */}
      <div className="relative flex justify-center mb-6">
        <svg width="200" height="120" viewBox="0 0 200 120">
          {/* Background arc */}
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="#E7E5E4"
            strokeWidth="12"
            strokeLinecap="round"
          />

          {/* Animated progress arc */}
          <motion.path
            d={createArc(displayPercentage)}
            fill="none"
            stroke={config.color}
            strokeWidth="12"
            strokeLinecap="round"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1, delay: delay + 0.3, ease: "easeOut" }}
          />

          {/* Center text */}
          <text
            x="100"
            y="85"
            textAnchor="middle"
            className="text-3xl font-semibold fill-warmGray-800"
          >
            {displayPercentage}%
          </text>
          <text
            x="100"
            y="105"
            textAnchor="middle"
            className="text-xs fill-warmGray-500"
          >
            {config.label}
          </text>
        </svg>
      </div>

      {/* Status message */}
      <motion.p
        className={`text-center text-sm font-medium mb-6 ${config.textColor}`}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: delay + 0.5 }}
      >
        {config.message}
      </motion.p>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3">
        <motion.div
          className="bg-warmGray-50/50 rounded-xl p-3 text-center"
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: delay + 0.4 }}
        >
          <p className="text-2xl font-semibold text-warmGray-800">{unresolvedIssues}</p>
          <p className="text-xs text-warmGray-500">Unresolved</p>
        </motion.div>

        <motion.div
          className="bg-warmGray-50/50 rounded-xl p-3 text-center"
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: delay + 0.5 }}
        >
          <p className="text-2xl font-semibold text-warmGray-800">{daysUntilPredicted}</p>
          <p className="text-xs text-warmGray-500">Days predicted</p>
        </motion.div>
      </div>
    </motion.div>
  );
};

export default RiskGauge;
