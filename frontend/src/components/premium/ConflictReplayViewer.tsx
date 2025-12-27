import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  MessageCircle,
  AlertTriangle,
  Heart,
  Zap,
  Lightbulb,
  Shield,
  ChevronDown,
  ChevronUp,
  X
} from 'lucide-react';
import { GlassCard } from './GlassCard';

interface Annotation {
  id?: string;
  message_sequence_start: number;
  message_sequence_end?: number | null;
  annotation_type: string;
  annotation_title: string;
  annotation_text: string;
  suggested_alternative?: string | null;
  severity: string;
  related_horseman?: string | null;
}

interface ReplayMessage {
  sequence: number;
  speaker: string;
  content: string;
  timestamp?: string;
  emotional_intensity?: number | null;
  primary_emotion?: string | null;
  is_escalation?: boolean;
  is_repair_attempt?: boolean;
  annotations?: Annotation[];
}

interface ConflictReplayViewerProps {
  messages: ReplayMessage[];
  surfaceUnderlying?: Array<{
    surface_statement: string;
    underlying_concern: string;
    speaker: string;
  }>;
  partnerAName?: string;
  partnerBName?: string;
  delay?: number;
}

const annotationIcons: Record<string, React.ReactNode> = {
  escalation: <Zap size={14} className="text-red-500" />,
  repair_attempt: <Heart size={14} className="text-emerald-500" />,
  missed_bid: <AlertTriangle size={14} className="text-amber-500" />,
  horseman: <Shield size={14} className="text-red-600" />,
  breakthrough: <Heart size={14} className="text-green-500" />,
  suggestion: <Lightbulb size={14} className="text-blue-500" />,
  insight: <Lightbulb size={14} className="text-purple-500" />,
};

const severityColors: Record<string, string> = {
  critical: 'border-red-300 bg-red-50',
  warning: 'border-amber-300 bg-amber-50',
  positive: 'border-emerald-300 bg-emerald-50',
  info: 'border-blue-300 bg-blue-50',
};

export const ConflictReplayViewer: React.FC<ConflictReplayViewerProps> = ({
  messages,
  surfaceUnderlying = [],
  partnerAName = 'Partner A',
  partnerBName = 'Partner B',
  delay = 0,
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [expandedAnnotation, setExpandedAnnotation] = useState<string | null>(null);
  const [showAllMessages, setShowAllMessages] = useState(false);

  React.useEffect(() => {
    if (isPlaying && currentIndex < messages.length - 1) {
      const timer = setTimeout(() => {
        setCurrentIndex(prev => prev + 1);
      }, 2000);
      return () => clearTimeout(timer);
    } else if (currentIndex >= messages.length - 1) {
      setIsPlaying(false);
    }
  }, [isPlaying, currentIndex, messages.length]);

  if (!messages || messages.length === 0) {
    return (
      <GlassCard className="p-6" delay={delay}>
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 rounded-xl bg-blue-50">
            <Play size={20} className="text-blue-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-warmGray-800">Conflict Replay</h3>
            <p className="text-xs text-warmGray-500">Step through the conversation with insights</p>
          </div>
        </div>
        <div className="text-center py-8">
          <p className="text-warmGray-500">No replay data available</p>
        </div>
      </GlassCard>
    );
  }

  const currentMessage = messages[currentIndex];
  const speakerName = currentMessage.speaker === 'partner_a' ? partnerAName : partnerBName;
  const hasAnnotations = currentMessage.annotations && currentMessage.annotations.length > 0;

  const getIntensityColor = (intensity: number | null | undefined) => {
    if (!intensity) return 'bg-warmGray-100';
    if (intensity >= 8) return 'bg-red-400';
    if (intensity >= 6) return 'bg-orange-400';
    if (intensity >= 4) return 'bg-yellow-400';
    return 'bg-green-400';
  };

  return (
    <GlassCard className="p-6" delay={delay} hover={false}>
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-blue-50">
            <MessageCircle size={20} className="text-blue-500" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-warmGray-800">Conflict Replay</h3>
            <p className="text-xs text-warmGray-500">
              Message {currentIndex + 1} of {messages.length}
            </p>
          </div>
        </div>

        <button
          onClick={() => setShowAllMessages(!showAllMessages)}
          className="text-xs text-warmGray-500 hover:text-warmGray-700 flex items-center gap-1"
        >
          {showAllMessages ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          {showAllMessages ? 'Show current' : 'Show all'}
        </button>
      </div>

      {/* Progress bar */}
      <div className="mb-4">
        <div className="h-1.5 bg-warmGray-100 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-blue-400 rounded-full"
            animate={{ width: `${((currentIndex + 1) / messages.length) * 100}%` }}
          />
        </div>
        <div className="flex justify-between mt-1">
          {messages.map((msg, idx) => (
            <button
              key={idx}
              onClick={() => setCurrentIndex(idx)}
              className={`w-2 h-2 rounded-full transition-colors ${
                idx === currentIndex ? 'bg-blue-500' :
                idx < currentIndex ? 'bg-blue-200' :
                'bg-warmGray-200'
              } ${msg.is_escalation ? 'ring-2 ring-red-300' : ''} ${msg.is_repair_attempt ? 'ring-2 ring-green-300' : ''}`}
              style={{ visibility: messages.length > 20 && idx % Math.ceil(messages.length / 20) !== 0 ? 'hidden' : 'visible' }}
            />
          ))}
        </div>
      </div>

      {/* Playback controls */}
      <div className="flex items-center justify-center gap-4 mb-6">
        <button
          onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))}
          disabled={currentIndex === 0}
          className="p-2 rounded-full hover:bg-warmGray-100 disabled:opacity-30 transition-colors"
        >
          <SkipBack size={20} className="text-warmGray-600" />
        </button>
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className="p-3 rounded-full bg-blue-500 hover:bg-blue-600 text-white transition-colors"
        >
          {isPlaying ? <Pause size={24} /> : <Play size={24} />}
        </button>
        <button
          onClick={() => setCurrentIndex(Math.min(messages.length - 1, currentIndex + 1))}
          disabled={currentIndex === messages.length - 1}
          className="p-2 rounded-full hover:bg-warmGray-100 disabled:opacity-30 transition-colors"
        >
          <SkipForward size={20} className="text-warmGray-600" />
        </button>
      </div>

      {/* Messages display */}
      <AnimatePresence mode="wait">
        {showAllMessages ? (
          <motion.div
            key="all"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="max-h-[400px] overflow-y-auto space-y-3"
          >
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`p-3 rounded-xl cursor-pointer transition-all ${
                  idx === currentIndex ? 'ring-2 ring-blue-300' : ''
                } ${msg.speaker === 'partner_a' ? 'bg-blue-50/50' : 'bg-rose-50/50'}`}
                onClick={() => setCurrentIndex(idx)}
              >
                <div className="flex items-start gap-2">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                    msg.speaker === 'partner_a' ? 'bg-blue-200 text-blue-700' : 'bg-rose-200 text-rose-700'
                  }`}>
                    {msg.speaker === 'partner_a' ? 'A' : 'B'}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-warmGray-700">{msg.content}</p>
                    <div className="flex items-center gap-2 mt-1">
                      {msg.is_escalation && <Zap size={10} className="text-red-500" />}
                      {msg.is_repair_attempt && <Heart size={10} className="text-emerald-500" />}
                      {msg.annotations && msg.annotations.length > 0 && (
                        <span className="text-[10px] text-blue-500">{msg.annotations.length} annotations</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </motion.div>
        ) : (
          <motion.div
            key={currentIndex}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-4"
          >
            {/* Current message */}
            <div className={`p-5 rounded-2xl ${
              currentMessage.speaker === 'partner_a' ? 'bg-blue-50' : 'bg-rose-50'
            }`}>
              <div className="flex items-start gap-3">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-medium ${
                  currentMessage.speaker === 'partner_a' ? 'bg-blue-200 text-blue-700' : 'bg-rose-200 text-rose-700'
                }`}>
                  {currentMessage.speaker === 'partner_a' ? 'A' : 'B'}
                </div>
                <div className="flex-1">
                  <p className="font-medium text-warmGray-800 mb-1">{speakerName}</p>
                  <p className="text-warmGray-700">{currentMessage.content}</p>

                  {/* Emotional indicators */}
                  <div className="flex items-center gap-3 mt-3">
                    {currentMessage.emotional_intensity && (
                      <div className="flex items-center gap-1.5">
                        <div className={`w-2 h-2 rounded-full ${getIntensityColor(currentMessage.emotional_intensity)}`} />
                        <span className="text-xs text-warmGray-500">
                          Intensity: {currentMessage.emotional_intensity}/10
                        </span>
                      </div>
                    )}
                    {currentMessage.primary_emotion && (
                      <span className="text-xs text-warmGray-500 capitalize">
                        {currentMessage.primary_emotion}
                      </span>
                    )}
                    {currentMessage.is_escalation && (
                      <span className="text-xs text-red-500 flex items-center gap-1">
                        <Zap size={10} /> Escalation
                      </span>
                    )}
                    {currentMessage.is_repair_attempt && (
                      <span className="text-xs text-emerald-500 flex items-center gap-1">
                        <Heart size={10} /> Repair attempt
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Annotations for current message */}
            {hasAnnotations && (
              <div className="space-y-2">
                <p className="text-xs text-warmGray-400 font-medium">Insights for this moment:</p>
                {currentMessage.annotations!.map((annotation, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.1 }}
                    className={`p-3 rounded-xl border ${severityColors[annotation.severity] || 'border-warmGray-200 bg-warmGray-50'}`}
                  >
                    <div
                      className="flex items-start gap-2 cursor-pointer"
                      onClick={() => setExpandedAnnotation(
                        expandedAnnotation === `${currentIndex}-${idx}` ? null : `${currentIndex}-${idx}`
                      )}
                    >
                      {annotationIcons[annotation.annotation_type] || <Lightbulb size={14} className="text-warmGray-400" />}
                      <div className="flex-1">
                        <p className="font-medium text-sm text-warmGray-800">{annotation.annotation_title}</p>
                        <AnimatePresence>
                          {expandedAnnotation === `${currentIndex}-${idx}` && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: 'auto', opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              className="overflow-hidden"
                            >
                              <p className="text-sm text-warmGray-600 mt-2">{annotation.annotation_text}</p>
                              {annotation.suggested_alternative && (
                                <div className="mt-2 p-2 bg-white/50 rounded-lg">
                                  <p className="text-xs text-warmGray-400 mb-1">Could have said:</p>
                                  <p className="text-sm text-emerald-700 italic">"{annotation.suggested_alternative}"</p>
                                </div>
                              )}
                              {annotation.related_horseman && (
                                <div className="mt-2 flex items-center gap-1">
                                  <Shield size={10} className="text-red-500" />
                                  <span className="text-xs text-red-600 capitalize">{annotation.related_horseman}</span>
                                </div>
                              )}
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                      <ChevronDown
                        size={14}
                        className={`text-warmGray-400 transition-transform ${
                          expandedAnnotation === `${currentIndex}-${idx}` ? 'rotate-180' : ''
                        }`}
                      />
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </GlassCard>
  );
};

export default ConflictReplayViewer;
