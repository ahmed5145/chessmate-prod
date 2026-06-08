/* eslint-disable import/first */
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { act } from 'react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import '@testing-library/jest-dom';

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

jest.mock('react-hot-toast', () => ({
  toast: { success: jest.fn(), error: jest.fn() },
}));

const clickConfirmDialog = async () => {
  const confirm = await screen.findByRole('button', { name: /^Confirm$/i });
  await userEvent.click(confirm);
};

const completedBatchReport = (overrides = {}) => ({
  status: 'completed',
  per_game_results: [{ game_id: 'g1', total_moves: 40, move_quality: { blunder: 0, mistake: 1, inaccuracy: 2 } }],
  games_count: 5,
  failed_games: [],
  batch_summary: {
    overall_accuracy: 0.5,
    phase_performance: { opening: { score: 0.5 }, middlegame: { score: 0.5 }, endgame: { score: 0.5 } },
    recurring_weaknesses: [],
    strength_patterns: [],
  },
  coaching_report: { executive_summary: 'Test summary', one_thing_to_do_today: 'Practice' },
  ...overrides,
});

describe('BatchAnalysisResults (PRD batch API)', () => {
  afterEach(() => {
    jest.clearAllMocks();
    jest.useRealTimers();
  });

  test('Retry Failed Games button calls retry API with failed IDs', async () => {
    const fakeReportWithFails = completedBatchReport({
      failed_games: [
        { game_id: 'g1', message: 'Timeout' },
        { game_id: 'g2', message: 'Invalid PGN' },
        { game_id: 'g3', message: 'Engine error' },
        { game_id: 'g4', message: 'Timeout' },
        { game_id: 'g5', message: 'Invalid PGN' },
      ],
    });

    getBatchReport.mockResolvedValue(fakeReportWithFails);
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
    await userEvent.click(retryButton);
    await clickConfirmDialog();

    await waitFor(() => expect(retryFailedGames).toHaveBeenCalled());
  });

  test('Add Games & Retry dialog allows adding IDs when failed < 5', async () => {
    const fakeSmallFailReport = completedBatchReport({
      games_count: 3,
      per_game_results: [],
      failed_games: [
        { game_id: 'a1', message: 'fail' },
        { game_id: 'a2', message: 'fail' },
        { game_id: 'a3', message: 'fail' },
      ],
    });

    getBatchReport.mockResolvedValue(fakeSmallFailReport);
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
    await userEvent.click(addButton);

    const textarea = await screen.findByPlaceholderText(/Paste game IDs or PGNs/);
    await userEvent.type(textarea, 'x1\n x2');

    const startButton = screen.getByRole('button', { name: /Start Retry/i });
    fireEvent.click(startButton);
    await clickConfirmDialog();

    await waitFor(() => expect(retryFailedGames).toHaveBeenCalled());
  });

  test('Retry with Completed Games combines completed + failed to reach minimum and starts retry', async () => {
    const fakePartialReport = completedBatchReport({
      per_game_results: [{ game_id: 'c1' }, { game_id: 'c2' }, { game_id: 'c3' }],
      failed_games: [{ game_id: 'f1' }, { game_id: 'f2' }],
    });

    getBatchReport.mockResolvedValue(fakePartialReport);
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
    await userEvent.click(includeButton);
    await clickConfirmDialog();

    await waitFor(() => expect(retryFailedGames).toHaveBeenCalled());
    const callArg = retryFailedGames.mock.calls[0][0];
    expect(Array.isArray(callArg.gameIds)).toBe(true);
    expect(callArg.gameIds.length).toBeGreaterThanOrEqual(5);
  });

  test('partial batch without coaching does not expose regenerate UI', async () => {
    const fakePartialNoCoach = completedBatchReport({
      status: 'partial',
      per_game_results: [
        { game_id: 's1' },
        { game_id: 's2' },
        { game_id: 's3' },
        { game_id: 's4' },
        { game_id: 's5' },
      ],
      failed_games: [{ game_id: 'f1' }],
      coaching_report: null,
    });

    getBatchReport.mockResolvedValue(fakePartialNoCoach);

    render(
      <MemoryRouter initialEntries={["/batch-analysis/results/report/PARTIAL_NO_COACH"]}>
        <Routes>
          <Route path="/batch-analysis/results/report/:reportId" element={<BatchAnalysisResults />} />
        </Routes>
      </MemoryRouter>
    );

    await screen.findByText('Batch Coach report');
    expect(screen.queryByRole('button', { name: /Regenerate Coaching Report/i })).not.toBeInTheDocument();
  });

  test('polls status then loads report and renders coaching section', async () => {
    jest.useFakeTimers();
    getBatchStatus
      .mockResolvedValueOnce({ status: 'in_progress', completed_games: 0, games_count: 2, progress: 0 })
      .mockResolvedValueOnce({ status: 'completed', completed_games: 2, games_count: 2, progress: 100 });

    const fakeReport = completedBatchReport({
      per_game_results: [
        { game_id: 1, move_quality: { blunder: 0, mistake: 1, inaccuracy: 1 }, total_moves: 20 },
        { game_id: 2, move_quality: { blunder: 1, mistake: 1, inaccuracy: 2 }, total_moves: 20 },
      ],
      games_count: 2,
      coaching_report: {
        executive_summary: 'Coach summary',
        coaching_narrative: { opening: '', middlegame: '', endgame: '' },
        top_3_priorities: [],
        training_plan: {},
        one_thing_to_do_today: 'Practice tactics',
      },
    });

    getBatchReport.mockResolvedValue(fakeReport);

    render(
      <MemoryRouter initialEntries={["/batch-analysis/results/FAKE_TASK"]}>
        <Routes>
          <Route path="/batch-analysis/results/:taskId" element={<BatchAnalysisResults />} />
        </Routes>
      </MemoryRouter>
    );

    await act(async () => {
      jest.advanceTimersByTime(2000);
    });
    await waitFor(() => expect(getBatchStatus).toHaveBeenCalledTimes(1));

    await act(async () => {
      jest.advanceTimersByTime(2000);
    });

    await waitFor(() => expect(getBatchReport).toHaveBeenCalledWith('FAKE_TASK'));
    expect(await screen.findByText('Combined Coaching Report', { timeout: 10000 })).toBeInTheDocument();
    expect(screen.getByText(/Coach summary/)).toBeInTheDocument();
    jest.useRealTimers();
  });

  test('loads saved report via reportId URL and renders coaching section', async () => {
    const fakeReport2 = completedBatchReport({
      per_game_results: [{ game_id: 10, move_quality: { blunder: 0, mistake: 0, inaccuracy: 1 }, total_moves: 30 }],
      games_count: 1,
      coaching_report: { executive_summary: 'Saved report summary', one_thing_to_do_today: 'Drill tactics' },
    });

    getBatchReport.mockResolvedValue(fakeReport2);

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
    const fakeNoFailReport = completedBatchReport({
      per_game_results: [],
      games_count: 1,
      failed_games: [{ game_id: 'f1', message: 'fail' }],
      coaching_report: { executive_summary: 'No fails', one_thing_to_do_today: 'Practice' },
    });

    getBatchReport.mockResolvedValue(fakeNoFailReport);
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
    await userEvent.click(addButton);

    const textarea = await screen.findByPlaceholderText(/Paste game IDs or PGNs/);

    const pgnBlockBase = `[Event "Live Chess"]\n[Site "Chess.com"]\n[Date "2026.05.28"]\n1. e4 e5 2. Nf3 Nc6 3. Bb5 a6`;
    const blocks = [0, 1, 2, 3, 4].map((i) => pgnBlockBase.replace('Live Chess', `Live Chess ${i + 1}`));
    const paste = blocks.join('\r\n\r\n');
    fireEvent.change(textarea, { target: { value: paste } });

    const startButton = screen.getByRole('button', { name: /Start Retry/i });
    await userEvent.click(startButton);
    await clickConfirmDialog();

    await waitFor(() => expect(retryFailedGames).toHaveBeenCalled());
    // ensure it was called with pgnList array
    const callArg = retryFailedGames.mock.calls[0][0];
    expect(Array.isArray(callArg.pgnList)).toBe(true);
    expect(callArg.pgnList.length).toBeGreaterThanOrEqual(5);
  });

  test('renders weakness and strength frequency labels in coaching report', async () => {
    getBatchReport.mockResolvedValue(
      completedBatchReport({
        batch_summary: {
          overall_accuracy: 0.62,
          phase_performance: {
            opening: { score: 0.7, primary_openings: ['Italian Game'] },
            middlegame: { score: 0.55 },
            endgame: { score: 0.5 },
          },
          recurring_weaknesses: [{ pattern: 'Hanging pieces', frequency: 4 }],
          strength_patterns: [{ pattern: 'Solid development', frequency: '3x', detail: 'Good piece play' }],
        },
        coaching_report: {
          executive_summary: 'You hang pieces too often.',
          one_thing_to_do_today: 'Do hanging-piece puzzles',
          training_plan: { week_1: 'Puzzles daily' },
        },
      })
    );

    render(
      <MemoryRouter initialEntries={['/batch-analysis/results/report/FREQ_LABELS']}>
        <Routes>
          <Route path="/batch-analysis/results/report/:reportId" element={<BatchAnalysisResults />} />
        </Routes>
      </MemoryRouter>
    );

    await screen.findByText('Combined Coaching Report');
    expect(screen.getByText('Hanging pieces (4)')).toBeInTheDocument();
    expect(screen.getByText('Solid development (3x)')).toBeInTheDocument();
    expect(screen.getAllByText(/Puzzles daily/).length).toBeGreaterThan(0);
  });

  test('displays per-game failure reasons from report errors', async () => {
    const fakeReportWithErrors = completedBatchReport({
      status: 'partial',
      per_game_results: [{ game_id: 'game_0' }, { game_id: 'game_1' }],
      games_count: 4,
      failed_games: [
        { game_id: 'game_2', error: 'Invalid PGN' },
        { game_id: 'game_3', error: 'Stockfish timeout' },
      ],
      errors: [
        { game_id: 'game_2', message: 'Invalid PGN' },
        { game_id: 'game_3', message: 'Stockfish timeout' },
      ],
    });

    getBatchReport.mockResolvedValue(fakeReportWithErrors);

    render(
      <MemoryRouter initialEntries={['/batch-analysis/results/report/FAIL_REASONS']}>
        <Routes>
          <Route path="/batch-analysis/results/report/:reportId" element={<BatchAnalysisResults />} />
        </Routes>
      </MemoryRouter>
    );

    await screen.findByText('Combined Coaching Report');
    expect(await screen.findByText(/Failed games \(2\)/)).toBeInTheDocument();
    expect(screen.getByText('Invalid PGN')).toBeInTheDocument();
    expect(screen.getByText('Stockfish timeout')).toBeInTheDocument();
  });
});
