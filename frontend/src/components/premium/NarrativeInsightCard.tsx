import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles } from 'lucide-react';

interface NarrativeInsightCardProps {
  title: string;
  insight: string | null;
  loading?: boolean;
  delay?: number;
}

export const NarrativeInsightCard: React.FC<NarrativeInsightCardProps> = ({
  title,
  insight,
  loading = false,
  delay = 0,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="bg-gradient-to-br from-white/80 to-purple-50/40 backdrop-blur-xl border border-purple-100/50 rounded-3xl p-6 shadow-glass"
    >
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 rounded-xl bg-purple-50">
          <Sparkles size={18} className="text-purple-500" />
        </div>
        <h3 className="text-sm font-semibold text-warmGray-700 uppercase tracking-wide">
          {title}
        </h3>
      </div>

      {loading ? (
        <div className="space-y-2.5">
          {[1, 0.9, 0.7].map((w, i) => (
            <motion.div
              key={i}
              className="h-3.5 bg-purple-100/60 rounded-full"
              style={{ width: `${w * 100}%` }}
              animate={{ opacity: [0.4, 0.8, 0.4] }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: 'easeInOut',
                delay: i * 0.15,
              }}
            />
          ))}
        </div>
      ) : insight ? (
        <p className="text-sm text-warmGray-600 leading-relaxed">{insight}</p>
      ) : (
        <p className="text-sm text-warmGray-400 italic">
          Not enough data yet. Keep logging conversations to unlock this insight.
        </p>
      )}
    </motion.div>
  );
};

export default NarrativeInsightCard;
