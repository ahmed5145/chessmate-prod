import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { toast } from 'react-hot-toast';
import BatchReportActions from '../BatchReportActions';
import { regenerateBatchCoaching, enableBatchShare } from '../../../services/apiRequests';
import { downloadReportPdf } from '../../../utils/downloadReportPdf';
import { printBatchReport } from '../../../utils/printBatchReport';

jest.mock('react-hot-toast', () => ({
  toast: {
    loading: jest.fn(() => 'toast-id'),
    success: jest.fn(),
    error: jest.fn(),
  },
}));

jest.mock('../../../services/apiRequests', () => ({
  regenerateBatchCoaching: jest.fn(),
  enableBatchShare: jest.fn(),
}));

jest.mock('../../../utils/downloadReportPdf', () => ({
  downloadReportPdf: jest.fn(),
}));

jest.mock('../../../utils/printBatchReport', () => ({
  printBatchReport: jest.fn(),
}));

jest.mock('../../../utils/clipboard', () => ({
  copyTextToClipboard: jest.fn().mockResolvedValue(true),
}));

describe('BatchReportActions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows refresh coaching and calls regenerate API', async () => {
    const onReportRefresh = jest.fn();
    regenerateBatchCoaching.mockResolvedValue({ id: 9, coaching_report: { executive_summary: 'new' } });

    render(
      <BatchReportActions
        batchId={9}
        hasCoaching
        canRegenerateCoaching
        onReportRefresh={onReportRefresh}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /Refresh coaching/i }));

    await waitFor(() => {
      expect(regenerateBatchCoaching).toHaveBeenCalledWith(9);
      expect(onReportRefresh).toHaveBeenCalled();
      expect(toast.success).toHaveBeenCalled();
    });
  });

  it('shows rate-limit error messaging', async () => {
    regenerateBatchCoaching.mockRejectedValue({
      code: 'COACH_001',
      message: 'Coaching regeneration limit reached for today. Try again tomorrow.',
    });

    render(
      <BatchReportActions batchId={4} hasCoaching canRegenerateCoaching />
    );

    fireEvent.click(screen.getByRole('button', { name: /Refresh coaching/i }));

    await waitFor(() => {
      expect(regenerateBatchCoaching).toHaveBeenCalledWith(4);
    });
    expect(toast.error).toHaveBeenCalled();
    const [message] = toast.error.mock.calls[0];
    expect(message).toMatch(/limit reached for today/i);
  });

  it('uses browser print fallback action', () => {
    render(<BatchReportActions batchId={3} hasCoaching={false} />);
    fireEvent.click(screen.getByRole('button', { name: /^Print$/i }));
    expect(printBatchReport).toHaveBeenCalled();
  });

  it('suggests print when PDF export fails', async () => {
    downloadReportPdf.mockRejectedValue(new Error('capture failed'));

    render(<BatchReportActions batchId={3} hasCoaching />);

    fireEvent.click(screen.getByRole('button', { name: /Download PDF/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        expect.stringMatching(/Use Print instead/i),
        expect.any(Object)
      );
    });
  });
});
