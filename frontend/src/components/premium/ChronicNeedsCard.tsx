import React from 'react';
import { motion } from 'framer-motion';
import { Heart, HeartCrack, Repeat, TrendingUp } from 'lucide-react';

interface ChronicNeed {
  need: string;
  conflict_count: number;
  percentage_of_conflicts: number;
  first_appeared?: string;
  is_chronic?: boolean;
}

interface ChronicNeedsCardProps {
  data: ChronicNeed[];
  delay?: number;
}

const needEmojis: Record<string, string> = {
  'feeling_heard': '👂',
  'trust': '🤝',
  'appreciation': '🌟',
  'respect': '🎯',
  'autonomy': '🦋',
  'security': '🛡️',
  'intimacy': '💕',
  'validation': '✨',
  'support': '🤗',
  'communication': '💬',
};

export const ChronicNeedsCard: React.FC<ChronicNeedsCardProps> = ({
  data,
  delay = 0,
}) => {
  const needs = data || [];

  const formatNeedLabel = (need: string) => {
    return need.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const getEmoji = (need: string) => {
    return needEmojis[need.toLowerCase()] || '💭';
  };

  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: delay + 0.2,
      },
    },
  };

  const item = {
    hidden: { opacity: 0, scale: 0.9 },
    show: { opacity: 1, scale: 1 },
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-3xl p-6 shadow-glass h-full"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-lavender-100">
            <Heart size={20} className="text-purple-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-warmGray-800">Unmet Needs</h3>
            <p className="text-xs text-warmGray-500">Recurring emotional patterns</p>
          </div>
        </div>
      </div>

      {/* Needs grid */}
      {needs.length > 0 ? (
        <motion.div
          variants={container}
          initial="hidden"
          animate="show"
          className="space-y-3"
        >
          {needs.slice(0, 5).map((need, idx) => (
            <motion.div
              key={idx}
              variants={item}
              whileHover={{ scale: 1.02 }}
              className="relative overflow-hidden rounded-xl bg-gradient-to-r from-lavender-50/50 to-peach-50/50 p-4"
            >
              <div className="flex items-center gap-3">
                {/* Emoji */}
                <span className="text-2xl">{getEmoji(need.need)}</span>

                {/* Content */}
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1.5">
                    <p className="text-sm font-medium text-warmGray-800">
                      {formatNeedLabel(need.need)}
                    </p>
                    {need.is_chronic && (
                      <span className="flex items-center gap-1 text-2xs font-medium text-amber-600 bg-amber-100 px-2 py-0.5 rounded-full">
                        <Repeat size={10} />
                        Chronic
                      </span>
                    )}
                  </div>

                  {/* Progress bar */}
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-warmGray-100 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-gradient-to-r from-purple-400 to-rose-400 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min(need.percentage_of_conflicts, 100)}%` }}
                        transition={{ duration: 0.8, delay: delay + 0.3 + idx * 0.1, ease: "easeOut" }}
                      />
                    </div>
                    <span className="text-xs font-medium text-warmGray-500 w-12 text-right">
                      {Math.round(need.percentage_of_conflicts)}%
                    </span>
                  </div>

                  {/* Meta */}
                  <p className="text-2xs text-warmGray-400 mt-1.5">
                    Appears in {need.conflict_count} conflicts
                  </p>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      ) : (
        // Empty state
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: delay + 0.3 }}
          className="flex flex-col items-center justify-center py-12 text-center"
        >
          <div className="p-4 rounded-full bg-lavender-100 mb-4">
            <HeartCrack size={24} className="text-purple-400" />
          </div>
          <p className="text-sm font-medium text-warmGray-600 mb-1">No chronic needs detected</p>
          <p className="text-xs text-warmGray-400 max-w-[200px]">
            Patterns emerge after analyzing multiple conflicts
          </p>
        </motion.div>
      )}

      {/* Insight footer */}
      {needs.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: delay + 0.6 }}
          className="mt-5 pt-4 border-t border-warmGray-100"
        >
          <div className="flex items-start gap-2 text-xs text-warmGray-500">
            <TrendingUp size={14} className="flex-shrink-0 mt-0.5 text-purple-400" />
            <p>
              Addressing these needs proactively can reduce conflict frequency by up to 40%
            </p>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
};

export default ChronicNeedsCard;
