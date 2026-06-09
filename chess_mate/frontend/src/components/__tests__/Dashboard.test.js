import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Dashboard from '../Dashboard';
import { fetchDashboardData, fetchNotifications } from '../../services/apiRequests';

jest.mock('../../services/apiRequests', () => ({
  fetchDashboardData: jest.fn(),
  refreshDashboardCache: jest.fn(),
  fetchNotifications: jest.fn(),
  patchNotifications: jest.fn(),
}));

jest.mock('../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

const mockUser = {
  username: 'player1',
  preferences: { welcome_guide_seen: true },
};

jest.mock('../../contexts/UserContext', () => ({
  useUser: () => ({ user: mockUser }),
}));

jest.mock('../WelcomeGuide', () => () => null);
jest.mock('../PwaInstallPrompt', () => () => null);

const coachReadyPayload = {
  total_games: 8,
  analyzed_games: 6,
  batches_completed: 0,
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
  priority_inbox: {
    pending_count: 0,
    pending_items: [],
    empty_state_cta: '/batch-analysis',
    empty_state_label: 'Start Batch Coach',
  },
  time_control_performance: { blitz: { total: 5, win_rate: 60 } },
  platform_stats: { lichess: { total: 8, win_rate: 55 } },
};

const coachActivePayload = {
  ...coachReadyPayload,
  batches_completed: 2,
  latest_batch_coach: {
    batch_id: 42,
    summary: 'Focus on hanging pieces in the middlegame.',
    games_count: 10,
    overall_accuracy_pct: 68.4,
  },
  nextAction: {
    type: 'open_batch_report',
    title: 'Pick up your latest coach report',
    description: 'Focus on hanging pieces in the middlegame.',
    ctaLabel: 'Open report',
    ctaTo: '/batch-report/42',
    secondaryLinks: [],
  },
  focusInsight: {
    type: 'warning',
    text: 'Top focus area: opening preparation',
    href: '/batch-report/42',
    actionLabel: 'Open report',
  },
  sinceLastVisit: {
    showBanner: true,
    summaryLines: ['1 batch completed', '2 inbox items reviewed'],
  },
  priority_inbox: {
    pending_count: 2,
    pending_items: [
      {
        id: '42:1',
        batch_id: 42,
        priority_index: 1,
        title: 'Stop hanging pieces',
        href: '/batch-report/42',
      },
    ],
  },
  oneThingToday: {
    headline: 'Review hanging piece drill',
    subline: '5 min from your latest batch',
    ctaLabel: 'Start drill',
    ctaTo: '/game/99/analysis?batch=42&mode=review',
    source: 'inbox',
  },
  fix_rate: {
    show: true,
    fixed_count: 2,
    total_count: 3,
    headline: 'You fixed 2/3 patterns from your January batch.',
    patterns: [],
  },
  phase_heatmap: { show: true, analyzed_games: 10, cells: [], results: ['win'], phases: ['opening'] },
};

describe('Dashboard', () => {
  beforeEach(() => {
    fetchNotifications.mockResolvedValue({ unread_count: 0, notifications: [] });
    fetchDashboardData.mockResolvedValue(coachReadyPayload);
  });

  const renderDashboard = () => render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Dashboard />
    </MemoryRouter>
  );

  it('renders coach-ready layout with hero first and next-step section', async () => {
    renderDashboard();

    expect(await screen.findByText('Run Batch Coach on your games')).toBeInTheDocument();
    expect(screen.getByText('Coach home')).toBeInTheDocument();
    expect(screen.getByText('Next step')).toBeInTheDocument();
    expect(screen.getByText('Your games')).toBeInTheDocument();
    expect(screen.getByText('Recent games')).toBeInTheDocument();
    expect(screen.queryByText("Today's coaching")).not.toBeInTheDocument();
    expect(screen.queryByText('Your progress')).not.toBeInTheDocument();
  });

  it('renders coach-active sections including progress and coaching loop', async () => {
    fetchDashboardData.mockResolvedValue(coachActivePayload);
    renderDashboard();

    expect(await screen.findByText('Pick up your latest coach report')).toBeInTheDocument();
    expect(screen.getByText(/Welcome back, player1/i)).toBeInTheDocument();
    expect(screen.getByText('Since your last visit')).toBeInTheDocument();
    expect(screen.getByText("Today's coaching")).toBeInTheDocument();
    expect(screen.getByText('One thing today')).toBeInTheDocument();
    expect(screen.getByText('Coach inbox')).toBeInTheDocument();
    expect(screen.getByText('Your progress')).toBeInTheDocument();
    expect(screen.getByText(/You fixed 2\/3 patterns/i)).toBeInTheDocument();
    expect(screen.getByText('Coach insight')).toBeInTheDocument();
    expect(screen.getByText('Top priority')).toBeInTheDocument();
    expect(screen.getAllByText('Stop hanging pieces').length).toBeGreaterThanOrEqual(1);
  });

  it('hides one-thing card when it duplicates the hero CTA', async () => {
    fetchDashboardData.mockResolvedValue({
      ...coachActivePayload,
      oneThingToday: {
        headline: 'Open your report',
        ctaLabel: 'Open report',
        ctaTo: '/batch-report/42',
        source: 'hero',
      },
    });
    renderDashboard();

    expect(await screen.findByText('Pick up your latest coach report')).toBeInTheDocument();
    expect(screen.queryByText('One thing today')).not.toBeInTheDocument();
  });

  it('renders new-user layout without coach widgets or more stats', async () => {
    fetchDashboardData.mockResolvedValue({
      total_games: 0,
      analyzed_games: 0,
      recent_games: [],
      nextAction: {
        type: 'import_games',
        title: 'Import games to get started',
        description: 'Pull games from Chess.com or Lichess.',
        ctaLabel: 'Import games',
        ctaTo: '/fetch-games',
        secondaryLinks: [],
      },
      sinceLastVisit: { showBanner: false, summaryLines: [] },
    });
    renderDashboard();

    expect(await screen.findByText('Import games to get started')).toBeInTheDocument();
    expect(screen.getByText(/Import games from Chess.com or Lichess/i)).toBeInTheDocument();
    expect(screen.queryByText('Next step')).not.toBeInTheDocument();
    expect(screen.queryByText('More stats')).not.toBeInTheDocument();
    expect(screen.getByText(/No games yet/i)).toBeInTheDocument();
  });

  it('renders onboarding layout without coach section', async () => {
    fetchDashboardData.mockResolvedValue({
      total_games: 3,
      analyzed_games: 0,
      recent_games: [],
      nextAction: {
        type: 'import_for_batch',
        title: 'Import 2 more games for Batch Coach',
        description: 'Batch Coach needs at least 5 games.',
        ctaLabel: 'Import games',
        ctaTo: '/fetch-games',
        secondaryLinks: [],
      },
      sinceLastVisit: { showBanner: false, summaryLines: [] },
    });
    renderDashboard();

    expect(await screen.findByText('Import 2 more games for Batch Coach')).toBeInTheDocument();
    expect(screen.queryByText('Next step')).not.toBeInTheDocument();
    expect(screen.queryByText('Coach inbox')).not.toBeInTheDocument();
  });
});
