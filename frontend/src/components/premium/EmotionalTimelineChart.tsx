import React from 'react';
import { motion } from 'framer-motion';
import { Activity, TrendingUp, TrendingDown, Minus, Zap, Heart, Shield } from 'lucide-react';
import { GlassCard } from './GlassCard';

interface EmotionalMoment {
  message_sequence: number;
  speaker: string;
  emotional_intensity: number;
  negativity_score?: number;
  primary_emotion: string;
  is_escalation_point: boolean;
  is_repair_attempt: boolean;
  is_de_escalation: boolean;
  moment_note?: string;
}

interface EmotionalTimelineChartProps {
  moments: EmotionalMoment[];
  summary?: {
    peak_intensity?: number;
    peak_moment?: number;
    peak_emotion?: string;
    total_escalations?: number;
    total_repair_attempts?: number;
    emotional_arc?: string;
  };
  delay?: number;
}

const emotionColors: Record<string, string> = {
  anger: '#ef4444',
  hurt: '#f43f5e',
  frustration: '#f97316',
  sadness: '#6366f1',
  contempt: '#dc2626',
  fear: '#eab308',
  anxiety: '#a855f7',
  disappointment: '#8b5cf6',
  neutral: '#9ca3af',
};

export const EmotionalTimelineChart: React.FC<EmotionalTimelineChartProps> = ({
  moments,
  summary,
  delay = 0,
}) => {
  if (!moments || moments.length === 0) {
    return (
      <GlassCard className="p-6" delay={delay}>
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 rounded-xl bg-rose-50">
            <Activity size={20} className="text-rose-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-warmGray-800">Emotional Timeline</h3>
            <p className="text-xs text-warmGray-500">Temperature throughout the conflict</p>
          </div>
        </div>
        <div className="text-center py-8">
          <p className="text-warmGray-500">No timeline data available yet</p>
        </div>
      </GlassCard>
    );
  }

  const maxIntensity = Math.max(...moments.map(m => m.emotional_intensity), 10);
  const chartHeight = 120;

  // Calculate arc description
  const getArcIcon = () => {
    if (summary?.emotional_arc === 'recovering' || summary?.emotional_arc === 'resolved') {
      return <TrendingDown size={14} className="text-emerald-500" />;
    } else if (summary?.emotional_arc === 'escalating') {
      return <TrendingUp size={14} className="text-red-500" />;
    }
    return <Minus size={14} className="text-warmGray-400" />;
  };

  return (
    <GlassCard className="p-6" delay={delay} hover={false}>
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-rose-50">
            <Activity size={20} className="text-rose-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-warmGray-800">Emotional Timeline</h3>
            <p className="text-xs text-warmGray-500">Temperature throughout the conflict</p>
          </div>
        </div>

        {/* Summary stats */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <Zap size={14} className="text-red-400" />
            <span className="text-xs text-warmGray-500">{summary?.total_escalations || 0} escalations</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Heart size={14} className="text-emerald-400" />
            <span className="text-xs text-warmGray-500">{summary?.total_repair_attempts || 0} repairs</span>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="relative mb-4">
        {/* Y-axis labels */}
        <div className="absolute left-0 top-0 bottom-6 w-8 flex flex-col justify-between text-xs text-warmGray-400">
          <span>10</span>
          <span>5</span>
          <span>0</span>
        </div>

        {/* Chart area */}
        <div className="ml-10 relative" style={{ height: chartHeight }}>
          {/* Background grid */}
          <div className="absolute inset-0 flex flex-col justify-between pointer-events-none">
            {[0, 1, 2].map(i => (
              <div key={i} className="border-b border-warmGray-100 w-full" />
            ))}
          </div>

          {/* Danger zone */}
          <div
            className="absolute left-0 right-0 bg-red-50/50"
            style={{ top: 0, height: chartHeight * 0.3 }}
          />

          {/* Line chart */}
          <svg className="absolute inset-0 w-full h-full overflow-visible">
            {/* Area fill */}
            <motion.path
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.2 }}
              transition={{ delay: delay + 0.3 }}
              d={`
                M 0 ${chartHeight}
                ${moments.map((m, i) => {
                  const x = (i / (moments.length - 1 || 1)) * 100;
                  const y = chartHeight - (m.emotional_intensity / maxIntensity) * chartHeight;
                  return `L ${x}% ${y}`;
                }).join(' ')}
                L 100% ${chartHeight}
                Z
              `}
              fill="url(#gradient)"
            />

            {/* Line */}
            <motion.path
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ delay: delay + 0.2, duration: 1, ease: "easeOut" }}
              d={moments.map((m, i) => {
                const x = (i / (moments.length - 1 || 1)) * 100;
                const y = chartHeight - (m.emotional_intensity / maxIntensity) * chartHeight;
                return `${i === 0 ? 'M' : 'L'} ${x}% ${y}`;
              }).join(' ')}
              stroke="#f43f5e"
              strokeWidth="2"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {/* Gradient definition */}
            <defs>
              <linearGradient id="gradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#f43f5e" />
                <stop offset="100%" stopColor="#f43f5e" stopOpacity="0" />
              </linearGradient>
            </defs>
          </svg>

          {/* Data points */}
          {moments.map((moment, i) => {
            const x = (i / (moments.length - 1 || 1)) * 100;
            const y = chartHeight - (moment.emotional_intensity / maxIntensity) * chartHeight;

            return (
              <motion.div
                key={i}
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: delay + 0.3 + i * 0.05 }}
                className="absolute group"
                style={{ left: `${x}%`, top: y, transform: 'translate(-50%, -50%)' }}
              >
                {/* Point */}
                <div
                  className={`w-3 h-3 rounded-full border-2 border-white shadow-sm ${
                    moment.is_escalation_point ? 'bg-red-500' :
                    moment.is_repair_attempt ? 'bg-emerald-500' :
                    moment.is_de_escalation ? 'bg-blue-500' :
                    'bg-rose-400'
                  }`}
                />

                {/* Escalation/Repair indicators */}
                {moment.is_escalation_point && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <Zap size={10} className="text-red-500" />
                  </div>
                )}
                {moment.is_repair_attempt && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <Heart size={10} className="text-emerald-500" />
                  </div>
                )}

                {/* Tooltip */}
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity z-10 pointer-events-none">
                  <div className="bg-warmGray-800 text-white text-xs rounded-lg px-3 py-2 whitespace-nowrap">
                    <p className="font-medium">{moment.speaker === 'partner_a' ? 'Partner A' : 'Partner B'}</p>
                    <p className="text-warmGray-300">Intensity: {moment.emotional_intensity}/10</p>
                    <p className="text-warmGray-300 capitalize">{moment.primary_emotion}</p>
                    {moment.moment_note && (
                      <p className="text-warmGray-400 text-[10px] mt-1 max-w-[150px]">{moment.moment_note}</p>
                    )}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* X-axis labels */}
        <div className="ml-10 flex justify-between text-xs text-warmGray-400 mt-2">
          <span>Start</span>
          <span>End</span>
        </div>
      </div>

      {/* Arc summary */}
      {summary?.emotional_arc && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: delay + 0.6 }}
          className="flex items-center justify-between pt-4 border-t border-warmGray-100"
        >
          <div className="flex items-center gap-2">
            {getArcIcon()}
            <span className="text-sm text-warmGray-600 capitalize">
              {summary.emotional_arc} conflict
            </span>
          </div>
          {summary.peak_emotion && (
            <span className="text-xs text-warmGray-400">
              Peak: {summary.peak_emotion} at message #{summary.peak_moment}
            </span>
          )}
        </motion.div>
      )}

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mt-4">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-red-500" />
          <span className="text-xs text-warmGray-400">Escalation</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-emerald-500" />
          <span className="text-xs text-warmGray-400">Repair attempt</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-blue-500" />
          <span className="text-xs text-warmGray-400">De-escalation</span>
        </div>
      </div>
    </GlassCard>
  );
};

export default EmotionalTimelineChart;
