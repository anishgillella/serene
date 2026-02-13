import React from 'react';
import { motion } from 'framer-motion';

interface SkeletonCardProps {
  lines?: number;
  className?: string;
}

export const SkeletonCard: React.FC<SkeletonCardProps> = ({ lines = 3, className = '' }) => {
  return (
    <div
      className={`bg-white/70 backdrop-blur-xl border border-white/50 rounded-3xl p-6 shadow-glass ${className}`}
    >
      {/* Title skeleton */}
      <div className="flex items-center gap-3 mb-5">
        <motion.div
          className="w-10 h-10 rounded-xl bg-warmGray-100"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
        />
        <div className="flex-1 space-y-2">
          <motion.div
            className="h-4 bg-warmGray-100 rounded-full w-1/3"
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut', delay: 0.1 }}
          />
          <motion.div
            className="h-3 bg-warmGray-100 rounded-full w-1/4"
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut', delay: 0.2 }}
          />
        </div>
      </div>

      {/* Content lines */}
      <div className="space-y-3">
        {Array.from({ length: lines }).map((_, i) => (
          <motion.div
            key={i}
            className={`h-3 bg-warmGray-100 rounded-full ${i === lines - 1 ? 'w-2/3' : 'w-full'}`}
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: 'easeInOut',
              delay: 0.1 * (i + 3),
            }}
          />
        ))}
      </div>
    </div>
  );
};

export default SkeletonCard;
