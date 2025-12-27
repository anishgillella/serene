import { useState, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Types
interface SurfaceUnderlyingMapping {
  surface_statement: string;
  surface_category: string;
  underlying_concern: string;
  underlying_emotion: string;
  underlying_need: string;
  speaker: string;
  confidence: number;
}

interface EmotionalMoment {
  message_sequence: number;
  speaker: string;
  emotional_intensity: number;
  negativity_score?: number;
  primary_emotion: string;
  is_escalation_point: boolean;
  is_repair_attempt: boolean;
  is_de_escalation: boolean;
  moment_note?: string;
}

interface TriggerSensitivity {
  trigger_category: string;
  trigger_description: string;
  sensitivity_score: number;
  reaction_type?: string;
  example_phrases?: string[];
}

interface Annotation {
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

// Hook for Surface vs Underlying analysis
export const useSurfaceUnderlying = (relationshipId: string) => {
  const [data, setData] = useState<{
    mappings: SurfaceUnderlyingMapping[];
    overallPattern?: string;
    keyInsight?: string;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async (conflictId: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/api/analytics/advanced/surface-underlying/${conflictId}?relationship_id=${relationshipId}`,
        { headers: { 'ngrok-skip-browser-warning': 'true' } }
      );
      if (!response.ok) throw new Error('Failed to fetch surface/underlying analysis');
      const result = await response.json();
      setData({
        mappings: result.mappings || [],
        overallPattern: result.overall_pattern,
        keyInsight: result.key_insight
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [relationshipId]);

  return { data, loading, error, fetch };
};

// Hook for Emotional Timeline
export const useEmotionalTimeline = (relationshipId: string) => {
  const [data, setData] = useState<{
    moments: EmotionalMoment[];
    summary?: {
      peak_intensity?: number;
      peak_moment?: number;
      peak_emotion?: string;
      total_escalations?: number;
      total_repair_attempts?: number;
      emotional_arc?: string;
    };
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTimeline = useCallback(async (conflictId: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await window.fetch(
        `${API_BASE}/api/analytics/advanced/emotional-timeline/${conflictId}?relationship_id=${relationshipId}`,
        { headers: { 'ngrok-skip-browser-warning': 'true' } }
      );
      if (!response.ok) throw new Error('Failed to fetch emotional timeline');
      const result = await response.json();
      setData({
        moments: result.moments || [],
        summary: result.summary
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [relationshipId]);

  return { data, loading, error, fetchTimeline };
};

// Hook for Trigger Sensitivity
export const useTriggerSensitivity = (relationshipId: string) => {
  const [data, setData] = useState<{
    partnerATriggers: TriggerSensitivity[];
    partnerBTriggers: TriggerSensitivity[];
    crossTriggerPatterns?: string[];
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSensitivity = useCallback(async (refresh = false) => {
    setLoading(true);
    setError(null);
    try {
      const response = await window.fetch(
        `${API_BASE}/api/analytics/advanced/trigger-sensitivity?relationship_id=${relationshipId}&refresh=${refresh}`,
        { headers: { 'ngrok-skip-browser-warning': 'true' } }
      );
      if (!response.ok) throw new Error('Failed to fetch trigger sensitivity');
      const result = await response.json();
      setData({
        partnerATriggers: result.partner_a_triggers || [],
        partnerBTriggers: result.partner_b_triggers || [],
        crossTriggerPatterns: result.cross_trigger_patterns
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [relationshipId]);

  return { data, loading, error, fetchSensitivity };
};

// Hook for Conflict Replay
export const useConflictReplay = (relationshipId: string) => {
  const [data, setData] = useState<{
    messages: ReplayMessage[];
    surfaceUnderlying?: Array<{
      surface_statement: string;
      underlying_concern: string;
      speaker: string;
    }>;
    summary?: {
      total_messages: number;
      has_emotional_data: boolean;
      has_annotations: boolean;
      annotation_count: number;
    };
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchReplay = useCallback(async (conflictId: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await window.fetch(
        `${API_BASE}/api/analytics/advanced/conflict-replay/${conflictId}?relationship_id=${relationshipId}`,
        { headers: { 'ngrok-skip-browser-warning': 'true' } }
      );
      if (!response.ok) throw new Error('Failed to fetch conflict replay');
      const result = await response.json();
      setData({
        messages: result.messages || [],
        surfaceUnderlying: result.surface_underlying,
        summary: result.summary
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [relationshipId]);

  // Run full analysis on a conflict
  const runFullAnalysis = useCallback(async (conflictId: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await window.fetch(
        `${API_BASE}/api/analytics/advanced/analyze-conflict/${conflictId}?relationship_id=${relationshipId}`,
        {
          method: 'POST',
          headers: { 'ngrok-skip-browser-warning': 'true' }
        }
      );
      if (!response.ok) throw new Error('Failed to run analysis');
      const result = await response.json();
      // Refresh replay data after analysis
      if (result.success) {
        await fetchReplay(conflictId);
      }
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [relationshipId, fetchReplay]);

  return { data, loading, error, fetchReplay, runFullAnalysis };
};

// Hook for Emotional Trends (across conflicts)
export const useEmotionalTrends = (relationshipId: string) => {
  const [data, setData] = useState<Array<{
    period: string;
    conflicts_count: number;
    avg_intensity?: number;
    peak_intensity?: number;
    total_escalations?: number;
    total_repair_attempts?: number;
    intensity_trend?: string;
  }> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTrends = useCallback(async (periodType = 'weekly', periods = 8) => {
    setLoading(true);
    setError(null);
    try {
      const response = await window.fetch(
        `${API_BASE}/api/analytics/advanced/emotional-trends?relationship_id=${relationshipId}&period_type=${periodType}&periods=${periods}`,
        { headers: { 'ngrok-skip-browser-warning': 'true' } }
      );
      if (!response.ok) throw new Error('Failed to fetch emotional trends');
      const result = await response.json();
      setData(result.trends || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [relationshipId]);

  return { data, loading, error, fetchTrends };
};
