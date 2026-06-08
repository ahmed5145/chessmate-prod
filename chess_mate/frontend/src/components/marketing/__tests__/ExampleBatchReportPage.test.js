import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import api from '../../../services/api';
import ExampleBatchReportPage from '../ExampleBatchReportPage';

jest.mock('../../batch/BatchReportSections', () => function MockSections({ readOnly }) {
  return <div data-testid="example-sections">{readOnly ? 'read-only' : 'owner'}</div>;
});

jest.mock('../../../services/api', () => ({
  get: jest.fn(),
}));

describe('ExampleBatchReportPage', () => {
  beforeEach(() => {
    api.get.mockResolvedValue({ data: { signup_bonus_credits: 15 } });
  });

  it('renders example header and read-only report sections', async () => {
    render(
      <MemoryRouter>
        <ExampleBatchReportPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/Example Batch Coach report/i)).toBeInTheDocument();
    expect(screen.getByText(/anonymized games/i)).toBeInTheDocument();

    expect(await screen.findByTestId('example-sections')).toHaveTextContent('read-only');

    const registerLinks = screen.getAllByRole('link', { name: /Get your own/i });
    expect(registerLinks[0]).toHaveAttribute('href', '/register?from=example-batch-report');
  });
});
