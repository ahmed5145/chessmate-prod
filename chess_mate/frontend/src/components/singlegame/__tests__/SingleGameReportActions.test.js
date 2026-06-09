import React from 'react';
import { render, screen } from '@testing-library/react';
import SingleGameReportActions from '../SingleGameReportActions';

jest.mock('../../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

jest.mock('../../../services/gameAnalysisService', () => ({
  createGameMomentShare: jest.fn(),
}));

jest.mock('../../../utils/marketingAnalytics', () => ({
  trackSingleGameEvent: jest.fn(),
}));

describe('SingleGameReportActions', () => {
  it('does not render a print action', () => {
    render(<SingleGameReportActions gameId={42} onReanalyze={jest.fn()} />);

    expect(screen.queryByRole('button', { name: /print/i })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Copy link/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Share moment/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Re-run deep review/i })).toBeInTheDocument();
  });
});
