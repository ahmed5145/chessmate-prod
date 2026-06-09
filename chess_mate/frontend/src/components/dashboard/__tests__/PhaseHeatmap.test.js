import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import PhaseResultHeatmap from '../PhaseResultHeatmap';

jest.mock('../../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

describe('PhaseResultHeatmap', () => {
  it('renders nothing when heatmap is hidden', () => {
    const { container } = render(
      <MemoryRouter>
        <PhaseResultHeatmap phaseHeatmap={{ show: false }} />
      </MemoryRouter>
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('renders highlighted cell with review link', () => {
    render(
      <MemoryRouter>
        <PhaseResultHeatmap
          phaseHeatmap={{
            show: true,
            analyzed_games: 8,
            results: ['win', 'loss', 'draw'],
            phases: ['opening', 'middlegame', 'endgame'],
            top_insight: {
              headline: 'You lose winning middlegames',
              href: '/game/42/analysis?mode=review&move=18',
            },
            cells: [
              {
                result: 'loss',
                phase: 'middlegame',
                game_count: 4,
                avg_accuracy: 48.2,
                highlight: true,
                headline: 'You lose winning middlegames',
                example_games: [
                  {
                    saved_game_id: 42,
                    move_number: 18,
                    href: '/game/42/analysis?mode=review&move=18',
                  },
                ],
              },
            ],
          }}
        />
      </MemoryRouter>
    );

    expect(screen.getByText(/Result × phase patterns/i)).toBeInTheDocument();
    expect(screen.getByText(/You lose winning middlegames/i)).toBeInTheDocument();
    expect(screen.getAllByText(/48.2%/).length).toBeGreaterThan(0);
    expect(screen.getByRole('link', { name: /48.2%/i })).toHaveAttribute(
      'href',
      '/game/42/analysis?mode=review&move=18'
    );
  });
});
