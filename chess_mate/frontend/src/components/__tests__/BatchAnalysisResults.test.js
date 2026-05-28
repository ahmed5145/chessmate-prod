import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { act } from 'react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import '@testing-library/jest-dom';

jest.useFakeTimers();

// Mock the apiRequests module used by the component
jest.mock('../../services/apiRequests', () => ({
  getBatchStatus: jest.fn(),
  getBatchReport: jest.fn(),
}));

import { getBatchStatus, getBatchReport } from '../../services/apiRequests';
import BatchAnalysisResults from '../BatchAnalysisResults';

describe('BatchAnalysisResults (PRD batch API)', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  test('polls status then loads report and renders coaching section', async () => {
    // First call returns in-progress, second call returns completed
    getBatchStatus
      .mockImplementationOnce(async () => ({ status: 'in_progress', completed_games: 0, games_count: 2, progress: 0 }))
      .mockImplementationOnce(async () => ({ status: 'completed', completed_games: 2, games_count: 2, progress: 100 }));

    const fakeReport = {
      status: 'completed',
      per_game_results: [ { game_id: 1, move_quality: { blunder: 0, mistake: 1, inaccuracy: 1 }, total_moves: 20 }, { game_id: 2, move_quality: { blunder: 1, mistake: 1, inaccuracy: 2 }, total_moves: 20 } ],
      games_count: 2,
      batch_summary: {
        overall_accuracy: 0.8,
        phase_performance: {
          opening: { score: 0.8 },
          middlegame: { score: 0.75 },
          endgame: { score: 0.7 }
        },
        recurring_weaknesses: [],
        strength_patterns: []
      },
      coaching_report: {
        executive_summary: 'Coach summary',
        coaching_narrative: { opening: '', middlegame: '', endgame: '' },
        top_3_priorities: [],
        training_plan: {},
        one_thing_to_do_today: 'Practice tactics'
      }
    };

    getBatchReport.mockResolvedValue(fakeReport);

    render(
      <MemoryRouter initialEntries={["/batch-analysis/results/FAKE_TASK"]}>
        <Routes>
          <Route path="/batch-analysis/results/:taskId" element={<BatchAnalysisResults />} />
        </Routes>
      </MemoryRouter>
    );

    // Advance timers to trigger the polling interval once
    act(() => {
      jest.advanceTimersByTime(2100);
    });

    await waitFor(() => expect(getBatchStatus).toHaveBeenCalledTimes(1));

    // Advance timers to trigger the next poll and report loading
    act(() => {
      jest.advanceTimersByTime(2100);
    });

    await waitFor(() => expect(getBatchReport).toHaveBeenCalledWith('FAKE_TASK'));
    await waitFor(() => expect(screen.getByText('Combined Coaching Report')).toBeInTheDocument());

    expect(getBatchStatus).toHaveBeenCalled();
    expect(screen.getByText(/Coach summary/)).toBeInTheDocument();
  });

  test('loads saved report via reportId URL and renders coaching section', async () => {
    const fakeReport2 = {
      status: 'completed',
      per_game_results: [ { game_id: 10, move_quality: { blunder: 0, mistake: 0, inaccuracy: 1 }, total_moves: 30 } ],
      games_count: 1,
      batch_summary: { overall_accuracy: 0.9, phase_performance: { opening: { score: 0.9 }, middlegame: { score: 0.85 }, endgame: { score: 0.8 } }, recurring_weaknesses: [], strength_patterns: [] },
      coaching_report: { executive_summary: 'Saved report summary', one_thing_to_do_today: 'Drill tactics' }
    };

    getBatchReport.mockResolvedValueOnce(fakeReport2);

    render(
      <MemoryRouter initialEntries={["/batch-analysis/results/report/REPORT123"]}>
        <Routes>
          <Route path="/batch-analysis/results/report/:reportId" element={<BatchAnalysisResults />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => expect(getBatchReport).toHaveBeenCalledWith('REPORT123'));
    await waitFor(() => expect(screen.getByText('Combined Coaching Report')).toBeInTheDocument());
    expect(screen.getByText(/Saved report summary/)).toBeInTheDocument();
  });
});
