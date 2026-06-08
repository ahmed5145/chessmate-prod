import React from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import { useParams } from 'react-router-dom';
import BatchReport from '../BatchReport';
import { getBatchReport, getBatchStatus } from '../../../services/apiRequests';
import api from '../../../services/api';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useParams: jest.fn(),
}));

jest.mock('../../../services/apiRequests', () => ({
  getBatchStatus: jest.fn(),
  getBatchReport: jest.fn(),
}));

jest.mock('../../../services/api', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    defaults: { headers: { common: {} } },
  },
}));

jest.mock('../BatchReportSections', () => function MockSections() {
  return <div data-testid="batch-report-sections">Report sections</div>;
});

jest.mock('../BatchReportStickyActions', () => function MockStickyActions() {
  return <div data-testid="batch-report-sticky-actions">Actions</div>;
});

jest.mock('../BatchLoadingScreen', () => function MockLoadingScreen({ status }) {
  if (status === 'pending' || status === 'in_progress') {
    return <div data-testid="batch-loading">Loading</div>;
  }
  return null;
});

const completedReport = {
  id: 'batch-42',
  status: 'completed',
  games_count: 10,
  batch_summary: { games_analyzed: 10 },
  per_game_results: [],
  coaching_report: { executive_summary: 'Focus on tactics.' },
};

describe('BatchReport', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    window.history.pushState({}, '', '/batch-report/batch-42');
    api.get.mockResolvedValue({ data: { batch_sends_completion_email: true } });
    useParams.mockReturnValue({ batchId: 'batch-42' });
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('shows missing batch id error', async () => {
    useParams.mockReturnValue({ batchId: undefined });

    render(<BatchReport />);

    expect(await screen.findByText('Missing batch ID.')).toBeInTheDocument();
    expect(getBatchStatus).not.toHaveBeenCalled();
  });

  it('loads and renders report when batch completes', async () => {
    getBatchStatus.mockResolvedValue({
      status: 'completed',
      progress: '10/10 games analyzed',
      completed_games: 10,
      games_count: 10,
    });
    getBatchReport.mockResolvedValue(completedReport);

    render(<BatchReport />);

    await waitFor(() => {
      expect(getBatchReport).toHaveBeenCalledWith('batch-42');
    });

    expect(await screen.findByTestId('batch-report-sections')).toBeInTheDocument();
    expect(screen.getByTestId('batch-report-sticky-actions')).toBeInTheDocument();
    expect(screen.queryByText(/Building your Batch Coach report/i)).not.toBeInTheDocument();
  });

  it('renders partial report with coaching unavailable', async () => {
    getBatchStatus.mockResolvedValue({
      status: 'partial',
      progress: '8/10 games analyzed',
      completed_games: 8,
      games_count: 10,
    });
    getBatchReport.mockResolvedValue({
      ...completedReport,
      status: 'partial',
      coaching_report: null,
    });

    render(<BatchReport />);

    await waitFor(() => {
      expect(getBatchReport).toHaveBeenCalled();
    });

    expect(await screen.findByTestId('batch-report-sections')).toBeInTheDocument();
  });

  it('shows failed batch message with refund details', async () => {
    getBatchStatus.mockResolvedValue({
      status: 'failed',
      progress: '',
      completed_games: 2,
      games_count: 10,
    });
    getBatchReport.mockResolvedValue({
      status: 'failed',
      message: 'Analysis failed — insufficient games succeeded.',
      credits_refunded: true,
      credits_refunded_amount: 2,
    });

    render(<BatchReport />);

    expect(
      await screen.findByText(/Analysis failed — insufficient games succeeded/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/refunded 2 credits/i)).toBeInTheDocument();
    expect(screen.queryByTestId('batch-report-sections')).not.toBeInTheDocument();
  });

  it('shows server unreachable after repeated poll failures', async () => {
    getBatchStatus.mockRejectedValue(new Error('Network error'));

    render(<BatchReport />);

    await waitFor(() => expect(getBatchStatus).toHaveBeenCalledTimes(1));

    await act(async () => {
      jest.advanceTimersByTime(3000);
    });
    await waitFor(() => expect(getBatchStatus).toHaveBeenCalledTimes(2));

    await act(async () => {
      jest.advanceTimersByTime(3000);
    });

    expect(
      await screen.findByText('Unable to reach server. Please refresh the page.')
    ).toBeInTheDocument();
  });
});
