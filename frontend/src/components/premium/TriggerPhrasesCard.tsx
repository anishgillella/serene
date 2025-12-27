import React from 'react';
import { motion } from 'framer-motion';
import { Zap, AlertTriangle, TrendingUp } from 'lucide-react';

interface TriggerPhrase {
  phrase: string;
  usage_count: number;
  escalation_rate: number;
  avg_emotional_intensity?: number;
  speaker?: string;
  phrase_category?: string;
}

interface TriggerPhrasesCardProps {
  data: {
    most_impactful: TriggerPhrase[];
    trends?: any[];
  };
  delay?: number;
}

export const TriggerPhrasesCard: React.FC<TriggerPhrasesCardProps> = ({
  data,
  delay = 0,
}) => {
  const phrases = data?.most_impactful || [];

  const getIntensityColor = (rate: number) => {
    if (rate >= 0.7) return 'bg-rose-500';
    if (rate >= 0.4) return 'bg-amber-500';
    return 'bg-emerald-500';
  };

  const getIntensityLabel = (rate: number) => {
    if (rate >= 0.7) return 'High Impact';
    if (rate >= 0.4) return 'Moderate';
    return 'Low';
  };

  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08,
        delayChildren: delay + 0.2,
      },
    },
  };

  const item = {
    hidden: { opacity: 0, x: -20 },
    show: { opacity: 1, x: 0 },
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
          <div className="p-2.5 rounded-xl bg-rose-50">
            <Zap size={20} className="text-rose-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-warmGray-800">Trigger Phrases</h3>
            <p className="text-xs text-warmGray-500">Words that escalate conflicts</p>
          </div>
        </div>
        {phrases.length > 0 && (
          <span className="text-xs font-medium text-warmGray-400 bg-warmGray-100 px-2 py-1 rounded-full">
            {phrases.length} identified
          </span>
        )}
      </div>

      {/* Phrases list */}
      {phrases.length > 0 ? (
        <motion.div
          variants={container}
          initial="hidden"
          animate="show"
          className="space-y-3"
        >
          {phrases.slice(0, 5).map((phrase, idx) => (
            <motion.div
              key={idx}
              variants={item}
              whileHover={{ x: 4 }}
              className="group relative overflow-hidden rounded-xl bg-warmGray-50/50 hover:bg-warmGray-50 p-4 transition-colors"
            >
              {/* Intensity bar */}
              <motion.div
                className={`absolute left-0 top-0 bottom-0 w-1 ${getIntensityColor(phrase.escalation_rate)}`}
                initial={{ scaleY: 0 }}
                animate={{ scaleY: 1 }}
                transition={{ duration: 0.4, delay: delay + 0.3 + idx * 0.1 }}
              />

              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 pl-3">
                  {/* Phrase */}
                  <p className="text-sm font-medium text-warmGray-800 mb-1">
                    "{phrase.phrase}"
                  </p>

                  {/* Meta */}
                  <div className="flex items-center gap-3 text-xs text-warmGray-500">
                    <span className="flex items-center gap-1">
                      <TrendingUp size={12} />
                      Used {phrase.usage_count}x
                    </span>
                    {phrase.phrase_category && (
                      <span className="bg-warmGray-200/50 px-2 py-0.5 rounded-full">
                        {phrase.phrase_category}
                      </span>
                    )}
                  </div>
                </div>

                {/* Escalation rate badge */}
                <div className={`
                  px-2 py-1 rounded-lg text-xs font-medium
                  ${phrase.escalation_rate >= 0.7 ? 'bg-rose-100 text-rose-600' :
                    phrase.escalation_rate >= 0.4 ? 'bg-amber-100 text-amber-600' :
                    'bg-emerald-100 text-emerald-600'}
                `}>
                  {Math.round(phrase.escalation_rate * 100)}%
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
          <div className="p-4 rounded-full bg-warmGray-100 mb-4">
            <AlertTriangle size={24} className="text-warmGray-400" />
          </div>
          <p className="text-sm font-medium text-warmGray-600 mb-1">No triggers detected yet</p>
          <p className="text-xs text-warmGray-400 max-w-[200px]">
            Trigger phrases will appear here as patterns are identified
          </p>
        </motion.div>
      )}

      {/* Legend */}
      {phrases.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: delay + 0.5 }}
          className="flex items-center justify-center gap-4 mt-5 pt-4 border-t border-warmGray-100"
        >
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-rose-500" />
            <span className="text-2xs text-warmGray-500">High</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-amber-500" />
            <span className="text-2xs text-warmGray-500">Medium</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="text-2xs text-warmGray-500">Low</span>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
};

export default TriggerPhrasesCard;
