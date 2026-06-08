import React from 'react';
import { render, screen } from '@testing-library/react';
import BatchReportSections from '../BatchReportSections';

jest.mock('../BatchReportHero', () => () => <div data-testid="batch-hero" />);
jest.mock('../BatchReportHeader', () => () => <div data-testid="batch-header" />);
jest.mock('../ExecutiveSummary', () => () => <div data-testid="executive-summary" />);
jest.mock('../TopPriorities', () => () => <div data-testid="top-priorities" />);
jest.mock('../PracticeNextStrip', () => () => <div data-testid="practice-next" />);
jest.mock('../BatchCompareCard', () => () => <div data-testid="batch-compare" />);
jest.mock('../PhaseBreakdown', () => () => <div data-testid="phase-breakdown" />);
jest.mock('../TimeManagementInsight', () => {
  const actual = jest.requireActual('../TimeManagementInsight');
  return {
    __esModule: true,
    ...actual,
    default: () => <div data-testid="time-management" />,
  };
});
jest.mock('../CoachingInsightsSection', () => () => <div data-testid="coaching-insights" />);
jest.mock('../OpeningSection', () => () => <div data-testid="opening-section" />);
jest.mock('../RecurringPatterns', () => () => <div data-testid="recurring-patterns" />);
jest.mock('../TopCriticalMoments', () => () => <div data-testid="critical-moments" />);
jest.mock('../StudyDrillLinks', () => () => <div data-testid="study-drills" />);
jest.mock('../TrainingPlan', () => () => <div data-testid="training-plan" />);
jest.mock('../BatchReportToc', () => {
  const actual = jest.requireActual('../BatchReportToc');
  return {
    __esModule: true,
    ...actual,
    default: () => <div data-testid="batch-toc" />,
  };
});
jest.mock('../BatchReportLegend', () => () => <div data-testid="batch-legend" />);
jest.mock('../BatchReportMobileNav', () => () => <div data-testid="batch-mobile-nav" />);
jest.mock('../PartialBatchBanner', () => () => <div data-testid="partial-banner" />);

const buildReport = (overrides = {}) => ({
  games_count: 10,
  batch_summary: {
    games_analyzed: 10,
    recurring_weaknesses: [{ pattern: 'fork' }],
    rating_band_coaching: { focus: 'Tactics' },
    time_management_summary: {
      insight: 'You rush in time trouble.',
      games_with_clock_data: 3,
      games_analyzed: 10,
      pattern: 'rushed_critical_moments',
    },
  },
  coaching_report: {
    executive_summary: 'Improve tactics.',
    coaching_narrative: { opening: 'Play principled development.' },
    top_3_priorities: [{ rank: 1, title: 'Forks' }],
    training_plan: { week_1: 'Drill forks' },
  },
  per_game_results: [{ game_id: 'game_0', total_moves: 40 }],
  ...overrides,
});

describe('BatchReportSections', () => {
  beforeAll(() => {
    global.IntersectionObserver = class {
      observe() {}

      disconnect() {}

      unobserve() {}
    };
  });

  it('renders nothing without a batch report', () => {
    const { container } = render(<BatchReportSections batchReport={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders core sections and owner compare card', () => {
    render(<BatchReportSections batchReport={buildReport()} batchId="batch-9" />);

    expect(screen.getByTestId('batch-hero')).toBeInTheDocument();
    expect(screen.getByTestId('batch-compare')).toBeInTheDocument();
    expect(screen.getByTestId('opening-section')).toBeInTheDocument();
    expect(screen.getByTestId('recurring-patterns')).toBeInTheDocument();
    expect(screen.getByTestId('coaching-insights')).toBeInTheDocument();
    expect(screen.getByTestId('time-management')).toBeInTheDocument();
    expect(screen.queryByTestId('study-drills')).not.toBeInTheDocument();
  });

  it('hides compare in read-only share mode', () => {
    render(<BatchReportSections batchReport={buildReport()} batchId="batch-9" readOnly />);

    expect(screen.queryByTestId('batch-compare')).not.toBeInTheDocument();
  });

  it('shows coaching unavailable banner and failed games on partial batches', () => {
    render(
      <BatchReportSections
        batchReport={buildReport({
          coaching_report: null,
          errors: [{ game_id: 'game_2', message: 'Invalid PGN' }],
        })}
        status="partial"
        batchId="batch-9"
      />
    );

    expect(screen.getByText(/AI coaching narrative is unavailable/i)).toBeInTheDocument();
    expect(screen.getByText('Invalid PGN')).toBeInTheDocument();
  });

  it('shows extra study drills when practice strip cannot fit all links', () => {
    render(
      <BatchReportSections
        batchReport={buildReport({
          batch_summary: {
            games_analyzed: 10,
            recurring_weaknesses: [
              { pattern: 'pin' },
              { pattern: 'fork' },
              { pattern: 'skewer' },
              { pattern: 'hanging_piece' },
            ],
          },
        })}
        batchId="batch-9"
      />
    );

    expect(screen.getByTestId('study-drills')).toBeInTheDocument();
  });
});
