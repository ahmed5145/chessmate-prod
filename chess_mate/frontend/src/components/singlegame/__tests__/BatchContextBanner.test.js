import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import BatchContextBanner from '../BatchContextBanner';

jest.mock('../../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

describe('BatchContextBanner', () => {
  it('renders priority, pattern, and opening from batch_context', () => {
    render(
      <MemoryRouter>
        <BatchContextBanner
          batchId={9}
          move={18}
          priority={1}
          batchContext={{
            batch_id: 9,
            priority_rank: 1,
            priority: { title: 'Fix Najdorf prep' },
            pattern_label: 'hanging_pieces',
            opening_name: 'Sicilian Defense',
            opening_eco: 'B90',
            game_result: '0-1',
            linked_moment: { move_number: 18 },
            classification_disclaimer: 'Batch depth-14 differs from depth-20.',
          }}
        />
      </MemoryRouter>
    );

    expect(screen.getByText(/From your Batch Coach report/i)).toBeInTheDocument();
    expect(screen.getByText('hanging_pieces')).toBeInTheDocument();
    expect(screen.getByText(/Fix Najdorf prep/i)).toBeInTheDocument();
    expect(screen.getByText(/Sicilian Defense \(B90\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Batch depth-14 differs/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Back to batch report/i })).toHaveAttribute('href', '/batch-report/9');
  });

  it('returns null without batch id', () => {
    const { container } = render(
      <MemoryRouter>
        <BatchContextBanner batchId={null} />
      </MemoryRouter>
    );
    expect(container).toBeEmptyDOMElement();
  });
});
