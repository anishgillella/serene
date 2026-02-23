import React from 'react';
import { AlertTriangle, Clock, Heart, MessageCircle, X, BellOff } from 'lucide-react';
import type { Alert } from '../../hooks/useAlerts';

interface AlertCardProps {
  alert: Alert;
  onDismiss: (id: string) => void;
  onSnooze: (id: string, hours: number) => void;
}

const alertTypeConfig: Record<string, { icon: React.ElementType; color: string; bg: string }> = {
  tension_rising: { icon: AlertTriangle, color: 'text-amber-500', bg: 'bg-amber-500/10' },
  recurring_trigger: { icon: MessageCircle, color: 'text-red-400', bg: 'bg-red-400/10' },
  cool_down_reminder: { icon: Clock, color: 'text-blue-400', bg: 'bg-blue-400/10' },
  check_in_prompt: { icon: Heart, color: 'text-pink-400', bg: 'bg-pink-400/10' },
};

const severityBorder: Record<string, string> = {
  high: 'border-red-400/30',
  medium: 'border-amber-400/30',
  low: 'border-border-subtle',
};

const AlertCard: React.FC<AlertCardProps> = ({ alert, onDismiss, onSnooze }) => {
  const config = alertTypeConfig[alert.alert_type] || alertTypeConfig.check_in_prompt;
  const Icon = config.icon;
  const borderClass = severityBorder[alert.severity] || severityBorder.low;

  const formatTime = (dateStr: string | null) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${Math.floor(diffHours / 24)}d ago`;
  };

  return (
    <div className={`bg-surface-elevated rounded-2xl p-5 border ${borderClass} transition-all`}>
      <div className="flex items-start gap-4">
        <div className={`w-10 h-10 rounded-full ${config.bg} flex items-center justify-center flex-shrink-0`}>
          <Icon size={20} className={config.color} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <h4 className="text-small font-medium text-text-primary">{alert.title}</h4>
            <span className="text-tiny text-text-tertiary">{formatTime(alert.created_at)}</span>
          </div>
          <p className="text-small text-text-secondary mb-3">{alert.message}</p>

          <div className="flex items-center gap-3">
            <button
              onClick={() => onDismiss(alert.id)}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-tiny font-medium text-text-secondary hover:bg-surface-hover transition-colors"
            >
              <X size={12} />
              Dismiss
            </button>
            <button
              onClick={() => onSnooze(alert.id, 4)}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-tiny font-medium text-text-secondary hover:bg-surface-hover transition-colors"
            >
              <BellOff size={12} />
              Snooze 4h
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AlertCard;
