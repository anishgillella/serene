import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import {
  HealthScore,
  RiskMetrics,
  MetricsOverview,
  ConflictTrends,
  TriggerPhraseHeatmap,
  UnmetNeedsAnalysis,
  RecommendationsPanel,
  InsightsPanel
} from '../components/dashboard';
import Dashboard from '../pages/Analytics/Dashboard';


describe('Dashboard Components', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  describe('HealthScore Component', () => {
    it('renders health score value', () => {
      const mockData = {
        value: 75,
        trend: 'up',
        breakdownFactors: {
          unresolved_issues: 0.2,
          conflict_frequency: 0.3,
          escalation_risk: 0.4,
          resentment_level: 5
        }
      };

      render(<HealthScore data={mockData} />);

      expect(screen.getByText('75')).toBeInTheDocument();
      expect(screen.getByText('/ 100')).toBeInTheDocument();
    });

    it('displays trend indicator', () => {
      const mockData = {
        value: 60,
        trend: 'down',
        breakdownFactors: {
          unresolved_issues: 0.4,
          conflict_frequency: 0.5,
          escalation_risk: 0.6,
          resentment_level: 7
        }
      };

      render(<HealthScore data={mockData} />);

      expect(screen.getByText(/down.*Trend/i)).toBeInTheDocument();
    });

    it('shows unresolved issues breakdown', () => {
      const mockData = {
        value: 50,
        trend: 'stable',
        breakdownFactors: {
          unresolved_issues: 0.6,
          conflict_frequency: 0.5,
          escalation_risk: 0.5,
          resentment_level: 6
        }
      };

      render(<HealthScore data={mockData} />);

      expect(screen.getByText('Unresolved Issues')).toBeInTheDocument();
    });
  });

  describe('RiskMetrics Component', () => {
    it('renders escalation risk percentage', () => {
      const mockData = {
        risk_score: 0.7,
        interpretation: 'high',
        unresolved_issues: 3,
        days_until_predicted_conflict: 7
      };

      render(<RiskMetrics data={mockData} />);

      expect(screen.getByText('70%')).toBeInTheDocument();
    });

    it('displays critical risk level', () => {
      const mockData = {
        risk_score: 0.9,
        interpretation: 'critical',
        unresolved_issues: 5,
        days_until_predicted_conflict: 1
      };

      render(<RiskMetrics data={mockData} />);

      expect(screen.getByText('CRITICAL')).toBeInTheDocument();
    });

    it('shows unresolved issues count', () => {
      const mockData = {
        risk_score: 0.5,
        interpretation: 'medium',
        unresolved_issues: 2,
        days_until_predicted_conflict: 14
      };

      render(<RiskMetrics data={mockData} />);

      expect(screen.getByText('2')).toBeInTheDocument();
    });
  });

  describe('MetricsOverview Component', () => {
    it('displays total conflicts', () => {
      const mockData = {
        total_conflicts: 10,
        resolved_conflicts: 7,
        unresolved_conflicts: 3,
        resolution_rate: 70,
        avg_resentment: 6,
        days_since_last_conflict: 5
      };

      render(<MetricsOverview data={mockData} />);

      expect(screen.getByText('10')).toBeInTheDocument();
    });

    it('shows resolution rate', () => {
      const mockData = {
        total_conflicts: 10,
        resolved_conflicts: 8,
        unresolved_conflicts: 2,
        resolution_rate: 80,
        avg_resentment: 5,
        days_since_last_conflict: 3
      };

      render(<MetricsOverview data={mockData} />);

      expect(screen.getByText('80%')).toBeInTheDocument();
    });

    it('displays average resentment', () => {
      const mockData = {
        total_conflicts: 5,
        resolved_conflicts: 4,
        unresolved_conflicts: 1,
        resolution_rate: 80,
        avg_resentment: 7.5,
        days_since_last_conflict: 10
      };

      render(<MetricsOverview data={mockData} />);

      expect(screen.getByText('7.5/10')).toBeInTheDocument();
    });
  });

  describe('TriggerPhraseHeatmap Component', () => {
    it('renders trigger phrases', () => {
      const mockData = {
        most_impactful: [
          {
            phrase: 'You never listen',
            usage_count: 5,
            escalation_rate: 0.8
          }
        ]
      };

      render(<TriggerPhraseHeatmap data={mockData} />);

      expect(screen.getByText(/You never listen/)).toBeInTheDocument();
    });

    it('shows escalation percentage', () => {
      const mockData = {
        most_impactful: [
          {
            phrase: 'Always your fault',
            usage_count: 3,
            escalation_rate: 0.75
          }
        ]
      };

      render(<TriggerPhraseHeatmap data={mockData} />);

      expect(screen.getByText('75%')).toBeInTheDocument();
    });

    it('shows empty state when no phrases', () => {
      const mockData = {
        most_impactful: []
      };

      render(<TriggerPhraseHeatmap data={mockData} />);

      expect(screen.getByText(/No trigger phrases identified/)).toBeInTheDocument();
    });
  });

  describe('UnmetNeedsAnalysis Component', () => {
    it('displays chronic unmet needs', () => {
      const mockData = [
        {
          need: 'feeling_heard',
          conflict_count: 8,
          percentage_of_conflicts: 80
        }
      ];

      render(<UnmetNeedsAnalysis data={mockData} />);

      expect(screen.getByText(/feeling heard/i)).toBeInTheDocument();
    });

    it('shows conflict count', () => {
      const mockData = [
        {
          need: 'trust',
          conflict_count: 5,
          percentage_of_conflicts: 50
        }
      ];

      render(<UnmetNeedsAnalysis data={mockData} />);

      expect(screen.getByText('5x')).toBeInTheDocument();
    });

    it('shows empty state when no needs', () => {
      const mockData: any[] = [];

      render(<UnmetNeedsAnalysis data={mockData} />);

      expect(screen.getByText(/No chronic needs identified/)).toBeInTheDocument();
    });
  });

  describe('RecommendationsPanel Component', () => {
    it('displays recommendations', () => {
      const mockData = {
        recommendations: [
          'Schedule mediation',
          'Address unresolved issues'
        ],
        interpretation: 'high'
      };

      render(<RecommendationsPanel data={mockData} />);

      expect(screen.getByText('Schedule mediation')).toBeInTheDocument();
    });

    it('shows risk level', () => {
      const mockData = {
        recommendations: [],
        interpretation: 'critical'
      };

      render(<RecommendationsPanel data={mockData} />);

      expect(screen.getByText('CRITICAL')).toBeInTheDocument();
    });
  });

  describe('InsightsPanel Component', () => {
    it('displays insights', () => {
      const mockData = {
        insights: ['Excellent resolution rate'],
        metrics: {
          total_conflicts: 5,
          resolved_conflicts: 4,
          resolution_rate: 80,
          avg_resentment: 5,
          days_since_last_conflict: 20
        },
        escalationRisk: {
          interpretation: 'low'
        }
      };

      render(
        <InsightsPanel
          insights={mockData.insights}
          metrics={mockData.metrics}
          escalationRisk={mockData.escalationRisk}
        />
      );

      expect(screen.getByText(/Key Insights/)).toBeInTheDocument();
    });

    it('generates custom insights', () => {
      const mockData = {
        insights: [],
        metrics: {
          total_conflicts: 0,
          resolved_conflicts: 0,
          resolution_rate: 0,
          avg_resentment: 1,
          days_since_last_conflict: 100
        },
        escalationRisk: {
          interpretation: 'low'
        }
      };

      render(
        <InsightsPanel
          insights={mockData.insights}
          metrics={mockData.metrics}
          escalationRisk={mockData.escalationRisk}
        />
      );

      expect(screen.getByText(/No conflicts recorded yet/)).toBeInTheDocument();
    });
  });
});

describe('Dashboard Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it('shows loading state initially', () => {
    let resolveJson: any;
    const promise = new Promise(resolve => {
      resolveJson = resolve;
    });

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: () => promise
    });

    render(<Dashboard />);

    expect(screen.getByText(/Loading relationship analytics/)).toBeInTheDocument();

    resolveJson({
      health_score: { value: 70 },
      escalation_risk: { interpretation: 'medium' },
      trigger_phrases: { most_impactful: [] },
      conflict_chains: [],
      chronic_needs: [],
      metrics: {},
      insights: []
    });
  });

  it('displays dashboard title', async () => {
    const mockDashboard = {
      health_score: { value: 75, trend: 'up', breakdownFactors: {} },
      escalation_risk: { interpretation: 'medium', risk_score: 0.5 },
      trigger_phrases: { most_impactful: [] },
      conflict_chains: [],
      chronic_needs: [],
      metrics: {
        total_conflicts: 10,
        resolved_conflicts: 8,
        resolution_rate: 80,
        avg_resentment: 5,
        days_since_last_conflict: 5,
        unresolved_conflicts: 2
      },
      insights: []
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockDashboard
    });

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText(/Relationship Dashboard/)).toBeInTheDocument();
    });
  });

  it('shows error message on fetch failure', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 500
    });

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText(/Error Loading Dashboard/)).toBeInTheDocument();
    });
  });

  it('has refresh button', () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        health_score: { value: 70 },
        escalation_risk: { interpretation: 'medium' },
        trigger_phrases: { most_impactful: [] },
        conflict_chains: [],
        chronic_needs: [],
        metrics: {},
        insights: []
      })
    });

    render(<Dashboard />);

    expect(screen.getByText('Refresh')).toBeInTheDocument();
  });
});

describe('useDashboardData Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it('fetches dashboard data', async () => {
    const mockData = {
      health_score: { value: 80 },
      escalation_risk: { interpretation: 'low' },
      trigger_phrases: { most_impactful: [] },
      conflict_chains: [],
      chronic_needs: [],
      metrics: {},
      insights: []
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockData
    });

    const { useDashboardData } = await import('../hooks/useDashboardData');

    let result: any;
    const TestComponent = () => {
      result = useDashboardData('relationship-123');
      return null;
    };

    render(<TestComponent />);

    await result.refresh();

    expect(result.dashboardData).not.toBeNull();
  });

  it('gets health status correctly', async () => {
    const { useDashboardData } = await import('../hooks/useDashboardData');

    let result: any;
    const TestComponent = () => {
      result = useDashboardData('relationship-123');
      result.dashboardData = { health_score: { value: 85 } };
      return null;
    };

    render(<TestComponent />);

    expect(result.getHealthStatus()).toBe('excellent');
  });
});
