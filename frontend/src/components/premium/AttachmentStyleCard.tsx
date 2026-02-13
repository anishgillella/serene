import React from 'react';
import { motion } from 'framer-motion';
import { Users } from 'lucide-react';

interface AttachmentStyleProps {
  data: {
    has_data: boolean;
    partner_a: {
      primary_style: string;
      secondary_style: string | null;
      confidence: number;
      behavioral_indicators: Array<{ behavior: string; frequency: string; example: string }>;
      summary: string;
    } | null;
    partner_b: {
      primary_style: string;
      secondary_style: string | null;
      confidence: number;
      behavioral_indicators: Array<{ behavior: string; frequency: string; example: string }>;
      summary: string;
    } | null;
    interaction_dynamic: string | null;
  } | null;
  partnerAName?: string;
  partnerBName?: string;
  delay?: number;
}

const styleColors: Record<string, { bg: string; text: string; border: string }> = {
  secure: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  anxious: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  avoidant: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
  fearful_avoidant: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200' },
};

const formatStyle = (style: string) =>
  style.replace(/_/g, '-').replace(/\b\w/g, l => l.toUpperCase());

const ConfidenceBar: React.FC<{ confidence: number; delay: number }> = ({ confidence, delay }) => (
  <div className="h-1.5 bg-warmGray-100 rounded-full overflow-hidden w-full">
    <motion.div
      className="h-full rounded-full bg-gradient-to-r from-rose-400 to-purple-400"
      initial={{ width: 0 }}
      animate={{ width: `${confidence * 100}%` }}
      transition={{ duration: 0.8, delay }}
    />
  </div>
);

export const AttachmentStyleCard: React.FC<AttachmentStyleProps> = ({
  data,
  partnerAName = 'Partner A',
  partnerBName = 'Partner B',
  delay = 0,
}) => {
  if (!data?.has_data) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay }}
        className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-5 shadow-subtle"
      >
        <div className="flex items-center gap-2 mb-2">
          <div className="p-2 rounded-xl bg-purple-50">
            <Users size={18} className="text-purple-500" />
          </div>
          <h3 className="text-base font-semibold text-warmGray-700">Attachment Styles</h3>
        </div>
        <p className="text-sm text-warmGray-400">
          Need at least 3 conflicts for attachment analysis.
        </p>
      </motion.div>
    );
  }

  const renderPartner = (partner: NonNullable<typeof data.partner_a>, name: string, idx: number) => {
    const colors = styleColors[partner.primary_style] || styleColors.secure;

    return (
      <motion.div
        key={name}
        initial={{ opacity: 0, x: idx === 0 ? -20 : 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: delay + 0.1 * idx }}
        className="flex-1 min-w-0"
      >
        <p className="text-sm font-medium text-warmGray-600 mb-2">{name}</p>
        <div className={`p-3 rounded-xl ${colors.bg} border ${colors.border}`}>
          <p className={`text-sm font-bold ${colors.text}`}>
            {formatStyle(partner.primary_style)}
          </p>
          {partner.secondary_style && (
            <p className="text-xs text-warmGray-500 mt-0.5">
              + {formatStyle(partner.secondary_style)} tendencies
            </p>
          )}
        </div>
        <div className="mt-2">
          <div className="flex items-center justify-between text-xs text-warmGray-400 mb-1">
            <span>Confidence</span>
            <span>{Math.round(partner.confidence * 100)}%</span>
          </div>
          <ConfidenceBar confidence={partner.confidence} delay={delay + 0.3 + 0.1 * idx} />
        </div>
        <p className="text-xs text-warmGray-500 mt-2 leading-relaxed line-clamp-3">
          {partner.summary}
        </p>
      </motion.div>
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-5 shadow-subtle"
    >
      <div className="flex items-center gap-2 mb-4">
        <div className="p-2 rounded-xl bg-purple-50">
          <Users size={18} className="text-purple-500" />
        </div>
        <h3 className="text-base font-semibold text-warmGray-700">Attachment Styles</h3>
      </div>

      <div className="flex gap-4">
        {data.partner_a && renderPartner(data.partner_a, partnerAName, 0)}
        {data.partner_b && renderPartner(data.partner_b, partnerBName, 1)}
      </div>

      {data.interaction_dynamic && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: delay + 0.5 }}
          className="mt-4 p-3 rounded-xl bg-warmGray-50/50 border border-warmGray-100"
        >
          <p className="text-xs font-medium text-warmGray-600 mb-1">Interaction Dynamic</p>
          <p className="text-xs text-warmGray-500 leading-relaxed">{data.interaction_dynamic}</p>
        </motion.div>
      )}
    </motion.div>
  );
};

export default AttachmentStyleCard;
