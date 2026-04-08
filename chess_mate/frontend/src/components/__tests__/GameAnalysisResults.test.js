import React from 'react';
import { render, screen } from '@testing-library/react';
import GameAnalysisResults from '../GameAnalysisResults';

jest.mock('../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

describe('GameAnalysisResults', () => {
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
    expect(screen.getByText('Move Insights')).toBeInTheDocument();
    expect(screen.getByText('e4')).toBeInTheDocument();
    expect(screen.getByText('Nf3')).toBeInTheDocument();
    expect(screen.getByText('good')).toBeInTheDocument();
    expect(screen.getByText('best')).toBeInTheDocument();
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

    expect(screen.getByText('Move Insights')).toBeInTheDocument();
    expect(screen.getByText('Qh5')).toBeInTheDocument();
    expect(screen.getByText('mistake')).toBeInTheDocument();
  });
});
