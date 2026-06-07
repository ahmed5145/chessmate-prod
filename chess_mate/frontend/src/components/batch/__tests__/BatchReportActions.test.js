import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { toast } from 'react-hot-toast';
import BatchReportActions from '../BatchReportActions';
import { downloadBatchReport } from '../../../utils/printBatchReport';

jest.mock('react-hot-toast', () => ({
  toast: jest.fn(),
}));

jest.mock('../../../services/apiRequests', () => ({
  enableBatchShare: jest.fn(),
}));

jest.mock('../../../utils/printBatchReport', () => ({
  downloadBatchReport: jest.fn(),
  printBatchReport: jest.fn(),
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

  it('downloads via browser print dialog', () => {
    render(<BatchReportActions batchId={3} hasCoaching />);
    fireEvent.click(screen.getByRole('button', { name: /^Download$/i }));
    expect(downloadBatchReport).toHaveBeenCalled();
    expect(toast).toHaveBeenCalledWith(
      expect.stringMatching(/Save as PDF/i),
      expect.any(Object)
    );
  });

  it('does not expose separate Print or html2canvas PDF buttons', () => {
    render(<BatchReportActions batchId={3} hasCoaching />);
    expect(screen.queryByRole('button', { name: /^Print$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Download PDF/i })).not.toBeInTheDocument();
  });
});
