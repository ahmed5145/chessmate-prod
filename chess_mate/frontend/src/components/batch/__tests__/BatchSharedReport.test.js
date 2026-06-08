import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom';
import BatchSharedReport from '../BatchSharedReport';
import { getPublicBatchReport } from '../../../services/apiRequests';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useParams: jest.fn(),
}));

jest.mock('../../../services/apiRequests', () => ({
  getPublicBatchReport: jest.fn(),
}));

jest.mock('../BatchReportSections', () => function MockSections({ readOnly }) {
  return <div data-testid="shared-report-sections">{readOnly ? 'read-only' : 'owner'}</div>;
});

const renderAt = (token) =>
  render(
    <MemoryRouter initialEntries={[`/share/batch/${token || ''}`]}>
      <Routes>
        <Route path="/share/batch/:shareToken" element={<BatchSharedReport />} />
      </Routes>
    </MemoryRouter>
  );

describe('BatchSharedReport', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useParams.mockReturnValue({ shareToken: 'public-token-1' });
  });

  it('shows invalid share link when token is missing', async () => {
    useParams.mockReturnValue({ shareToken: undefined });
    render(
      <MemoryRouter>
        <BatchSharedReport />
      </MemoryRouter>
    );

    expect(await screen.findByText('Invalid share link.')).toBeInTheDocument();
    expect(getPublicBatchReport).not.toHaveBeenCalled();
  });

  it('loads and renders read-only report sections', async () => {
    getPublicBatchReport.mockResolvedValue({
      games_count: 8,
      status: 'completed',
      batch_summary: { games_analyzed: 8 },
    });

    renderAt('public-token-1');

    expect(screen.getByText('Loading shared report…')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId('shared-report-sections')).toHaveTextContent('read-only');
    });

    expect(getPublicBatchReport).toHaveBeenCalledWith('public-token-1');
    expect(screen.getByText(/Shared coaching report \(read-only\)/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Get your own batch report/i })).toHaveAttribute(
      'href',
      '/register?from=shared-report'
    );
    expect(screen.getByRole('link', { name: /See example report/i })).toHaveAttribute(
      'href',
      '/example/batch-report'
    );
    expect(screen.getByRole('link', { name: /See how it works/i })).toHaveAttribute(
      'href',
      '/how-batch-coach-works'
    );
  });

  it('shows API error message', async () => {
    getPublicBatchReport.mockRejectedValue({ detail: 'Share link expired.' });

    renderAt('expired-token');

    expect(await screen.findByText('Share link expired.')).toBeInTheDocument();
  });
});
