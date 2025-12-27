import React from 'react';
import { motion } from 'framer-motion';
import { Layers, ArrowRight, Heart, AlertCircle } from 'lucide-react';
import { GlassCard } from './GlassCard';

interface SurfaceUnderlyingMapping {
  surface_statement: string;
  surface_category: string;
  underlying_concern: string;
  underlying_emotion: string;
  underlying_need: string;
  speaker: string;
  confidence: number;
}

interface SurfaceUnderlyingCardProps {
  mappings: SurfaceUnderlyingMapping[];
  overallPattern?: string;
  keyInsight?: string;
  delay?: number;
}

const emotionColors: Record<string, string> = {
  hurt: 'bg-rose-100 text-rose-700',
  fear: 'bg-amber-100 text-amber-700',
  loneliness: 'bg-blue-100 text-blue-700',
  overwhelm: 'bg-purple-100 text-purple-700',
  rejection: 'bg-red-100 text-red-700',
  disrespect: 'bg-orange-100 text-orange-700',
  anxiety: 'bg-yellow-100 text-yellow-700',
  sadness: 'bg-indigo-100 text-indigo-700',
};

const needEmojis: Record<string, string> = {
  feeling_heard: '👂',
  trust: '🤝',
  appreciation: '💝',
  respect: '🎯',
  autonomy: '🦋',
  security: '🛡️',
  intimacy: '💕',
  validation: '✨',
};

export const SurfaceUnderlyingCard: React.FC<SurfaceUnderlyingCardProps> = ({
  mappings,
  overallPattern,
  keyInsight,
  delay = 0,
}) => {
  if (!mappings || mappings.length === 0) {
    return (
      <GlassCard className="p-6" delay={delay}>
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 rounded-xl bg-purple-50">
            <Layers size={20} className="text-purple-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-warmGray-800">What They Really Mean</h3>
            <p className="text-xs text-warmGray-500">Surface vs underlying concerns</p>
          </div>
        </div>
        <div className="text-center py-8">
          <p className="text-warmGray-500">No analysis available yet</p>
        </div>
      </GlassCard>
    );
  }

  return (
    <GlassCard className="p-6" delay={delay} hover={false}>
      <div className="flex items-center gap-3 mb-5">
        <div className="p-2.5 rounded-xl bg-purple-50">
          <Layers size={20} className="text-purple-500" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-warmGray-800">What They Really Mean</h3>
          <p className="text-xs text-warmGray-500">Surface statements → underlying concerns</p>
        </div>
      </div>

      {/* Key Insight Banner */}
      {keyInsight && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: delay + 0.2 }}
          className="mb-5 p-4 rounded-xl bg-gradient-to-r from-purple-50 to-rose-50 border border-purple-100"
        >
          <div className="flex items-start gap-2">
            <Heart size={16} className="text-purple-500 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-warmGray-700">{keyInsight}</p>
          </div>
        </motion.div>
      )}

      {/* Mappings */}
      <div className="space-y-4">
        {mappings.slice(0, 5).map((mapping, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: delay + 0.1 + idx * 0.1 }}
            className="p-4 rounded-xl bg-warmGray-50/50 hover:bg-warmGray-50 transition-colors"
          >
            <div className="flex items-start gap-3">
              {/* Speaker indicator */}
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium ${
                mapping.speaker === 'partner_a' ? 'bg-blue-100 text-blue-600' : 'bg-rose-100 text-rose-600'
              }`}>
                {mapping.speaker === 'partner_a' ? 'A' : 'B'}
              </div>

              <div className="flex-1 min-w-0">
                {/* Surface statement */}
                <div className="flex items-start gap-2 mb-2">
                  <span className="text-xs text-warmGray-400 mt-0.5 flex-shrink-0">Said:</span>
                  <p className="text-sm text-warmGray-600 italic">"{mapping.surface_statement}"</p>
                </div>

                {/* Arrow */}
                <div className="flex items-center gap-2 my-2 pl-6">
                  <ArrowRight size={14} className="text-purple-400" />
                  <span className="text-xs text-purple-500 font-medium">Really means</span>
                </div>

                {/* Underlying concern */}
                <div className="flex items-start gap-2 pl-6">
                  <p className="text-sm text-warmGray-800 font-medium">{mapping.underlying_concern}</p>
                </div>

                {/* Tags */}
                <div className="flex flex-wrap gap-2 mt-3 pl-6">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    emotionColors[mapping.underlying_emotion] || 'bg-gray-100 text-gray-600'
                  }`}>
                    {mapping.underlying_emotion}
                  </span>
                  <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-lavender-100 text-lavender-700">
                    {needEmojis[mapping.underlying_need] || '💭'} {mapping.underlying_need.replace('_', ' ')}
                  </span>
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Overall Pattern */}
      {overallPattern && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: delay + 0.5 }}
          className="mt-5 pt-4 border-t border-warmGray-100"
        >
          <div className="flex items-start gap-2">
            <AlertCircle size={14} className="text-warmGray-400 mt-0.5" />
            <p className="text-xs text-warmGray-500">{overallPattern}</p>
          </div>
        </motion.div>
      )}
    </GlassCard>
  );
};

export default SurfaceUnderlyingCard;
