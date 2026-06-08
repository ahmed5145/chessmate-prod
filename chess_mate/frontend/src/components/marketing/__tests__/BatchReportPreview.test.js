import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import BatchReportPreview from '../BatchReportPreview';

jest.mock('../../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

jest.mock('../../batch/BatchReportHero', () => function MockHero() {
  return <div data-testid="preview-hero">Hero panel</div>;
});

jest.mock('../../batch/PriorityCard', () => function MockPriority() {
  return <div data-testid="preview-priority">Priority panel</div>;
});

jest.mock('../../batch/PhaseBreakdown', () => function MockPhases() {
  return <div data-testid="preview-phases">Phases panel</div>;
});

const renderPreview = () =>
  render(
    <MemoryRouter>
      <BatchReportPreview />
    </MemoryRouter>
  );

describe('BatchReportPreview', () => {
  it('renders example badge and full example link', () => {
    renderPreview();

    expect(screen.getByText(/Example report · anonymized games/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /View full example/i })).toHaveAttribute(
      'href',
      '/example/batch-report'
    );
  });

  it('shows summary tab by default and switches panels', () => {
    renderPreview();

    expect(screen.getByTestId('preview-hero')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: /Priority/i }));
    expect(screen.getByTestId('preview-priority')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: /Phases/i }));
    expect(screen.getByTestId('preview-phases')).toBeInTheDocument();
  });
});
