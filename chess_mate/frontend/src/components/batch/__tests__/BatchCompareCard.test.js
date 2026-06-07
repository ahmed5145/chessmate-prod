import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import BatchCompareCard from '../BatchCompareCard';
import { fetchBatchCompare } from '../../../services/apiRequests';

jest.mock('../../../services/apiRequests', () => ({
  fetchBatchCompare: jest.fn(),
}));

describe('BatchCompareCard', () => {
  beforeEach(() => {
    fetchBatchCompare.mockReset();
  });

  it('shows skeleton while loading', () => {
    fetchBatchCompare.mockReturnValue(new Promise(() => {}));

    render(<BatchCompareCard batchId={12} />);

    expect(screen.getByLabelText(/Loading batch comparison/i)).toBeInTheDocument();
  });

  it('shows empty state when no previous batch exists', async () => {
    const error = new Error('No previous batch');
    error.status = 404;
    fetchBatchCompare.mockRejectedValue(error);

    render(<BatchCompareCard batchId={12} />);

    expect(await screen.findByText(/Track progress over time/i)).toBeInTheDocument();
    expect(screen.getByText(/Run another batch later/i)).toBeInTheDocument();
  });

  it('shows comparison when previous batch exists', async () => {
    fetchBatchCompare.mockResolvedValue({
      other_batch_id: 11,
      narrative: 'Move match improved slightly.',
      weaknesses: { persisting: ['fork'], resolved: [], new: [] },
    });

    render(<BatchCompareCard batchId={12} />);

    await waitFor(() => {
      expect(screen.getByText(/vs previous batch/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/Move match improved slightly/i)).toBeInTheDocument();
  });
});
