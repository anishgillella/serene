import React from 'react';
import { motion } from 'framer-motion';
import { HandHeart } from 'lucide-react';

interface BidResponseProps {
  data: {
    has_data: boolean;
    overall: {
      total_bids: number;
      toward: number;
      away: number;
      against: number;
      toward_rate: number;
      gottman_benchmark: number;
    };
    per_partner: Record<string, {
      total_bids: number;
      toward: number;
      away: number;
      against: number;
      toward_rate: number;
    }>;
  } | null;
  partnerAName?: string;
  partnerBName?: string;
  delay?: number;
}

const ResponseBar: React.FC<{
  toward: number;
  away: number;
  against: number;
  total: number;
  delay: number;
}> = ({ toward, away, against, total, delay }) => {
  if (total === 0) return <div className="h-4 bg-warmGray-100 rounded-full" />;

  const towardPct = (toward / total) * 100;
  const awayPct = (away / total) * 100;
  const againstPct = (against / total) * 100;

  return (
    <div className="h-4 bg-warmGray-100 rounded-full overflow-hidden flex">
      <motion.div
        className="bg-emerald-400 h-full"
        initial={{ width: 0 }}
        animate={{ width: `${towardPct}%` }}
        transition={{ duration: 0.6, delay }}
      />
      <motion.div
        className="bg-warmGray-300 h-full"
        initial={{ width: 0 }}
        animate={{ width: `${awayPct}%` }}
        transition={{ duration: 0.6, delay: delay + 0.1 }}
      />
      <motion.div
        className="bg-red-400 h-full"
        initial={{ width: 0 }}
        animate={{ width: `${againstPct}%` }}
        transition={{ duration: 0.6, delay: delay + 0.2 }}
      />
    </div>
  );
};

export const BidResponseCard: React.FC<BidResponseProps> = ({
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
          <div className="p-2 rounded-xl bg-rose-50">
            <HandHeart size={18} className="text-rose-500" />
          </div>
          <h3 className="text-base font-semibold text-warmGray-700">Bid-Response Ratio</h3>
        </div>
        <p className="text-sm text-warmGray-400">No bid data available yet.</p>
      </motion.div>
    );
  }

  const { overall, per_partner } = data;
  const isMeetingBenchmark = overall.toward_rate >= overall.gottman_benchmark;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-2xl p-5 shadow-subtle"
    >
      <div className="flex items-center gap-2 mb-4">
        <div className="p-2 rounded-xl bg-rose-50">
          <HandHeart size={18} className="text-rose-500" />
        </div>
        <h3 className="text-base font-semibold text-warmGray-700">Bid-Response Ratio</h3>
      </div>

      {/* Overall score */}
      <div className="text-center mb-4">
        <motion.span
          className={`text-4xl font-bold ${isMeetingBenchmark ? 'text-emerald-600' : 'text-amber-600'}`}
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: delay + 0.2 }}
        >
          {overall.toward_rate}%
        </motion.span>
        <p className="text-xs text-warmGray-400 mt-1">
          turning toward bids (benchmark: {overall.gottman_benchmark}%)
        </p>

        {/* Benchmark indicator */}
        <div className="relative mt-2 h-2 bg-warmGray-100 rounded-full overflow-hidden">
          <motion.div
            className={`h-full rounded-full ${isMeetingBenchmark ? 'bg-emerald-400' : 'bg-amber-400'}`}
            initial={{ width: 0 }}
            animate={{ width: `${Math.min(overall.toward_rate, 100)}%` }}
            transition={{ duration: 0.8, delay: delay + 0.3 }}
          />
          {/* Benchmark line */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-warmGray-600"
            style={{ left: `${overall.gottman_benchmark}%` }}
          />
        </div>
      </div>

      {/* Overall breakdown */}
      <ResponseBar
        toward={overall.toward}
        away={overall.away}
        against={overall.against}
        total={overall.total_bids}
        delay={delay + 0.3}
      />
      <div className="flex items-center justify-between mt-2 text-xs text-warmGray-500">
        <span>Toward: {overall.toward}</span>
        <span>Away: {overall.away}</span>
        <span>Against: {overall.against}</span>
      </div>

      {/* Per-partner breakdown */}
      {Object.keys(per_partner).length > 0 && (
        <div className="mt-4 space-y-3">
          {per_partner['partner_a'] && (
            <div>
              <p className="text-xs font-medium text-warmGray-600 mb-1">
                {partnerAName}'s bids: {per_partner['partner_a'].toward_rate}% toward
              </p>
              <ResponseBar
                toward={per_partner['partner_a'].toward}
                away={per_partner['partner_a'].away}
                against={per_partner['partner_a'].against}
                total={per_partner['partner_a'].total_bids}
                delay={delay + 0.5}
              />
            </div>
          )}
          {per_partner['partner_b'] && (
            <div>
              <p className="text-xs font-medium text-warmGray-600 mb-1">
                {partnerBName}'s bids: {per_partner['partner_b'].toward_rate}% toward
              </p>
              <ResponseBar
                toward={per_partner['partner_b'].toward}
                away={per_partner['partner_b'].away}
                against={per_partner['partner_b'].against}
                total={per_partner['partner_b'].total_bids}
                delay={delay + 0.6}
              />
            </div>
          )}
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center gap-4 mt-3 text-[10px] text-warmGray-400">
        <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-emerald-400" /> Toward</div>
        <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-warmGray-300" /> Away</div>
        <div className="flex items-center gap-1"><div className="w-2 h-2 rounded-full bg-red-400" /> Against</div>
      </div>
    </motion.div>
  );
};

export default BidResponseCard;
