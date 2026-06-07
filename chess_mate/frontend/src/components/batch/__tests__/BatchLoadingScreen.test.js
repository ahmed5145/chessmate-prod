import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import BatchLoadingScreen from '../BatchLoadingScreen';

const renderScreen = (props) =>
  render(
    <MemoryRouter>
      <BatchLoadingScreen {...props} />
    </MemoryRouter>
  );

describe('BatchLoadingScreen', () => {
  it('renders nothing when status is completed', () => {
    const { container } = renderScreen({
      status: 'completed',
      total_games: 5,
      completed_games: 5,
    });

    expect(container).toBeEmptyDOMElement();
  });

  it('shows pending state without progress bar', () => {
    renderScreen({
      status: 'pending',
      total_games: 3,
      completed_games: 0,
    });

    expect(screen.getByText(/Building your batch coach report/i)).toBeInTheDocument();
    expect(screen.getByText(/Waiting to start/i)).toBeInTheDocument();
    expect(screen.getByText(/Analyzing/)).toBeInTheDocument();
    expect(screen.queryByText(/games analyzed/i)).not.toBeInTheDocument();
  });

  it('shows in-progress state with linear progress', () => {
    const { container } = renderScreen({
      status: 'in_progress',
      total_games: 4,
      completed_games: 2,
      progress: 'Game 2 of 4',
    });

    expect(screen.getByText('Game 2 of 4')).toBeInTheDocument();
    expect(screen.getByText('2 of 4 games analyzed')).toBeInTheDocument();
    const linearProgress = container.querySelector('.MuiLinearProgress-root');
    expect(linearProgress).toHaveAttribute('aria-valuenow', '50');
  });

  it('shows email alert by default and alternate copy when email is disabled', () => {
    const { rerender } = render(
      <MemoryRouter>
        <BatchLoadingScreen status="pending" total_games={1} completed_games={0} />
      </MemoryRouter>
    );

    expect(screen.getByText(/We'll email you when your report is ready/i)).toBeInTheDocument();

    rerender(
      <MemoryRouter>
        <BatchLoadingScreen
          status="pending"
          total_games={1}
          completed_games={0}
          sendsCompletionEmail={false}
        />
      </MemoryRouter>
    );

    expect(screen.getByText(/You can leave this page/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Back to dashboard/i })).toHaveAttribute('href', '/dashboard');
    expect(screen.getByRole('link', { name: /Batch analysis/i })).toHaveAttribute('href', '/batch-analysis');
  });
});
