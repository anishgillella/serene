import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { MediatorContextPanel } from '../components/MediatorContextPanel';


describe('MediatorContextPanel Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it('renders collapse button when closed', () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({})
    });

    const { container } = render(
      <MediatorContextPanel conflictId="test-123" isExpanded={false} />
    );

    const button = container.querySelector('button');
    expect(button).toBeInTheDocument();
  });

  it('fetches context on mount', async () => {
    const mockContext = {
      current_conflict: { topic: 'finances', resentment_level: 7 },
      escalation_risk: { score: 0.6, interpretation: 'high', is_critical: false }
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockContext
    });

    render(<MediatorContextPanel conflictId="test-123" isExpanded={true} />);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/mediator/context/test-123'),
        expect.any(Object)
      );
    });
  });

  it('displays escalation risk with correct color', async () => {
    const mockContext = {
      escalation_risk: {
        score: 0.8,
        interpretation: 'critical',
        is_critical: true
      }
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockContext
    });

    const { container } = render(
      <MediatorContextPanel conflictId="test-123" isExpanded={true} />
    );

    await waitFor(() => {
      expect(screen.getByText('CRITICAL RISK')).toBeInTheDocument();
    });

    const riskElement = screen.getByText('CRITICAL RISK').closest('div');
    expect(riskElement).toHaveClass('text-red-600');
  });

  it('displays chronic needs', async () => {
    const mockContext = {
      chronic_needs: ['feeling_heard', 'trust'],
      escalation_risk: { score: 0.5, interpretation: 'medium', is_critical: false }
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockContext
    });

    render(<MediatorContextPanel conflictId="test-123" isExpanded={true} />);

    await waitFor(() => {
      expect(screen.getByText(/feeling heard/i)).toBeInTheDocument();
      expect(screen.getByText(/trust/i)).toBeInTheDocument();
    });
  });

  it('displays unresolved issues count', async () => {
    const mockContext = {
      unresolved_issues: [
        { conflict_id: '1', topic: 'finances', days_unresolved: 5, resentment_level: 7 },
        { conflict_id: '2', topic: 'communication', days_unresolved: 3, resentment_level: 6 }
      ],
      escalation_risk: { score: 0.4, interpretation: 'medium', is_critical: false }
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockContext
    });

    render(<MediatorContextPanel conflictId="test-123" isExpanded={true} />);

    await waitFor(() => {
      expect(screen.getByText(/2 Unresolved Issues/)).toBeInTheDocument();
    });
  });

  it('displays escalation triggers', async () => {
    const mockContext = {
      high_impact_triggers: [
        { phrase: 'You never listen', category: 'blame', escalation_rate: 0.8 },
        { phrase: 'Always your fault', category: 'blame', escalation_rate: 0.75 }
      ],
      escalation_risk: { score: 0.5, interpretation: 'medium', is_critical: false }
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockContext
    });

    render(<MediatorContextPanel conflictId="test-123" isExpanded={true} />);

    await waitFor(() => {
      expect(screen.getByText(/You never listen/)).toBeInTheDocument();
    });
  });

  it('shows loading state initially', async () => {
    let resolveJson: any;
    const promise = new Promise(resolve => {
      resolveJson = resolve;
    });

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: () => promise
    });

    render(<MediatorContextPanel conflictId="test-123" isExpanded={true} />);

    expect(screen.getByText(/Loading context/i)).toBeInTheDocument();

    resolveJson({
      escalation_risk: { score: 0.5, interpretation: 'medium', is_critical: false }
    });

    await waitFor(() => {
      expect(screen.queryByText(/Loading context/i)).not.toBeInTheDocument();
    });
  });

  it('shows error message on fetch failure', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 500
    });

    render(<MediatorContextPanel conflictId="test-123" isExpanded={true} />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to fetch context/)).toBeInTheDocument();
    });
  });

  it('closes panel on close button click', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        escalation_risk: { score: 0.5, interpretation: 'medium', is_critical: false }
      })
    });

    const mockOnClose = vi.fn();

    const { container } = render(
      <MediatorContextPanel
        conflictId="test-123"
        isExpanded={true}
        onClose={mockOnClose}
      />
    );

    await waitFor(() => {
      const closeButton = container.querySelector('button[title="Show relationship context"]');
      if (closeButton) closeButton.click();
    });

    // Panel should close
    expect(mockOnClose).toHaveBeenCalled();
  });
});


describe('useLunaMediator Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it('enhances Luna response successfully', async () => {
    const mockEnhancement = {
      original_response: 'I hear you',
      suggestions: [
        { type: 'address_chronic_needs', message: 'Consider needs' }
      ],
      risk_warnings: [],
      context_applied: ['chronic_needs']
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockEnhancement
    });

    const { useLunaMediator } = await import('../hooks/useLunaMediator');

    let result: any;
    const TestComponent = () => {
      result = useLunaMediator();
      return null;
    };

    render(<TestComponent />);

    const enhancement = await result.enhanceResponse(
      'conflict-123',
      'I hear you',
      'Can we talk?'
    );

    expect(enhancement?.suggestions.length).toBe(1);
    expect(enhancement?.context_applied).toContain('chronic_needs');
  });

  it('detects risk warnings', async () => {
    const mockEnhancement = {
      original_response: 'response',
      suggestions: [],
      risk_warnings: [
        { type: 'critical_escalation', message: 'Critical', severity: 'high' }
      ],
      context_applied: ['escalation_risk']
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockEnhancement
    });

    const { useLunaMediator } = await import('../hooks/useLunaMediator');

    let result: any;
    const TestComponent = () => {
      result = useLunaMediator();
      return null;
    };

    render(<TestComponent />);

    await result.enhanceResponse('conflict-123', 'response');

    expect(result.hasRiskWarnings()).toBe(true);
    expect(result.getCriticalWarnings().length).toBe(1);
  });
});


describe('useConflictContext Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it('fetches conflict context', async () => {
    const mockContext = {
      current_conflict: { topic: 'finances', resentment_level: 7 },
      chronic_needs: ['feeling_heard'],
      escalation_risk: { score: 0.6, interpretation: 'high', is_critical: false }
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockContext
    });

    const { useConflictContext } = await import('../hooks/useConflictContext');

    let result: any;
    const TestComponent = () => {
      result = useConflictContext('conflict-123');
      return null;
    };

    render(<TestComponent />);

    await waitFor(() => {
      expect(result.context).not.toBeNull();
    });
  });

  it('identifies critical escalation', async () => {
    const mockContext = {
      escalation_risk: { score: 0.9, interpretation: 'critical', is_critical: true }
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockContext
    });

    const { useConflictContext } = await import('../hooks/useConflictContext');

    let result: any;
    const TestComponent = () => {
      result = useConflictContext('conflict-123');
      return null;
    };

    render(<TestComponent />);

    await waitFor(() => {
      expect(result.isCritical()).toBe(true);
    });
  });

  it('returns chronic needs list', async () => {
    const mockContext = {
      chronic_needs: ['feeling_heard', 'trust', 'respect'],
      escalation_risk: { score: 0.5, interpretation: 'medium', is_critical: false }
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockContext
    });

    const { useConflictContext } = await import('../hooks/useConflictContext');

    let result: any;
    const TestComponent = () => {
      result = useConflictContext('conflict-123');
      return null;
    };

    render(<TestComponent />);

    await waitFor(() => {
      expect(result.getChronicNeeds()).toHaveLength(3);
      expect(result.getChronicNeeds()).toContain('feeling_heard');
    });
  });

  it('counts unresolved issues', async () => {
    const mockContext = {
      unresolved_issues: [
        { conflict_id: '1', topic: 'finances', days_unresolved: 5, resentment_level: 7 },
        { conflict_id: '2', topic: 'communication', days_unresolved: 3, resentment_level: 6 }
      ],
      escalation_risk: { score: 0.4, interpretation: 'medium', is_critical: false }
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockContext
    });

    const { useConflictContext } = await import('../hooks/useConflictContext');

    let result: any;
    const TestComponent = () => {
      result = useConflictContext('conflict-123');
      return null;
    };

    render(<TestComponent />);

    await waitFor(() => {
      expect(result.getUnresolvedCount()).toBe(2);
    });
  });
});
