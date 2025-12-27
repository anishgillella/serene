import React from 'react';
import { motion } from 'framer-motion';
import { MessageCircle, User, Users, AlertCircle } from 'lucide-react';

interface CommunicationQualityProps {
  partnerA: {
    iStatements: number;
    youStatements: number;
    name?: string;
  };
  partnerB: {
    iStatements: number;
    youStatements: number;
    name?: string;
  };
  interruptions: number;
  activeListening: number;
  delay?: number;
}

export const CommunicationQuality: React.FC<CommunicationQualityProps> = ({
  partnerA,
  partnerB,
  interruptions,
  activeListening,
  delay = 0,
}) => {
  // Calculate I/You ratios
  const getRatio = (i: number, you: number) => {
    if (you === 0) return i > 0 ? i : 0;
    return Math.round((i / you) * 100) / 100;
  };

  const partnerARatio = getRatio(partnerA.iStatements, partnerA.youStatements);
  const partnerBRatio = getRatio(partnerB.iStatements, partnerB.youStatements);

  const getRatioStatus = (ratio: number) => {
    if (ratio >= 2) return { label: 'Healthy', color: 'emerald' };
    if (ratio >= 1) return { label: 'Balanced', color: 'amber' };
    return { label: 'Needs Work', color: 'rose' };
  };

  const partnerAStatus = getRatioStatus(partnerARatio);
  const partnerBStatus = getRatioStatus(partnerBRatio);

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
    hidden: { opacity: 0, y: 10 },
    show: { opacity: 1, y: 0 },
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
        <div className="p-2.5 rounded-xl bg-blue-50">
          <MessageCircle size={20} className="text-blue-500" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-warmGray-800">Communication Quality</h3>
          <p className="text-xs text-warmGray-500">"I" vs "You" statement analysis</p>
        </div>
      </div>

      {/* Partner comparison */}
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="space-y-4"
      >
        {/* Partner A */}
        <motion.div variants={item} className="p-4 bg-warmGray-50/50 rounded-xl">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <User size={16} className="text-blue-500" />
              <span className="text-sm font-medium text-warmGray-700">
                {partnerA.name || 'Partner A'}
              </span>
            </div>
            <span className={`text-xs font-medium px-2 py-1 rounded-full bg-${partnerAStatus.color}-100 text-${partnerAStatus.color}-600`}>
              {partnerAStatus.label}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-3 text-center">
            <div>
              <p className="text-lg font-semibold text-emerald-600">{partnerA.iStatements}</p>
              <p className="text-2xs text-warmGray-500">"I" statements</p>
            </div>
            <div>
              <p className="text-lg font-semibold text-rose-500">{partnerA.youStatements}</p>
              <p className="text-2xs text-warmGray-500">"You" statements</p>
            </div>
            <div>
              <p className="text-lg font-semibold text-warmGray-800">{partnerARatio}:1</p>
              <p className="text-2xs text-warmGray-500">Ratio</p>
            </div>
          </div>

          {/* Ratio bar */}
          <div className="mt-3 h-2 bg-warmGray-200 rounded-full overflow-hidden flex">
            <motion.div
              className="h-full bg-emerald-500"
              initial={{ width: 0 }}
              animate={{ width: `${(partnerA.iStatements / (partnerA.iStatements + partnerA.youStatements || 1)) * 100}%` }}
              transition={{ duration: 0.8, delay: delay + 0.4 }}
            />
            <motion.div
              className="h-full bg-rose-400"
              initial={{ width: 0 }}
              animate={{ width: `${(partnerA.youStatements / (partnerA.iStatements + partnerA.youStatements || 1)) * 100}%` }}
              transition={{ duration: 0.8, delay: delay + 0.4 }}
            />
          </div>
        </motion.div>

        {/* Partner B */}
        <motion.div variants={item} className="p-4 bg-warmGray-50/50 rounded-xl">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <User size={16} className="text-purple-500" />
              <span className="text-sm font-medium text-warmGray-700">
                {partnerB.name || 'Partner B'}
              </span>
            </div>
            <span className={`text-xs font-medium px-2 py-1 rounded-full bg-${partnerBStatus.color}-100 text-${partnerBStatus.color}-600`}>
              {partnerBStatus.label}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-3 text-center">
            <div>
              <p className="text-lg font-semibold text-emerald-600">{partnerB.iStatements}</p>
              <p className="text-2xs text-warmGray-500">"I" statements</p>
            </div>
            <div>
              <p className="text-lg font-semibold text-rose-500">{partnerB.youStatements}</p>
              <p className="text-2xs text-warmGray-500">"You" statements</p>
            </div>
            <div>
              <p className="text-lg font-semibold text-warmGray-800">{partnerBRatio}:1</p>
              <p className="text-2xs text-warmGray-500">Ratio</p>
            </div>
          </div>

          {/* Ratio bar */}
          <div className="mt-3 h-2 bg-warmGray-200 rounded-full overflow-hidden flex">
            <motion.div
              className="h-full bg-emerald-500"
              initial={{ width: 0 }}
              animate={{ width: `${(partnerB.iStatements / (partnerB.iStatements + partnerB.youStatements || 1)) * 100}%` }}
              transition={{ duration: 0.8, delay: delay + 0.5 }}
            />
            <motion.div
              className="h-full bg-rose-400"
              initial={{ width: 0 }}
              animate={{ width: `${(partnerB.youStatements / (partnerB.iStatements + partnerB.youStatements || 1)) * 100}%` }}
              transition={{ duration: 0.8, delay: delay + 0.5 }}
            />
          </div>
        </motion.div>

        {/* Additional metrics */}
        <motion.div variants={item} className="grid grid-cols-2 gap-3">
          <div className="p-3 bg-orange-50/50 rounded-xl text-center">
            <p className="text-xl font-semibold text-orange-600">{interruptions}</p>
            <p className="text-xs text-warmGray-500">Interruptions</p>
          </div>
          <div className="p-3 bg-emerald-50/50 rounded-xl text-center">
            <p className="text-xl font-semibold text-emerald-600">{activeListening}</p>
            <p className="text-xs text-warmGray-500">Active Listening</p>
          </div>
        </motion.div>
      </motion.div>

      {/* Tip */}
      <motion.div
        className="mt-4 p-3 bg-blue-50/50 rounded-xl flex items-start gap-2"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: delay + 0.7 }}
      >
        <AlertCircle size={14} className="text-blue-500 mt-0.5 flex-shrink-0" />
        <p className="text-xs text-blue-700">
          Higher "I" to "You" ratio indicates healthier communication. Try phrases like "I feel..." instead of "You always..."
        </p>
      </motion.div>
    </motion.div>
  );
};

export default CommunicationQuality;
