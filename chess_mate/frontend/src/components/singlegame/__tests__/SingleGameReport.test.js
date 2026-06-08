import React from 'react';
import { render, screen } from '@testing-library/react';
import SingleGameReport from '../SingleGameReport';

jest.mock('../../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

jest.mock('../../batch/FenBoardImage', () => function MockFenBoard() {
  return <div data-testid="fen-board" />;
});

jest.mock('react-chartjs-2', () => ({
  Line: () => null,
}));

jest.mock('../../batch/LichessActionButton', () => function MockLichessActionButton({ label }) {
  return <a href="https://lichess.org/training">{label}</a>;
});

jest.mock('../SingleGameFooterCta', () => function MockSingleGameFooterCta() {
  return <div data-testid="single-game-footer-cta" />;
});

jest.mock('../SingleGameReportActions', () => function MockSingleGameReportActions() {
  return null;
});

jest.mock('../../../utils/marketingAnalytics', () => ({
  trackSingleGameEvent: jest.fn(),
}));

describe('SingleGameReport', () => {
  it('renders coaching hero and engine disclaimer', () => {
    render(
      <SingleGameReport
        analysisData={{
          coaching: {
            takeaway: 'Your biggest swing was on move 12.',
            do_today: 'Replay that position for five minutes.',
          },
          engine_meta: {
            classification_note: 'Single-game uses depth-20 coach model; batch report uses depth-14.',
          },
          moves: [{ move_number: 1, san: 'e4', position: 'fen', eval_after: 0.2, is_white: true }],
        }}
      />
    );

    expect(screen.getByText(/Your biggest swing was on move 12/i)).toBeInTheDocument();
    expect(screen.getByText(/depth-20 coach model/i)).toBeInTheDocument();
  });

  it('renders batch-aligned priority banner data via phase strip context', () => {
    render(
      <SingleGameReport
        batchId={9}
        analysisData={{
          coaching: { takeaway: 'Batch-linked takeaway', do_today: 'Study the fork pattern.' },
          batch_context: {
            batch_id: 9,
            priority_rank: 1,
            priority: { title: 'Fix opening prep' },
            pattern_label: 'Hanging pieces',
          },
          moves: [{ move_number: 12, san: 'Nf3', position: 'fen', eval_after: -1.2, is_white: true }],
          critical_moments: [
            {
              move_number: 12,
              type: 'mistake',
              fen: 'fen',
              played_move: 'Nf3',
              best_move: 'd4',
            },
          ],
        }}
      />
    );

    expect(screen.getByText(/Batch-linked takeaway/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Move 12/i).length).toBeGreaterThan(0);
  });
});
