import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Dashboard from '../Dashboard';
import { fetchDashboardData } from '../../services/apiRequests';

jest.mock('../../services/apiRequests', () => ({
  fetchDashboardData: jest.fn(),
  refreshDashboardCache: jest.fn(),
}));

jest.mock('../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

jest.mock('../../contexts/UserContext', () => ({
  useUser: () => ({
    user: { username: 'player1', preferences: { welcome_guide_seen: true } },
  }),
}));

jest.mock('../WelcomeGuide', () => () => null);

describe('Dashboard', () => {
  beforeEach(() => {
    fetchDashboardData.mockResolvedValue({
      total_games: 8,
      analyzed_games: 6,
      game_stats: { analyzed_games: 6 },
      win_rate: 55,
      average_accuracy: 71,
      recent_games: [
        {
          id: 1,
          opponent: 'Rival',
          platform: 'lichess',
          result: 'win',
          status: 'analyzed',
          opening_name: 'Sicilian',
          date_played: '2025-01-01T00:00:00Z',
        },
      ],
      nextAction: {
        type: 'start_batch_coach',
        title: 'Run Batch Coach on your games',
        description: 'You have 6 analyzed games ready for a coaching report.',
        ctaLabel: 'Start Batch Coach',
        ctaTo: '/batch-analysis',
        secondaryLinks: [],
      },
      focusInsight: {
        type: 'warning',
        text: 'Top focus area: opening preparation',
        href: '/games',
        actionLabel: 'View games',
      },
      heroMetrics: [{ label: 'Analyzed', value: '6 / 8' }],
      sinceLastVisit: { showBanner: false, summaryLines: [] },
      time_control_performance: { blitz: { total: 5, win_rate: 60 } },
      platform_stats: { lichess: { total: 8, win_rate: 55 } },
    });
  });

  it('renders streamlined dashboard sections', async () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Dashboard />
      </MemoryRouter>
    );

    expect(await screen.findByText('Run Batch Coach on your games')).toBeInTheDocument();
    expect(screen.getByText('Coach home')).toBeInTheDocument();
    const batchCoachLinks = screen.getAllByRole('link', { name: /Start Batch Coach/i });
    expect(batchCoachLinks.length).toBeGreaterThanOrEqual(1);
    expect(batchCoachLinks[0]).toHaveAttribute('href', '/batch-analysis');
    expect(screen.getByText('Your games')).toBeInTheDocument();
    expect(screen.getByText('Recent games')).toBeInTheDocument();
    expect(screen.getByText('vs Rival')).toBeInTheDocument();
    expect(screen.getByText('More stats')).toBeInTheDocument();
    expect(screen.queryByText('Quick Actions')).not.toBeInTheDocument();
    expect(screen.queryByText('Stats Overview')).not.toBeInTheDocument();
  });
});
