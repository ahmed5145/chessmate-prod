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

jest.mock('../../batch/BatchReportHeader', () => function MockHeader() {
  return <div data-testid="preview-header">Header panel</div>;
});

jest.mock('../../batch/PriorityCard', () => function MockPriority() {
  return <div data-testid="preview-priority">Priority panel</div>;
});

jest.mock('../../batch/PhaseBreakdown', () => function MockPhases() {
  return <div data-testid="preview-phases">Phases panel</div>;
});

jest.mock('../../batch/CoachingInsightsSection', () => function MockInsights() {
  return <div data-testid="preview-insights">Insights panel</div>;
});

jest.mock('../../batch/TrainingPlan', () => function MockPlan() {
  return <div data-testid="preview-plan">Plan panel</div>;
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

  it('shows overview tab by default and switches panels', () => {
    renderPreview();

    expect(screen.getByTestId('preview-hero')).toBeInTheDocument();
    expect(screen.getByTestId('preview-header')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: /Priority/i }));
    expect(screen.getByTestId('preview-priority')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: /Insights/i }));
    expect(screen.getByTestId('preview-phases')).toBeInTheDocument();
    expect(screen.getByTestId('preview-insights')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: /Plan/i }));
    expect(screen.getByTestId('preview-plan')).toBeInTheDocument();
  });
});
