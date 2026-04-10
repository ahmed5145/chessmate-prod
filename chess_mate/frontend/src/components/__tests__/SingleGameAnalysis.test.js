import React from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import SingleGameAnalysis from '../SingleGameAnalysis';
import {
  analyzeSpecificGame,
  checkAnalysisStatus,
  classifyAnalysisPollingStatus,
  computeNextPollDelay,
  fetchGameAnalysis,
} from '../../services/gameAnalysisService';

// Mock the API call
jest.mock('../../services/gameAnalysisService', () => ({
  analyzeSpecificGame: jest.fn(),
  checkAnalysisStatus: jest.fn(),
  classifyAnalysisPollingStatus: jest.fn((status, progress) => {
    const normalizedStatus = String(status || '').toUpperCase();
    return {
      normalizedStatus,
      isSuccess: normalizedStatus === 'SUCCESS' || normalizedStatus === 'COMPLETED' || Number(progress) >= 100,
      isTerminalFailure: ['FAILURE', 'FAILED', 'ERROR', 'REVOKED', 'AUTH_ERROR'].includes(normalizedStatus),
    };
  }),
  computeNextPollDelay: jest.fn(({ currentDelay, minDelay, maxDelay, hadError }) =>
    hadError ? Math.min(maxDelay, currentDelay * 2) : minDelay
  ),
  shouldPollStatus: jest.fn((status, progress) => {
    const normalizedStatus = String(status || '').toUpperCase();
    const numericProgress = Number(progress) || 0;
    if (numericProgress >= 100) return false;
    const SUCCESS_STATUSES = new Set(['SUCCESS', 'COMPLETED']);
    const TERMINAL_FAILURE_STATUSES = new Set(['FAILURE', 'FAILED', 'ERROR', 'REVOKED', 'AUTH_ERROR']);
    if (SUCCESS_STATUSES.has(normalizedStatus) || TERMINAL_FAILURE_STATUSES.has(normalizedStatus)) {
      return false;
    }
    return true;
  }),
  fetchGameAnalysis: jest.fn(),
  restartAnalysis: jest.fn(),
}));

jest.mock('../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

// Mock chart.js to avoid canvas errors
jest.mock('react-chartjs-2', () => ({
  Line: () => null,
}));

describe('SingleGameAnalysis', () => {
  beforeEach(() => {
    jest.useRealTimers();
    analyzeSpecificGame.mockReset();
    checkAnalysisStatus.mockReset();
    classifyAnalysisPollingStatus.mockReset();
    computeNextPollDelay.mockReset();
    fetchGameAnalysis.mockReset();

    classifyAnalysisPollingStatus.mockImplementation((status, progress) => {
      const normalizedStatus = String(status || '').toUpperCase();
      return {
        normalizedStatus,
        isSuccess: normalizedStatus === 'SUCCESS' || normalizedStatus === 'COMPLETED' || Number(progress) >= 100,
        isTerminalFailure: ['FAILURE', 'FAILED', 'ERROR', 'REVOKED', 'AUTH_ERROR'].includes(normalizedStatus),
      };
    });

    computeNextPollDelay.mockImplementation(({ currentDelay, minDelay, maxDelay, hadError }) =>
      hadError ? Math.min(maxDelay, currentDelay * 2) : minDelay
    );

    localStorage.clear();
  });

  it('renders loading state initially', () => {
    analyzeSpecificGame.mockImplementation(() => new Promise(() => {}));

    render(
      <MemoryRouter initialEntries={['/analysis/1']}>
        <Routes>
          <Route path="/analysis/:gameId" element={<SingleGameAnalysis />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Analysis in Progress')).toBeInTheDocument();
  });

  it('renders analysis data when loaded', async () => {
    localStorage.setItem('analysis_complete_1', 'true');
    fetchGameAnalysis.mockResolvedValue({
      moves: [{ move: 'e4', score: 0.3 }],
      metrics: { summary: { accuracy: 85.5 } },
    });

    render(
      <MemoryRouter initialEntries={['/analysis/1']}>
        <Routes>
          <Route path="/analysis/:gameId" element={<SingleGameAnalysis />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Game Analysis Results')).toBeInTheDocument();
    });

    expect(fetchGameAnalysis).toHaveBeenCalledWith('1');
  });

  it('renders error state when API call fails', async () => {
    analyzeSpecificGame.mockRejectedValue(new Error('API Error'));

    render(
      <MemoryRouter initialEntries={['/analysis/1']}>
        <Routes>
          <Route path="/analysis/:gameId" element={<SingleGameAnalysis />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('API Error')).toBeInTheDocument();
    });
  });

  it('shows no-data state when completed analysis has no results payload', async () => {
    localStorage.setItem('analysis_complete_1', 'true');
    fetchGameAnalysis.mockResolvedValue({});

    render(
      <MemoryRouter initialEntries={['/analysis/1']}>
        <Routes>
          <Route path="/analysis/:gameId" element={<SingleGameAnalysis />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Failed to start analysis. Please try again.')).toBeInTheDocument();
    });
  });

  it('stops polling after entering an error state', async () => {
    jest.useFakeTimers();
    analyzeSpecificGame.mockResolvedValue({ success: true });
    checkAnalysisStatus.mockResolvedValue({
      status: 'PENDING',
      progress: 95,
      message: 'Almost done',
    });
    fetchGameAnalysis.mockRejectedValue(new Error('analysis fetch failed'));

    render(
      <MemoryRouter initialEntries={['/analysis/1']}>
        <Routes>
          <Route path="/analysis/:gameId" element={<SingleGameAnalysis />} />
        </Routes>
      </MemoryRouter>
    );

    // Trigger initial poll. High progress triggers direct fetch, and its failure
    // sets analysisError.
    await waitFor(() => expect(analyzeSpecificGame).toHaveBeenCalledWith('1'));

    await act(async () => {
      jest.advanceTimersByTime(6000);
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(fetchGameAnalysis).toHaveBeenCalledWith('1');
      expect(screen.getByText('analysis fetch failed')).toBeInTheDocument();
    });

    const callCountAfterError = checkAnalysisStatus.mock.calls.length;

    // Polling should remain stopped after the error even if more time passes.
    await act(async () => {
      jest.advanceTimersByTime(60000);
      await Promise.resolve();
    });

    expect(checkAnalysisStatus.mock.calls.length).toBe(callCountAfterError);
  });

  it('stops polling on terminal FAILED status', async () => {
    jest.useFakeTimers();
    analyzeSpecificGame.mockResolvedValue({ success: true });
    checkAnalysisStatus.mockResolvedValue({
      status: 'FAILED',
      message: 'Worker failed to analyze game',
      progress: 40,
    });

    render(
      <MemoryRouter initialEntries={['/analysis/1']}>
        <Routes>
          <Route path="/analysis/:gameId" element={<SingleGameAnalysis />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => expect(analyzeSpecificGame).toHaveBeenCalledWith('1'));

    await act(async () => {
      jest.advanceTimersByTime(6000);
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(screen.getByText('Worker failed to analyze game')).toBeInTheDocument();
    });

    const callCountAfterFailure = checkAnalysisStatus.mock.calls.length;

    await act(async () => {
      jest.advanceTimersByTime(30000);
      await Promise.resolve();
    });

    expect(checkAnalysisStatus.mock.calls.length).toBe(callCountAfterFailure);
    expect(fetchGameAnalysis).not.toHaveBeenCalled();
  });
});
