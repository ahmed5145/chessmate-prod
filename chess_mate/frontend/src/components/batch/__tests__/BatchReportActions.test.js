import React from 'react';
import { render, screen } from '@testing-library/react';
import BatchReportActions from '../BatchReportActions';

jest.mock('react-hot-toast', () => ({
  toast: jest.fn(),
}));

jest.mock('../../../services/apiRequests', () => ({
  enableBatchShare: jest.fn(),
}));

jest.mock('../../../utils/clipboard', () => ({
  copyTextToClipboard: jest.fn().mockResolvedValue(true),
}));

describe('BatchReportActions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('does not expose coaching regenerate controls', () => {
    render(<BatchReportActions batchId={9} hasCoaching canRegenerateCoaching />);
    expect(screen.queryByRole('button', { name: /Refresh coaching/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Generate coaching/i })).not.toBeInTheDocument();
  });

  it('does not expose download or print export controls', () => {
    render(<BatchReportActions batchId={3} hasCoaching />);
    expect(screen.queryByRole('button', { name: /Download report/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Print$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Download PDF/i })).not.toBeInTheDocument();
  });

  it('shows copy share link for report owners', () => {
    render(<BatchReportActions batchId={3} hasCoaching />);
    expect(screen.getByRole('button', { name: /Copy share link/i })).toBeInTheDocument();
  });
});
