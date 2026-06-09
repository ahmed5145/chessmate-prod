import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import FirstBatchModal from '../FirstBatchModal';
import { updateUserProfile } from '../../../services/apiRequests';

jest.mock('../../../services/apiRequests', () => ({
  updateUserProfile: jest.fn().mockResolvedValue({}),
}));

jest.mock('../../../utils/marketingAnalytics', () => ({
  trackMarketingEvent: jest.fn(),
}));

describe('FirstBatchModal', () => {
  it('renders celebration copy and dismisses with preference save', async () => {
    render(
      <MemoryRouter>
        <FirstBatchModal
          open
          celebration={{
            show: true,
            headline: 'Your biggest leak is loose pieces.',
            cta_label: 'Review your #1 priority',
            cta_href: '/game/5/analysis?mode=review&batch=1',
            batch_id: 1,
          }}
          onDismiss={jest.fn()}
        />
      </MemoryRouter>
    );

    expect(screen.getByText(/first Batch Coach report is ready/i)).toBeInTheDocument();
    expect(screen.getByText(/loose pieces/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Browse report/i }));

    await waitFor(() => {
      expect(updateUserProfile).toHaveBeenCalledWith(
        expect.objectContaining({
          preferences: expect.objectContaining({
            first_batch_celebrated_at: expect.any(String),
          }),
        })
      );
    });
  });

  it('returns null when celebration is hidden', () => {
    const { container } = render(
      <MemoryRouter>
        <FirstBatchModal open={false} celebration={{ show: false }} />
      </MemoryRouter>
    );
    expect(container).toBeEmptyDOMElement();
  });
});
