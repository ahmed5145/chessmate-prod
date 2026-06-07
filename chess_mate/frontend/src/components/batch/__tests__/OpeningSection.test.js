import React from 'react';
import { render, screen } from '@testing-library/react';
import OpeningSection from '../OpeningSection';

jest.mock('../LichessActionButton', () => function MockLichessButton({ label }) {
  return <button type="button">{label}</button>;
});

jest.mock('../GameExampleActions', () => function MockGameExampleActions() {
  return <span data-testid="game-example-actions">Example</span>;
});

jest.mock('../OpeningRecommendationText', () => function MockRecommendation({ item }) {
  return <span data-testid="opening-recommendation">{item.recommendation}</span>;
});

const perGameResults = [
  {
    game_id: 'game_0',
    result: '0-1',
    player_color: 'white',
    opening_name: "Queen's Pawn Game",
    eco_code: 'D00',
    platform: 'lichess',
    platform_game_url: 'https://lichess.org/abc',
    phase_breakdown: { opening: { moves: 8, avg_eval_drop: 0.3 } },
  },
  {
    game_id: 'game_1',
    result: '1-0',
    player_color: 'white',
    opening_name: 'Sicilian Defense',
    eco_code: 'B90',
    phase_breakdown: { opening: { moves: 9, avg_eval_drop: 0.2 } },
  },
];

describe('OpeningSection', () => {
  it('shows info alert when there is no opening data', () => {
    render(<OpeningSection batch_summary={{}} per_game_results={[]} />);

    expect(screen.getByText(/No recognizable opening data/i)).toBeInTheDocument();
  });

  it('renders repertoire gaps and example game link', () => {
    render(
      <OpeningSection
        batch_summary={{
          repertoire_gaps: [
            {
              opening_name: "Queen's Pawn Game",
              eco_code: 'D00',
              player_color: 'white',
              record: '0W-1L-0D',
              summary: 'This line needs review.',
            },
          ],
        }}
        per_game_results={perGameResults}
      />
    );

    expect(screen.getByText(/Lines to review/i)).toBeInTheDocument();
    expect(screen.getByText(/This line needs review/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /View game on lichess/i })).toHaveAttribute(
      'href',
      'https://lichess.org/abc'
    );
    expect(screen.getByRole('button', { name: /Study on Lichess/i })).toBeInTheDocument();
  });

  it('shows success alert when there are no repertoire gaps', () => {
    render(
      <OpeningSection
        batch_summary={{}}
        per_game_results={[
          {
            game_id: 'game_2',
            result: '1-0',
            player_color: 'white',
            opening_name: 'Sicilian Defense',
            eco_code: 'B90',
            phase_breakdown: { opening: { moves: 9, avg_eval_drop: 0.2 } },
          },
        ]}
      />
    );

    expect(screen.getByText(/No major repertoire gaps/i)).toBeInTheDocument();
    expect(screen.getByText(/Game-by-game results/i)).toBeInTheDocument();
    expect(screen.getByText(/Sicilian Defense/i)).toBeInTheDocument();
  });

  it('formats W/L/D result labels in the table', () => {
    render(
      <OpeningSection
        batch_summary={{}}
        per_game_results={[
          {
            game_id: 'game_w',
            result: '1-0',
            player_color: 'white',
            opening_name: 'Italian Game',
            eco_code: 'C50',
            phase_breakdown: { opening: { moves: 8, avg_eval_drop: 0.1 } },
          },
          {
            game_id: 'game_l',
            result: '0-1',
            player_color: 'white',
            opening_name: 'French Defense',
            eco_code: 'C00',
            phase_breakdown: { opening: { moves: 8, avg_eval_drop: 0.4 } },
          },
        ]}
      />
    );

    const rows = screen.getAllByRole('row');
    expect(rows.some((row) => row.textContent.includes('Italian Game') && row.textContent.includes('W'))).toBe(
      true
    );
    expect(rows.some((row) => row.textContent.includes('French') && row.textContent.includes('L'))).toBe(true);
  });
});
