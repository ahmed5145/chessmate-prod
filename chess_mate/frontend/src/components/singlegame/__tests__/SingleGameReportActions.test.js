import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { toast } from 'react-hot-toast';
import SingleGameReportActions from '../SingleGameReportActions';
import { createGameMomentShare } from '../../../services/gameAnalysisService';
import { copyTextToClipboard } from '../../../utils/clipboard';

jest.mock('../../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

jest.mock('../../../services/gameAnalysisService', () => ({
  createGameMomentShare: jest.fn(),
}));

jest.mock('../../../utils/clipboard', () => ({
  copyTextToClipboard: jest.fn(),
}));

jest.mock('../../../utils/marketingAnalytics', () => ({
  trackSingleGameEvent: jest.fn(),
}));

jest.mock('react-hot-toast', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

describe('SingleGameReportActions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    copyTextToClipboard.mockResolvedValue(true);
  });

  it('does not render a print action', () => {
    render(<SingleGameReportActions gameId={42} onReanalyze={jest.fn()} />);

    expect(screen.queryByRole('button', { name: /print/i })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Copy link/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Share moment/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Re-run deep review/i })).toBeInTheDocument();
  });

  it('creates share link even when clipboard copy fails', async () => {
    createGameMomentShare.mockResolvedValue({
      share_token: 'abc-123',
      share_url: 'https://www.chess-mate.online/share/game-moment/abc-123',
    });
    copyTextToClipboard.mockResolvedValue(false);

    render(<SingleGameReportActions gameId={42} move={12} />);
    fireEvent.click(screen.getByRole('button', { name: /Share moment/i }));

    await waitFor(() => {
      expect(createGameMomentShare).toHaveBeenCalledWith(42, { move: 12 });
    });
    expect(toast.success).toHaveBeenCalledWith(
      'https://www.chess-mate.online/share/game-moment/abc-123',
      { duration: 8000 },
    );
    expect(toast.error).not.toHaveBeenCalled();
  });

  it('shows API error when share creation fails', async () => {
    createGameMomentShare.mockRejectedValue({
      response: { data: { detail: 'Complete analysis before sharing a moment.' } },
    });

    render(<SingleGameReportActions gameId={42} />);
    fireEvent.click(screen.getByRole('button', { name: /Share moment/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Complete analysis before sharing a moment.');
    });
  });
});
