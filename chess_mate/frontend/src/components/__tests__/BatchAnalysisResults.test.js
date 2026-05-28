/* eslint-disable import/first */
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { act } from 'react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import '@testing-library/jest-dom';

jest.useFakeTimers();

// Allow imports below for mocking purposes
// Mock the apiRequests module used by the component
jest.mock('../../services/apiRequests', () => ({
  getBatchStatus: jest.fn(),
  getBatchReport: jest.fn(),
  retryFailedGames: jest.fn(),
}));

import { getBatchStatus, getBatchReport } from '../../services/apiRequests';
import BatchAnalysisResults from '../BatchAnalysisResults';
import userEvent from '@testing-library/user-event';

describe('BatchAnalysisResults (PRD batch API)', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  test('Retry Failed Games button calls retry API with failed IDs', async () => {
    const fakeReportWithFails = {
      status: 'completed',
      per_game_results: [],
      games_count: 5,
      failed_games: [
        { game_id: 'g1' },
        { game_id: 'g2' },
        { game_id: 'g3' },
        { game_id: 'g4' },
        { game_id: 'g5' }
      ],
      batch_summary: { overall_accuracy: 0.5, phase_performance: { opening: { score: 0.5 }, middlegame: { score: 0.5 }, endgame: { score: 0.5 } }, recurring_weaknesses: [], strength_patterns: [] },
      coaching_report: { executive_summary: 'Partial results', one_thing_to_do_today: 'Practice' }
    };

    getBatchReport.mockResolvedValueOnce(fakeReportWithFails);
    const { retryFailedGames } = require('../../services/apiRequests');
    retryFailedGames.mockResolvedValueOnce({ batch_id: 'NEWBATCH', task_id: 'NEWTASK' });

    render(
      <MemoryRouter initialEntries={["/batch-analysis/results/report/REPORT_RETRY"]}>
        <Routes>
          <Route path="/batch-analysis/results/report/:reportId" element={<BatchAnalysisResults />} />
        </Routes>
      </MemoryRouter>
    );

    await screen.findByText('Combined Coaching Report');

    const retryButton = screen.getByRole('button', { name: /Retry Failed Games/i });
    // userEvent uses timers internally; switch to real timers for this interaction
    jest.useRealTimers();
    await userEvent.click(retryButton);
    jest.useFakeTimers();

    await waitFor(() => expect(retryFailedGames).toHaveBeenCalled());
  });

  test('Add Games & Retry dialog allows adding IDs when failed < 5', async () => {
    const fakeSmallFailReport = {
      status: 'completed',
      per_game_results: [],
      games_count: 3,
      failed_games: [ { game_id: 'a1' }, { game_id: 'a2' }, { game_id: 'a3' } ],
      batch_summary: { overall_accuracy: 0.5, phase_performance: { opening: { score: 0.5 }, middlegame: { score: 0.5 }, endgame: { score: 0.5 } }, recurring_weaknesses: [], strength_patterns: [] },
      coaching_report: { executive_summary: 'Partial', one_thing_to_do_today: 'Practice' }
    };

    getBatchReport.mockResolvedValueOnce(fakeSmallFailReport);
    const { retryFailedGames } = require('../../services/apiRequests');
    retryFailedGames.mockResolvedValueOnce({ batch_id: 'BATCH2', task_id: 'TASK2' });

    render(
      <MemoryRouter initialEntries={["/batch-analysis/results/report/SMALL_FAIL"]}>
        <Routes>
          <Route path="/batch-analysis/results/report/:reportId" element={<BatchAnalysisResults />} />
        </Routes>
      </MemoryRouter>
    );

    await screen.findByText('Combined Coaching Report');

    const addButton = screen.getByRole('button', { name: /Add Games & Retry/i });
    // Use real timers for userEvent interactions that trigger dialog mount/effects
    jest.useRealTimers();
    await userEvent.click(addButton);

    const textarea = await screen.findByPlaceholderText(/Paste game IDs or PGNs/);
    // already using real timers; continue typing and clicking
    // Add two more ids to reach 5
    await userEvent.type(textarea, 'x1\n x2');

    const startButton = screen.getByRole('button', { name: /Start Retry/i });
    fireEvent.click(startButton);
    jest.useFakeTimers();

    await waitFor(() => expect(retryFailedGames).toHaveBeenCalled());
  });

  test('Retry with Completed Games combines completed + failed to reach minimum and starts retry', async () => {
    const fakePartialReport = {
      status: 'completed',
      per_game_results: [ { game_id: 'c1' }, { game_id: 'c2' }, { game_id: 'c3' } ],
      games_count: 5,
      failed_games: [ { game_id: 'f1' }, { game_id: 'f2' } ],
      batch_summary: { overall_accuracy: 0.5, phase_performance: { opening: { score: 0.5 }, middlegame: { score: 0.5 }, endgame: { score: 0.5 } }, recurring_weaknesses: [], strength_patterns: [] },
      coaching_report: { executive_summary: 'Partial mix', one_thing_to_do_today: 'Practice' }
    };

    getBatchReport.mockResolvedValueOnce(fakePartialReport);
    const { retryFailedGames } = require('../../services/apiRequests');
    retryFailedGames.mockResolvedValueOnce({ batch_id: 'BATCH_MIX', task_id: 'TASK_MIX' });

    render(
      <MemoryRouter initialEntries={["/batch-analysis/results/report/PARTIAL_MIX"]}>
        <Routes>
          <Route path="/batch-analysis/results/report/:reportId" element={<BatchAnalysisResults />} />
        </Routes>
      </MemoryRouter>
    );

    await screen.findByText('Combined Coaching Report');

    const includeButton = screen.getByRole('button', { name: /Retry with Completed Games/i });
    jest.useRealTimers();
    await userEvent.click(includeButton);
    jest.useFakeTimers();

    await waitFor(() => expect(retryFailedGames).toHaveBeenCalled());
    const callArg = retryFailedGames.mock.calls[0][0];
    expect(Array.isArray(callArg.gameIds)).toBe(true);
    expect(callArg.gameIds.length).toBeGreaterThanOrEqual(5);
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
    // prefer findByText for async element queries
    await screen.findByText('Combined Coaching Report');

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
    await screen.findByText('Combined Coaching Report');
    expect(await screen.findByText(/Saved report summary/)).toBeInTheDocument();
  });

  test('Add Games & Retry dialog allows adding PGNs and submits pgnList when enough PGNs provided', async () => {
    const fakeNoFailReport = {
      status: 'completed',
      per_game_results: [],
      games_count: 1,
      failed_games: [{ game_id: 'f1' }],
      batch_summary: { overall_accuracy: 0.5, phase_performance: { opening: { score: 0.5 }, middlegame: { score: 0.5 }, endgame: { score: 0.5 } }, recurring_weaknesses: [], strength_patterns: [] },
      coaching_report: { executive_summary: 'No fails', one_thing_to_do_today: 'Practice' }
    };

    getBatchReport.mockResolvedValueOnce(fakeNoFailReport);
    const { retryFailedGames } = require('../../services/apiRequests');
    retryFailedGames.mockResolvedValueOnce({ batch_id: 'BPGN', task_id: 'TPGN' });

    render(
      <MemoryRouter initialEntries={["/batch-analysis/results/report/PGN_FAILS"]}>
        <Routes>
          <Route path="/batch-analysis/results/report/:reportId" element={<BatchAnalysisResults />} />
        </Routes>
      </MemoryRouter>
    );

    await screen.findByText('Combined Coaching Report');

    const addButton = screen.getByRole('button', { name: /Add Games & Retry/i });
    jest.useRealTimers();
    await userEvent.click(addButton);

    const textarea = await screen.findByPlaceholderText(/Paste game IDs or PGNs/);

    // Provide 5 small PGN blocks separated by blank lines
    const pgnBlockBase = `[Event "Live Chess"]\n[Site "Chess.com"]\n[Date "2026.05.28"]\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6`;
    const blocks = [0,1,2,3,4].map((i) => pgnBlockBase.replace('Live Chess', `Live Chess ${i+1}`));
    const paste = blocks.join('\r\n\r\n');
    // Use direct change event for controlled MUI TextField
    fireEvent.change(textarea, { target: { value: paste } });
    // textarea value set via change event

    const startButton = screen.getByRole('button', { name: /Start Retry/i });
    await userEvent.click(startButton);
    jest.useFakeTimers();

    await waitFor(() => expect(retryFailedGames).toHaveBeenCalled());
    // ensure it was called with pgnList array
    const callArg = retryFailedGames.mock.calls[0][0];
    expect(Array.isArray(callArg.pgnList)).toBe(true);
    expect(callArg.pgnList.length).toBeGreaterThanOrEqual(5);
  });
});
