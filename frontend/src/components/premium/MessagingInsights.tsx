import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageCircle,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Smile,
  Frown,
  Meh,
  Bot,
  Calendar,
  Users,
  Shield
} from 'lucide-react';
import { GlassCard } from './GlassCard';
import { MetricCard } from './MetricCard';

interface MessagingAnalytics {
  period_days: number;
  total_messages: number;
  messages_by_partner: { partner_a: number; partner_b: number };
  sentiment_distribution: {
    positive: number;
    negative: number;
    neutral: number;
    positive_ratio: number;
  };
  average_sentiment: number;
  high_risk_messages: number;
  luna_interventions: number;
  daily_trend: { date: string; count: number; avg_sentiment: number }[];
  top_emotions: { emotion: string; count: number }[];
  top_triggers: { trigger: string; count: number }[];
  gottman_markers: {
    criticism: number;
    contempt: number;
    defensiveness: number;
    stonewalling: number;
  };
}

interface MessagingInsightsProps {
  relationshipId: string;
  partnerNames?: { partner_a: string; partner_b: string };
  delay?: number;
}

const emotionEmojis: Record<string, string> = {
  happy: '😊',
  loving: '❤️',
  hopeful: '🌟',
  grateful: '🙏',
  sad: '😢',
  hurt: '💔',
  frustrated: '😤',
  angry: '😠',
  anxious: '😰',
  worried: '😟',
  confused: '😕',
  tired: '😴'
};

export const MessagingInsights: React.FC<MessagingInsightsProps> = ({
  relationshipId,
  partnerNames = { partner_a: 'Partner A', partner_b: 'Partner B' },
  delay = 0
}) => {
  const [analytics, setAnalytics] = useState<MessagingAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState(30);

  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    const loadAnalytics = async () => {
      if (!relationshipId) return;

      setLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `${apiUrl}/api/partner-messages/analytics?relationship_id=${relationshipId}&days=${period}`
        );

        if (!response.ok) {
          throw new Error('Failed to load messaging analytics');
        }

        const data = await response.json();
        setAnalytics(data);
      } catch (err) {
        console.error('Failed to load messaging analytics:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    loadAnalytics();
  }, [relationshipId, period, apiUrl]);

  const getSentimentIcon = (score: number) => {
    if (score > 0.3) return <Smile size={18} className="text-emerald-500" />;
    if (score < -0.3) return <Frown size={18} className="text-rose-500" />;
    return <Meh size={18} className="text-amber-500" />;
  };

  const getSentimentColor = (score: number) => {
    if (score > 0.3) return 'text-emerald-600';
    if (score < -0.3) return 'text-rose-600';
    return 'text-amber-600';
  };

  const getEmotionEmoji = (emotion: string) => {
    return emotionEmojis[emotion.toLowerCase()] || '💬';
  };

  // Loading state
  if (loading) {
    return (
      <div className="space-y-4">
        <div className="animate-pulse bg-white/50 rounded-2xl h-32" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="animate-pulse bg-white/50 rounded-2xl h-28" />
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <GlassCard className="p-6 text-center" delay={delay}>
        <AlertTriangle className="mx-auto mb-3 text-amber-500" size={32} />
        <p className="text-warmGray-600">{error}</p>
      </GlassCard>
    );
  }

  // No data state
  if (!analytics || analytics.total_messages === 0) {
    return (
      <GlassCard className="p-8 text-center" delay={delay}>
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-lavender-100 flex items-center justify-center">
          <MessageCircle className="text-purple-500" size={32} />
        </div>
        <h3 className="text-lg font-semibold text-warmGray-800 mb-2">No Messages Yet</h3>
        <p className="text-warmGray-500 text-sm">
          Start chatting to see messaging insights and patterns.
        </p>
      </GlassCard>
    );
  }

  const totalGottman =
    analytics.gottman_markers.criticism +
    analytics.gottman_markers.contempt +
    analytics.gottman_markers.defensiveness +
    analytics.gottman_markers.stonewalling;

  return (
    <div className="space-y-6">
      {/* Period Selector */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay }}
        className="flex gap-2"
      >
        {[7, 30, 90].map((days) => (
          <motion.button
            key={days}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setPeriod(days)}
            className={`
              px-4 py-2 rounded-full text-sm font-medium transition-all
              ${period === days
                ? 'bg-purple-500 text-white shadow-md'
                : 'bg-white/70 text-warmGray-600 hover:bg-white/90 border border-white/50'
              }
            `}
          >
            {days === 7 ? '7 days' : days === 30 ? '30 days' : '90 days'}
          </motion.button>
        ))}
      </motion.div>

      {/* Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Total Messages"
          value={analytics.total_messages}
          icon={<MessageCircle size={18} />}
          color="lavender"
          delay={delay + 0.1}
        />

        <MetricCard
          label="Avg Sentiment"
          value={`${analytics.average_sentiment > 0 ? '+' : ''}${(analytics.average_sentiment * 100).toFixed(0)}%`}
          icon={getSentimentIcon(analytics.average_sentiment)}
          color={analytics.average_sentiment > 0 ? 'emerald' : analytics.average_sentiment < 0 ? 'rose' : 'amber'}
          delay={delay + 0.15}
        />

        <MetricCard
          label="High Risk"
          value={analytics.high_risk_messages}
          icon={<AlertTriangle size={18} />}
          color="amber"
          delay={delay + 0.2}
        />

        <MetricCard
          label="Luna Helped"
          value={analytics.luna_interventions}
          icon={<Bot size={18} />}
          color="blue"
          delay={delay + 0.25}
        />
      </div>

      {/* Partner Balance */}
      <GlassCard className="p-6" delay={delay + 0.3}>
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 rounded-xl bg-purple-50">
            <Users size={20} className="text-purple-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-warmGray-800">Message Balance</h3>
            <p className="text-xs text-warmGray-500">Who's initiating more conversations?</p>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-warmGray-700">{partnerNames.partner_a}</span>
            <span className="text-sm text-warmGray-500">{analytics.messages_by_partner.partner_a} messages</span>
          </div>
          <div className="h-3 bg-warmGray-100 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-purple-400 to-rose-400 rounded-full"
              initial={{ width: 0 }}
              animate={{
                width: `${(analytics.messages_by_partner.partner_a / analytics.total_messages) * 100}%`
              }}
              transition={{ duration: 0.8, delay: delay + 0.4 }}
            />
          </div>

          <div className="flex items-center justify-between mt-4">
            <span className="text-sm font-medium text-warmGray-700">{partnerNames.partner_b}</span>
            <span className="text-sm text-warmGray-500">{analytics.messages_by_partner.partner_b} messages</span>
          </div>
          <div className="h-3 bg-warmGray-100 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-blue-400 to-purple-400 rounded-full"
              initial={{ width: 0 }}
              animate={{
                width: `${(analytics.messages_by_partner.partner_b / analytics.total_messages) * 100}%`
              }}
              transition={{ duration: 0.8, delay: delay + 0.5 }}
            />
          </div>
        </div>
      </GlassCard>

      {/* Emotions & Triggers Grid */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Top Emotions */}
        <GlassCard className="p-6" delay={delay + 0.4}>
          <h3 className="text-base font-semibold text-warmGray-800 mb-4">Top Emotions</h3>
          {analytics.top_emotions.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {analytics.top_emotions.map((item, idx) => (
                <motion.div
                  key={item.emotion}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: delay + 0.5 + idx * 0.05 }}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-warmGray-50 rounded-full text-sm"
                >
                  <span>{getEmotionEmoji(item.emotion)}</span>
                  <span className="capitalize text-warmGray-700">{item.emotion}</span>
                  <span className="text-warmGray-400">({item.count})</span>
                </motion.div>
              ))}
            </div>
          ) : (
            <p className="text-warmGray-500 text-sm">No emotions detected yet</p>
          )}
        </GlassCard>

        {/* Top Triggers */}
        <GlassCard className="p-6" delay={delay + 0.45}>
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle size={16} className="text-amber-500" />
            <h3 className="text-base font-semibold text-warmGray-800">Trigger Phrases</h3>
          </div>
          {analytics.top_triggers.length > 0 ? (
            <div className="space-y-2">
              {analytics.top_triggers.slice(0, 5).map((item, idx) => (
                <motion.div
                  key={item.trigger}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: delay + 0.55 + idx * 0.05 }}
                  className="flex items-center justify-between p-3 bg-red-50 rounded-xl"
                >
                  <span className="text-sm text-red-700">"{item.trigger}"</span>
                  <span className="text-xs text-red-500 font-medium">{item.count}x</span>
                </motion.div>
              ))}
            </div>
          ) : (
            <p className="text-warmGray-500 text-sm">No triggers detected - that's great!</p>
          )}
        </GlassCard>
      </div>

      {/* Gottman Markers */}
      <GlassCard className="p-6" delay={delay + 0.5}>
        <div className="flex items-center gap-3 mb-5">
          <div className="p-2.5 rounded-xl bg-purple-50">
            <Shield size={20} className="text-purple-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-warmGray-800">Communication Patterns</h3>
            <p className="text-xs text-warmGray-500">Gottman's Four Horsemen detected in messages</p>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(analytics.gottman_markers).map(([marker, count], idx) => (
            <motion.div
              key={marker}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: delay + 0.6 + idx * 0.05 }}
              className={`
                p-4 rounded-xl text-center
                ${count > 0 ? 'bg-red-50' : 'bg-emerald-50'}
              `}
            >
              <p className={`text-2xl font-bold ${count > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                {count}
              </p>
              <p className="text-xs capitalize text-warmGray-600 mt-1">{marker}</p>
            </motion.div>
          ))}
        </div>

        <p className="text-xs text-warmGray-400 mt-4 text-center">
          The "Four Horsemen" are communication patterns that predict relationship problems.
          Lower numbers are better.
        </p>
      </GlassCard>

      {/* Sentiment Distribution */}
      <GlassCard className="p-6" delay={delay + 0.55}>
        <h3 className="text-base font-semibold text-warmGray-800 mb-4">Sentiment Distribution</h3>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <div className="flex h-4 rounded-full overflow-hidden bg-warmGray-100">
              <motion.div
                className="bg-emerald-400"
                initial={{ width: 0 }}
                animate={{
                  width: `${(analytics.sentiment_distribution.positive / analytics.total_messages) * 100}%`
                }}
                transition={{ duration: 0.8, delay: delay + 0.6 }}
              />
              <motion.div
                className="bg-warmGray-300"
                initial={{ width: 0 }}
                animate={{
                  width: `${(analytics.sentiment_distribution.neutral / analytics.total_messages) * 100}%`
                }}
                transition={{ duration: 0.8, delay: delay + 0.65 }}
              />
              <motion.div
                className="bg-rose-400"
                initial={{ width: 0 }}
                animate={{
                  width: `${(analytics.sentiment_distribution.negative / analytics.total_messages) * 100}%`
                }}
                transition={{ duration: 0.8, delay: delay + 0.7 }}
              />
            </div>
          </div>
        </div>
        <div className="flex justify-between mt-3 text-xs">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-emerald-400" />
            <span className="text-warmGray-600">Positive ({analytics.sentiment_distribution.positive})</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-warmGray-300" />
            <span className="text-warmGray-600">Neutral ({analytics.sentiment_distribution.neutral})</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-rose-400" />
            <span className="text-warmGray-600">Negative ({analytics.sentiment_distribution.negative})</span>
          </span>
        </div>
      </GlassCard>
    </div>
  );
};

export default MessagingInsights;
