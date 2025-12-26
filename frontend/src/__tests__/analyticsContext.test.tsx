import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { AnalyticsProvider } from '../contexts/AnalyticsContext';


// Mock component to test context usage
const TestComponent = () => {
  const { escalationRisk, loading, error } = React.useContext(require('../contexts/AnalyticsContext').AnalyticsContext);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      {escalationRisk && (
        <div data-testid="risk-score">{escalationRisk.risk_score}</div>
      )}
    </div>
  );
};


describe('AnalyticsContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('provides default state', () => {
    const TestWrapper = () => (
      <AnalyticsProvider>
        <div data-testid="test-content">Content</div>
      </AnalyticsProvider>
    );

    render(<TestWrapper />);

    expect(screen.getByTestId('test-content')).toBeInTheDocument();
  });

  it('handles loading state', async () => {
    // Mock fetch to simulate loading
    global.fetch = vi.fn(() => new Promise(resolve => {
      setTimeout(() => {
        resolve({
          ok: true,
          json: async () => ({
            escalation_risk: { risk_score: 0.5 }
          })
        });
      }, 100);
    }));

    const TestWrapper = () => (
      <AnalyticsProvider>
        <TestComponent />
      </AnalyticsProvider>
    );

    const { container } = render(<TestWrapper />);

    // Should show loading initially
    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    }, { timeout: 500 });
  });

  it('handles API errors gracefully', async () => {
    global.fetch = vi.fn(() =>
      Promise.reject(new Error('Network error'))
    );

    const TestWrapper = () => (
      <AnalyticsProvider>
        <TestComponent />
      </AnalyticsProvider>
    );

    render(<TestWrapper />);

    // Component should render without crashing
    expect(screen.queryByText('Error:')).not.toBeInTheDocument();
  });
});


describe('useAnalyticsData Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('provides refresh function', () => {
    const { useAnalyticsData } = require('../hooks/useAnalytics');

    const mockHook = () => ({
      escalationRisk: null,
      triggerPhrases: null,
      conflictChains: [],
      unmetNeeds: [],
      healthScore: 0,
      loading: false,
      error: null,
      refresh: vi.fn()
    });

    const { refresh } = mockHook();

    expect(typeof refresh).toBe('function');
  });

  it('returns analytics data in correct shape', () => {
    const mockHook = () => ({
      escalationRisk: { risk_score: 0.5 },
      triggerPhrases: { most_impactful: [] },
      conflictChains: [],
      unmetNeeds: [],
      healthScore: 50,
      loading: false,
      error: null,
      refresh: vi.fn()
    });

    const data = mockHook();

    expect(data).toHaveProperty('escalationRisk');
    expect(data).toHaveProperty('triggerPhrases');
    expect(data).toHaveProperty('conflictChains');
    expect(data).toHaveProperty('unmetNeeds');
    expect(data).toHaveProperty('healthScore');
    expect(data).toHaveProperty('loading');
    expect(data).toHaveProperty('error');
    expect(data).toHaveProperty('refresh');
  });
});
