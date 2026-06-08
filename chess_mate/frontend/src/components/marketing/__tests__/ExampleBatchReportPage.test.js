import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ExampleBatchReportPage from '../ExampleBatchReportPage';
import { getDemoBatchReport } from '../../../content/demoBatchReport';
import useExampleBatchReport from '../../../hooks/useExampleBatchReport';

jest.mock('../../batch/BatchReportSections', () => function MockSections({ readOnly }) {
  return <div data-testid="example-sections">{readOnly ? 'read-only' : 'owner'}</div>;
});

jest.mock('../../../hooks/useExampleBatchReport');

describe('ExampleBatchReportPage', () => {
  beforeEach(() => {
    useExampleBatchReport.mockReturnValue({
      batchReport: getDemoBatchReport(),
      reportSource: 'static',
      loading: false,
      signupBonus: 15,
    });
  });

  it('renders example header and read-only report sections', async () => {
    render(
      <MemoryRouter>
        <ExampleBatchReportPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/Example Batch Coach report/i)).toBeInTheDocument();
    expect(screen.getByText(/anonymized games/i)).toBeInTheDocument();
    expect(screen.getByTestId('example-sections')).toHaveTextContent('read-only');

    const registerLinks = screen.getAllByRole('link', { name: /Get your own/i });
    expect(registerLinks[0]).toHaveAttribute('href', '/register?from=example-batch-report');
  });

  it('shows live demo messaging when report comes from share token', () => {
    useExampleBatchReport.mockReturnValue({
      batchReport: { games_count: 10, status: 'completed', batch_summary: { games_analyzed: 10 } },
      reportSource: 'live',
      loading: false,
      signupBonus: 15,
    });

    render(
      <MemoryRouter>
        <ExampleBatchReportPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/Live example/i)).toBeInTheDocument();
    expect(screen.getByText(/real shared Batch Coach report/i)).toBeInTheDocument();
  });
});
