import React from 'react';
import { motion } from 'framer-motion';
import { Target, AlertTriangle, User, Users } from 'lucide-react';
import { GlassCard } from './GlassCard';

interface TriggerSensitivity {
  trigger_category: string;
  trigger_description: string;
  sensitivity_score: number;
  reaction_type?: string;
  example_phrases?: string[];
}

interface TriggerSensitivityCardProps {
  partnerATriggers: TriggerSensitivity[];
  partnerBTriggers: TriggerSensitivity[];
  crossTriggerPatterns?: string[];
  partnerAName?: string;
  partnerBName?: string;
  currentPartner?: 'partner_a' | 'partner_b';
  delay?: number;
}

const categoryIcons: Record<string, string> = {
  criticism: '💬',
  dismissal: '🚫',
  past_reference: '⏪',
  tone: '🔊',
  interruption: '✋',
  topic_money: '💰',
  topic_family: '👨‍👩‍👧',
  topic_work: '💼',
  comparison: '⚖️',
  silence: '🤐',
};

const getSensitivityColor = (score: number) => {
  if (score >= 0.8) return 'bg-red-100 text-red-700 border-red-200';
  if (score >= 0.6) return 'bg-orange-100 text-orange-700 border-orange-200';
  if (score >= 0.4) return 'bg-yellow-100 text-yellow-700 border-yellow-200';
  return 'bg-green-100 text-green-700 border-green-200';
};

const getSensitivityLabel = (score: number) => {
  if (score >= 0.8) return 'Very High';
  if (score >= 0.6) return 'High';
  if (score >= 0.4) return 'Moderate';
  return 'Low';
};

export const TriggerSensitivityCard: React.FC<TriggerSensitivityCardProps> = ({
  partnerATriggers,
  partnerBTriggers,
  crossTriggerPatterns,
  partnerAName = 'Partner A',
  partnerBName = 'Partner B',
  currentPartner,
  delay = 0,
}) => {
  const [activeTab, setActiveTab] = React.useState<'partner_a' | 'partner_b' | 'patterns'>(
    currentPartner || 'partner_a'
  );

  const hasData = partnerATriggers.length > 0 || partnerBTriggers.length > 0;

  if (!hasData) {
    return (
      <GlassCard className="p-6" delay={delay}>
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 rounded-xl bg-amber-50">
            <Target size={20} className="text-amber-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-warmGray-800">Trigger Sensitivity</h3>
            <p className="text-xs text-warmGray-500">What triggers each partner</p>
          </div>
        </div>
        <div className="text-center py-8">
          <p className="text-warmGray-500">No trigger data available yet</p>
          <p className="text-xs text-warmGray-400 mt-1">Analyze more conflicts to identify patterns</p>
        </div>
      </GlassCard>
    );
  }

  const renderTriggers = (triggers: TriggerSensitivity[], isCurrentPartner: boolean) => {
    if (triggers.length === 0) {
      return <p className="text-warmGray-400 text-sm text-center py-4">No triggers identified yet</p>;
    }

    return (
      <div className="space-y-3">
        {triggers.sort((a, b) => b.sensitivity_score - a.sensitivity_score).map((trigger, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: delay + 0.1 + idx * 0.05 }}
            className={`p-4 rounded-xl transition-colors ${
              isCurrentPartner ? 'bg-rose-50/50 border border-rose-100' : 'bg-warmGray-50/50'
            }`}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-lg">{categoryIcons[trigger.trigger_category] || '⚡'}</span>
                <span className="font-medium text-warmGray-800 capitalize">
                  {trigger.trigger_category.replace('_', ' ')}
                </span>
              </div>
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${getSensitivityColor(trigger.sensitivity_score)}`}>
                {getSensitivityLabel(trigger.sensitivity_score)}
              </span>
            </div>

            <p className="text-sm text-warmGray-600 mb-2">{trigger.trigger_description}</p>

            {/* Sensitivity bar */}
            <div className="h-1.5 bg-warmGray-100 rounded-full overflow-hidden mb-2">
              <motion.div
                className={`h-full rounded-full ${
                  trigger.sensitivity_score >= 0.8 ? 'bg-red-400' :
                  trigger.sensitivity_score >= 0.6 ? 'bg-orange-400' :
                  trigger.sensitivity_score >= 0.4 ? 'bg-yellow-400' : 'bg-green-400'
                }`}
                initial={{ width: 0 }}
                animate={{ width: `${trigger.sensitivity_score * 100}%` }}
                transition={{ delay: delay + 0.2 + idx * 0.05, duration: 0.5 }}
              />
            </div>

            {/* Example phrases */}
            {trigger.example_phrases && trigger.example_phrases.length > 0 && (
              <div className="mt-2">
                <p className="text-xs text-warmGray-400 mb-1">Example triggers:</p>
                <div className="flex flex-wrap gap-1">
                  {trigger.example_phrases.slice(0, 3).map((phrase, i) => (
                    <span key={i} className="text-xs px-2 py-0.5 bg-warmGray-100 text-warmGray-600 rounded">
                      "{phrase}"
                    </span>
                  ))}
                </div>
              </div>
            )}

            {isCurrentPartner && (
              <div className="mt-2 text-xs text-rose-500 flex items-center gap-1">
                <AlertTriangle size={10} />
                <span>Your sensitivity</span>
              </div>
            )}
          </motion.div>
        ))}
      </div>
    );
  };

  return (
    <GlassCard className="p-6" delay={delay} hover={false}>
      <div className="flex items-center gap-3 mb-5">
        <div className="p-2.5 rounded-xl bg-amber-50">
          <Target size={20} className="text-amber-500" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-warmGray-800">Trigger Sensitivity</h3>
          <p className="text-xs text-warmGray-500">What triggers each partner and how they react</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-5 p-1 bg-warmGray-100 rounded-xl">
        <button
          onClick={() => setActiveTab('partner_a')}
          className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
            activeTab === 'partner_a'
              ? 'bg-white text-warmGray-800 shadow-sm'
              : 'text-warmGray-500 hover:text-warmGray-700'
          }`}
        >
          <User size={14} />
          {partnerAName}
          {currentPartner === 'partner_a' && <span className="text-[10px] text-rose-400">(You)</span>}
        </button>
        <button
          onClick={() => setActiveTab('partner_b')}
          className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
            activeTab === 'partner_b'
              ? 'bg-white text-warmGray-800 shadow-sm'
              : 'text-warmGray-500 hover:text-warmGray-700'
          }`}
        >
          <User size={14} />
          {partnerBName}
          {currentPartner === 'partner_b' && <span className="text-[10px] text-rose-400">(You)</span>}
        </button>
        {crossTriggerPatterns && crossTriggerPatterns.length > 0 && (
          <button
            onClick={() => setActiveTab('patterns')}
            className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
              activeTab === 'patterns'
                ? 'bg-white text-warmGray-800 shadow-sm'
                : 'text-warmGray-500 hover:text-warmGray-700'
            }`}
          >
            <Users size={14} />
            Patterns
          </button>
        )}
      </div>

      {/* Content */}
      <div className="max-h-[400px] overflow-y-auto">
        {activeTab === 'partner_a' && renderTriggers(partnerATriggers, currentPartner === 'partner_a')}
        {activeTab === 'partner_b' && renderTriggers(partnerBTriggers, currentPartner === 'partner_b')}
        {activeTab === 'patterns' && crossTriggerPatterns && (
          <div className="space-y-3">
            {crossTriggerPatterns.map((pattern, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: delay + 0.1 + idx * 0.1 }}
                className="p-4 rounded-xl bg-purple-50/50 border border-purple-100"
              >
                <div className="flex items-start gap-2">
                  <Users size={14} className="text-purple-500 mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-warmGray-700">{pattern}</p>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </GlassCard>
  );
};

export default TriggerSensitivityCard;
