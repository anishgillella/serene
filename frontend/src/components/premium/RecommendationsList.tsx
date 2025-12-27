import React from 'react';
import { motion } from 'framer-motion';
import { Lightbulb, ArrowRight, Sparkles } from 'lucide-react';

interface RecommendationsListProps {
  recommendations: string[];
  delay?: number;
}

export const RecommendationsList: React.FC<RecommendationsListProps> = ({
  recommendations,
  delay = 0,
}) => {
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
    hidden: { opacity: 0, x: -20 },
    show: { opacity: 1, x: 0 },
  };

  // Parse emoji from recommendation if present
  const parseRecommendation = (rec: string) => {
    const emojiMatch = rec.match(/^(\p{Emoji})\s*/u);
    if (emojiMatch) {
      return {
        emoji: emojiMatch[1],
        text: rec.slice(emojiMatch[0].length),
      };
    }
    return { emoji: null, text: rec };
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-3xl p-6 shadow-glass"
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <div className="p-2.5 rounded-xl bg-amber-50">
          <Sparkles size={20} className="text-amber-500" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-warmGray-800">Recommendations</h3>
          <p className="text-xs text-warmGray-500">Personalized insights for your relationship</p>
        </div>
      </div>

      {/* Recommendations list */}
      <motion.ul
        variants={container}
        initial="hidden"
        animate="show"
        className="space-y-3"
      >
        {recommendations.map((rec, idx) => {
          const { emoji, text } = parseRecommendation(rec);

          return (
            <motion.li
              key={idx}
              variants={item}
              whileHover={{ x: 4 }}
              className="group"
            >
              <div className="flex items-start gap-3 p-3 rounded-xl bg-warmGray-50/50 hover:bg-warmGray-50 transition-colors cursor-pointer">
                {/* Emoji or number indicator */}
                <div className={`
                  flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-sm font-medium
                  ${emoji ? 'text-lg' : 'bg-rose-100 text-rose-600'}
                `}>
                  {emoji || idx + 1}
                </div>

                {/* Text */}
                <p className="flex-1 text-sm text-warmGray-700 leading-relaxed pt-1">
                  {text}
                </p>

                {/* Arrow on hover */}
                <ArrowRight
                  size={16}
                  className="flex-shrink-0 mt-1.5 text-warmGray-300 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all"
                />
              </div>
            </motion.li>
          );
        })}
      </motion.ul>

      {/* Empty state */}
      {recommendations.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-8"
        >
          <Lightbulb size={32} className="mx-auto text-warmGray-300 mb-3" />
          <p className="text-sm text-warmGray-500">No recommendations yet</p>
        </motion.div>
      )}
    </motion.div>
  );
};

export default RecommendationsList;
