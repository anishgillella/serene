import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { EscalationRiskCard, TriggerPhraseTable, UnresolvedIssuesList, ChronicNeedsList } from '../components/analytics';
import ConflictAnalysis from '../pages/Analytics/ConflictAnalysis';
import TriggerPhrases from '../pages/Analytics/TriggerPhrases';


describe('EscalationRiskCard Component', () => {
  it('renders risk score with correct color for low risk', () => {
    const mockData = {
      risk_score: 0.2,
      interpretation: 'low',
      unresolved_issues: 0,
      days_until_predicted_conflict: 30,
      recommendations: []
    };

    render(<EscalationRiskCard data={mockData} />);

    const riskScore = screen.getByText('20%');
    expect(riskScore).toHaveClass('text-green-600');
  });

  it('renders risk score with correct color for high risk', () => {
    const mockData = {
      risk_score: 0.8,
      interpretation: 'critical',
      unresolved_issues: 5,
      days_until_predicted_conflict: 3,
      recommendations: []
    };

    render(<EscalationRiskCard data={mockData} />);

    const riskScore = screen.getByText('80%');
    expect(riskScore).toHaveClass('text-red-600');
  });

  it('displays unresolved issues count', () => {
    const mockData = {
      risk_score: 0.5,
      interpretation: 'medium',
      unresolved_issues: 3,
      days_until_predicted_conflict: 7,
      recommendations: []
    };

    render(<EscalationRiskCard data={mockData} />);

    expect(screen.getByText(/3.*unresolved issues/)).toBeInTheDocument();
  });

  it('displays days until predicted conflict', () => {
    const mockData = {
      risk_score: 0.4,
      interpretation: 'medium',
      unresolved_issues: 1,
      days_until_predicted_conflict: 14,
      recommendations: []
    };

    render(<EscalationRiskCard data={mockData} />);

    expect(screen.getByText('14')).toBeInTheDocument();
  });
});


describe('TriggerPhraseTable Component', () => {
  it('renders empty table when no phrases provided', () => {
    render(<TriggerPhraseTable phrases={[]} />);

    const table = screen.getByRole('table');
    expect(table).toBeInTheDocument();
  });

  it('renders trigger phrases with correct data', () => {
    const mockPhrases = [
      {
        phrase: 'You never listen',
        usage_count: 5,
        avg_emotional_intensity: 8,
        escalation_rate: 0.8,
        phrase_category: 'blame',
        speaker: 'partner_a'
      }
    ];

    render(<TriggerPhraseTable phrases={mockPhrases} />);

    expect(screen.getByText('"You never listen"')).toBeInTheDocument();
    expect(screen.getByText('5x')).toBeInTheDocument();
    expect(screen.getByText('80%')).toBeInTheDocument();
  });

  it('renders multiple phrases', () => {
    const mockPhrases = [
      {
        phrase: 'You never listen',
        usage_count: 5,
        avg_emotional_intensity: 8,
        escalation_rate: 0.8,
        phrase_category: 'blame'
      },
      {
        phrase: 'You always blame me',
        usage_count: 3,
        avg_emotional_intensity: 7,
        escalation_rate: 0.7,
        phrase_category: 'blame'
      }
    ];

    render(<TriggerPhraseTable phrases={mockPhrases} />);

    expect(screen.getByText('"You never listen"')).toBeInTheDocument();
    expect(screen.getByText('"You always blame me"')).toBeInTheDocument();
  });

  it('renders intensity bar with correct width', () => {
    const mockPhrases = [
      {
        phrase: 'Test phrase',
        usage_count: 2,
        avg_emotional_intensity: 5,
        escalation_rate: 0.5,
        phrase_category: 'test'
      }
    ];

    const { container } = render(<TriggerPhraseTable phrases={mockPhrases} />);

    const intensityBar = container.querySelector('.bg-red-500');
    expect(intensityBar).toHaveStyle({ width: '50%' });
  });
});


describe('UnresolvedIssuesList Component', () => {
  it('renders success message when no issues', () => {
    render(<UnresolvedIssuesList issues={[]} />);

    expect(screen.getByText('All issues resolved!')).toBeInTheDocument();
  });

  it('renders unresolved issues', () => {
    const mockIssues = [
      {
        conflict_id: '123',
        topic: 'finances',
        days_unresolved: 5,
        resentment_level: 7
      },
      {
        conflict_id: '456',
        topic: 'trust',
        days_unresolved: 10,
        resentment_level: 8
      }
    ];

    render(<UnresolvedIssuesList issues={mockIssues} />);

    expect(screen.getByText('finances')).toBeInTheDocument();
    expect(screen.getByText('trust')).toBeInTheDocument();
  });

  it('displays days unresolved correctly', () => {
    const mockIssues = [
      {
        conflict_id: '123',
        topic: 'finances',
        days_unresolved: 5,
        resentment_level: 7
      }
    ];

    render(<UnresolvedIssuesList issues={mockIssues} />);

    expect(screen.getByText(/Unresolved for 5 days/)).toBeInTheDocument();
  });

  it('displays resentment level', () => {
    const mockIssues = [
      {
        conflict_id: '123',
        topic: 'finances',
        days_unresolved: 5,
        resentment_level: 7
      }
    ];

    render(<UnresolvedIssuesList issues={mockIssues} />);

    expect(screen.getByText('Resentment: 7/10')).toBeInTheDocument();
  });
});


describe('ChronicNeedsList Component', () => {
  it('renders empty list when no needs', () => {
    render(<ChronicNeedsList needs={[]} />);

    const heading = screen.getByText('Chronic Unmet Needs');
    expect(heading).toBeInTheDocument();
  });

  it('renders chronic needs with data', () => {
    const mockNeeds = [
      {
        need: 'feeling_heard',
        conflict_count: 5,
        percentage_of_conflicts: 50
      },
      {
        need: 'trust',
        conflict_count: 4,
        percentage_of_conflicts: 40
      }
    ];

    render(<ChronicNeedsList needs={mockNeeds} />);

    expect(screen.getByText(/feeling heard/i)).toBeInTheDocument();
    expect(screen.getByText(/trust/i)).toBeInTheDocument();
  });

  it('displays conflict count and percentage', () => {
    const mockNeeds = [
      {
        need: 'feeling_heard',
        conflict_count: 5,
        percentage_of_conflicts: 50
      }
    ];

    render(<ChronicNeedsList needs={mockNeeds} />);

    expect(screen.getByText(/Appears in 5 conflicts \(50%\)/)).toBeInTheDocument();
  });

  it('renders progress bar with correct width', () => {
    const mockNeeds = [
      {
        need: 'feeling_heard',
        conflict_count: 5,
        percentage_of_conflicts: 75
      }
    ];

    const { container } = render(<ChronicNeedsList needs={mockNeeds} />);

    const progressBar = container.querySelector('.bg-purple-500');
    expect(progressBar).toHaveStyle({ width: '75%' });
  });

  it('formats need name by replacing underscores', () => {
    const mockNeeds = [
      {
        need: 'feeling_heard',
        conflict_count: 3,
        percentage_of_conflicts: 30
      }
    ];

    render(<ChronicNeedsList needs={mockNeeds} />);

    expect(screen.getByText(/feeling heard/)).toBeInTheDocument();
  });
});


describe('Analytics Pages', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders ConflictAnalysis page with loading state', () => {
    // Mock the hook to return loading state
    vi.mock('../../hooks/useAnalytics', () => ({
      useAnalyticsData: () => ({
        escalationRisk: null,
        unmetNeeds: [],
        loading: true,
        error: null,
        refresh: vi.fn()
      })
    }));

    render(<ConflictAnalysis />);

    expect(screen.getByText('Loading analysis...')).toBeInTheDocument();
  });

  it('renders TriggerPhrases page title', () => {
    vi.mock('../../hooks/useAnalytics', () => ({
      useAnalyticsData: () => ({
        triggerPhrases: null,
        loading: false,
        error: null,
        refresh: vi.fn()
      })
    }));

    render(<TriggerPhrases />);

    expect(screen.getByText('Trigger Phrase Analysis')).toBeInTheDocument();
  });
});
