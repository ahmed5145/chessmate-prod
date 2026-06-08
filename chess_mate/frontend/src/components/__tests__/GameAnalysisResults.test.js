import React from 'react';
import { render, screen } from '@testing-library/react';
import GameAnalysisResults from '../GameAnalysisResults';

jest.mock('../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

jest.mock('../batch/FenBoardImage', () => function MockFenBoard() {
  return <div data-testid="fen-board" />;
});

jest.mock('react-chartjs-2', () => ({
  Line: () => null,
}));

jest.mock('../batch/LichessActionButton', () => function MockLichessActionButton({ label }) {
  return <a href="https://lichess.org/training">{label}</a>;
});

jest.mock('../singlegame/SingleGameFooterCta', () => function MockSingleGameFooterCta() {
  return <div data-testid="single-game-footer-cta" />;
});

describe('GameAnalysisResults', () => {
  it('renders coaching hero when coaching payload is present', () => {
    render(
      <GameAnalysisResults
        analysisData={{
          coaching: {
            takeaway: 'Your biggest swing was on move 12.',
            do_today: 'Replay that position for five minutes.',
          },
          moves: [{ move_number: 1, san: 'e4', position: 'fen', eval_after: 0.2, is_white: true }],
        }}
      />
    );

    expect(screen.getByText(/Your biggest swing was on move 12/i)).toBeInTheDocument();
    expect(screen.getByText(/Replay that position/i)).toBeInTheDocument();
  });

  it('renders metrics and move insights from metrics+moves payload shape', () => {
    const analysisData = {
      metrics: {
        overall: { accuracy: 88.5, mistakes: 2 },
        time_management: { time_management_score: 71.2, time_pressure_percentage: 12.3 },
        phases: {
          opening: { accuracy: 90, mistakes: 0, opportunities: 1, best_moves: 2 },
          middlegame: { accuracy: 82, mistakes: 1, opportunities: 2, best_moves: 1 },
          endgame: { accuracy: 87, mistakes: 1, opportunities: 0, best_moves: 1 },
        },
      },
      moves: [
        {
          move_number: 1,
          san: 'e4',
          classification: 'good',
          eval_change: -0.12,
        },
        {
          move_number: 2,
          san: 'Nf3',
          classification: 'best',
          eval_change: 0.35,
        },
      ],
      feedback: {
        strengths: ['Opening discipline'],
      },
    };

    render(<GameAnalysisResults analysisData={analysisData} />);

    expect(screen.getByText('Overall Accuracy')).toBeInTheDocument();
    expect(screen.getByText('88.5%')).toBeInTheDocument();
    expect(screen.getByText(/All moves/i)).toBeInTheDocument();
    expect(screen.getAllByText('e4').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Nf3').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Good').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Best').length).toBeGreaterThan(0);
  });

  it('renders move insights from legacy movesAnalysis shape', () => {
    const analysisData = {
      analysis_results: {
        summary: {
          overall: { accuracy: 75, mistakes: 4 },
        },
      },
      movesAnalysis: [
        {
          move_number: 10,
          move: 'Qh5',
          classification: 'mistake',
          evaluation: -1.4,
        },
      ],
    };

    render(<GameAnalysisResults analysisData={analysisData} />);

    expect(screen.getByText(/All moves/i)).toBeInTheDocument();
    expect(screen.getAllByText('Qh5').length).toBeGreaterThan(0);
    expect(screen.getByText('Mistake')).toBeInTheDocument();
  });

  it('prefers top-level metrics over stale analysis_results summary values', () => {
    const analysisData = {
      metrics: {
        overall: { accuracy: 77.4, mistakes: 3 },
        time_management: { time_management_score: 64.2, time_pressure_percentage: 11.1 },
      },
      analysis_results: {
        summary: {
          overall: { accuracy: 0, mistakes: 0 },
          time_management: { time_management_score: 0, time_pressure_percentage: 0 },
        },
      },
      moves: [
        { move_number: 1, san: 'd4', classification: 'good', eval_change: 0.11 },
      ],
    };

    render(<GameAnalysisResults analysisData={analysisData} />);

    expect(screen.getByText('77.4%')).toBeInTheDocument();
    expect(screen.getByText('64.2%')).toBeInTheDocument();
    expect(screen.getByText('11.1%')).toBeInTheDocument();
  });

  it('uses move_quality accuracy when overall accuracy is zero', () => {
    const analysisData = {
      metrics: {
        overall: { accuracy: 0, mistakes: 0 },
        move_quality: { accuracy: 100, mistakes: 0 },
        time_management: { time_management_score: 0, time_pressure_percentage: 0 },
      },
      moves: [
        { move_number: 1, san: 'd4', classification: 'good', eval_change: 0.11 },
      ],
    };

    render(<GameAnalysisResults analysisData={analysisData} />);

    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('shows unavailable states when analysis data is explicitly unavailable', () => {
    const analysisData = {
      metrics: {
        summary: {
          overall: { accuracy: 0, mistakes: 0, data_status: 'unavailable' },
          data_status: 'unavailable',
        },
      },
      feedback: {
        data_status: 'unavailable',
      },
    };

    render(<GameAnalysisResults analysisData={analysisData} />);

    expect(screen.getAllByText('N/A').length).toBeGreaterThan(0);
  });

  it('applies cyan and dark blue badges for brilliant and great move', () => {
    const analysisData = {
      metrics: {
        overall: { accuracy: 90, mistakes: 0 },
      },
      moves: [
        {
          move_number: 15,
          san: 'Qxh7+',
          classification: 'brilliant',
          eval_change: 1.9,
        },
        {
          move_number: 16,
          san: 'Rf1',
          classification: 'great move',
          eval_change: 0.8,
        },
      ],
    };

    render(<GameAnalysisResults analysisData={analysisData} />);

    const brilliantBadge = screen.getByText('Brilliant');
    const greatMoveBadge = screen.getByText('Great move');

    expect(brilliantBadge.className).toContain('bg-cyan-100');
    expect(brilliantBadge.className).toContain('text-cyan-700');
    expect(greatMoveBadge.className).toContain('bg-blue-900');
    expect(greatMoveBadge.className).toContain('text-blue-100');
  });
});
