import React from 'react';
import { Calendar, Sparkles, CheckCircle, ArrowRight } from 'lucide-react';
import type { Digest } from '../../hooks/useDigests';

interface DigestCardProps {
  digest: Digest;
  onClick?: () => void;
  compact?: boolean;
}

const DigestCard: React.FC<DigestCardProps> = ({ digest, onClick, compact = false }) => {
  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  if (compact) {
    return (
      <div
        onClick={onClick}
        className="bg-surface-elevated rounded-xl p-4 border border-border-subtle hover:border-accent/30 cursor-pointer transition-all"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles size={16} className="text-accent" />
            <span className="text-small font-medium text-text-primary">
              Week of {formatDate(digest.week_start)}
            </span>
          </div>
          <ArrowRight size={14} className="text-text-tertiary" />
        </div>
        {digest.narrative && (
          <p className="text-tiny text-text-secondary mt-2 line-clamp-2">
            {digest.narrative.slice(0, 120)}...
          </p>
        )}
      </div>
    );
  }

  return (
    <div
      onClick={onClick}
      className="bg-surface-elevated rounded-2xl p-6 border border-border-subtle hover:border-accent/30 cursor-pointer transition-all"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Calendar size={18} className="text-accent" />
          <span className="text-body font-medium text-text-primary">
            {formatDate(digest.week_start)} - {formatDate(digest.week_end)}
          </span>
        </div>
        <div className="flex items-center gap-2 text-tiny text-text-tertiary">
          {digest.metrics?.conflict_count !== undefined && (
            <span>{digest.metrics.conflict_count} conflict{digest.metrics.conflict_count !== 1 ? 's' : ''}</span>
          )}
        </div>
      </div>

      {/* Narrative */}
      {digest.narrative && (
        <p className="text-small text-text-secondary mb-4 leading-relaxed">
          {digest.narrative}
        </p>
      )}

      {/* Highlights */}
      {digest.highlights && digest.highlights.length > 0 && (
        <div className="mb-4">
          <h4 className="text-tiny font-medium text-text-tertiary uppercase tracking-wider mb-2">Highlights</h4>
          <div className="space-y-1">
            {digest.highlights.map((h, i) => (
              <div key={i} className="flex items-start gap-2">
                <Sparkles size={12} className="text-amber-400 mt-1 flex-shrink-0" />
                <span className="text-small text-text-secondary">{h}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {digest.recommendations && digest.recommendations.length > 0 && (
        <div>
          <h4 className="text-tiny font-medium text-text-tertiary uppercase tracking-wider mb-2">Recommendations</h4>
          <div className="space-y-1">
            {digest.recommendations.map((r, i) => (
              <div key={i} className="flex items-start gap-2">
                <CheckCircle size={12} className="text-green-400 mt-1 flex-shrink-0" />
                <span className="text-small text-text-secondary">{r}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default DigestCard;
