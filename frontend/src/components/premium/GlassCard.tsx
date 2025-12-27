import React from 'react';
import { motion } from 'framer-motion';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  hover?: boolean;
  onClick?: () => void;
}

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className = '',
  delay = 0,
  hover = true,
  onClick,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.5,
        delay,
        ease: [0.25, 0.46, 0.45, 0.94],
      }}
      whileHover={hover ? {
        y: -4,
        transition: { duration: 0.2, ease: "easeOut" }
      } : undefined}
      onClick={onClick}
      className={`
        relative overflow-hidden
        bg-white/70 backdrop-blur-xl
        border border-white/50
        rounded-3xl
        shadow-glass
        transition-shadow duration-300
        ${hover ? 'hover:shadow-lifted cursor-pointer' : ''}
        ${className}
      `}
    >
      {/* Inner glow effect */}
      <div className="absolute inset-0 bg-gradient-to-br from-white/50 via-transparent to-transparent pointer-events-none" />

      {/* Content */}
      <div className="relative z-10">
        {children}
      </div>
    </motion.div>
  );
};

// Variant for featured/highlighted cards
export const GlassCardFeatured: React.FC<GlassCardProps> = ({
  children,
  className = '',
  delay = 0,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        duration: 0.6,
        delay,
        ease: [0.25, 0.46, 0.45, 0.94],
      }}
      whileHover={{
        y: -6,
        transition: { duration: 0.2, ease: "easeOut" }
      }}
      className={`
        relative overflow-hidden
        bg-gradient-to-br from-white/80 to-white/60 backdrop-blur-xl
        border border-rose-200/30
        rounded-3xl
        shadow-glow
        transition-all duration-300
        hover:shadow-glow-lg
        ${className}
      `}
    >
      {/* Animated gradient border */}
      <div className="absolute inset-0 rounded-3xl bg-gradient-to-r from-rose-200/20 via-lavender-200/20 to-peach-200/20 opacity-0 hover:opacity-100 transition-opacity duration-500" />

      {/* Inner glow */}
      <div className="absolute inset-0 bg-gradient-to-br from-white/60 via-transparent to-transparent pointer-events-none" />

      {/* Content */}
      <div className="relative z-10">
        {children}
      </div>
    </motion.div>
  );
};

export default GlassCard;
