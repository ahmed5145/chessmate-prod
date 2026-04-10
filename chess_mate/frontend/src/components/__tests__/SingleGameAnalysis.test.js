import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import SingleGameAnalysis from '../SingleGameAnalysis';
import { analyzeSpecificGame, fetchGameAnalysis } from '../../services/gameAnalysisService';

// Mock the API call
jest.mock('../../services/gameAnalysisService', () => ({
  analyzeSpecificGame: jest.fn(),
  checkAnalysisStatus: jest.fn(),
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
    analyzeSpecificGame.mockReset();
    fetchGameAnalysis.mockReset();
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
});
