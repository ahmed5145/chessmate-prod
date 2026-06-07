import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import TopCriticalMoments from '../TopCriticalMoments';
import { scrollToBatchGame } from '../../../utils/batchGameLinks';

jest.mock('../FenBoardImage', () => function MockFenBoard({ fen }) {
  return <div data-testid="fen-board">{fen}</div>;
});

jest.mock('../../../utils/batchGameLinks', () => ({
  ...jest.requireActual('../../../utils/batchGameLinks'),
  scrollToBatchGame: jest.fn(),
}));

const perGameResults = [
  {
    game_id: 'game_0',
    saved_game_id: 42,
    white: 'Alice',
    black: 'Bob',
    player_color: 'white',
    platform: 'lichess',
    platform_game_url: 'https://lichess.org/xyz',
    critical_moments: [
      {
        move_number: 18,
        type: 'blunder',
        fen: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR',
        played_move: 'Qh5',
        best_move: 'Nf3',
        eval_swing: 3.25,
        explanation: 'You hung the queen on move 18.',
        played_move_uci: 'd1h5',
        best_move_uci: 'g1f3',
      },
    ],
  },
];

const renderMoments = (props) =>
  render(
    <MemoryRouter>
      <TopCriticalMoments per_game_results={perGameResults} {...props} />
    </MemoryRouter>
  );

describe('TopCriticalMoments', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders nothing when there are no moments', () => {
    const { container } = renderMoments({ batch_summary: {}, per_game_results: [] });
    expect(container).toBeEmptyDOMElement();
  });

  it('renders summary moments with board and actions', () => {
    renderMoments({
      batch_summary: {
        top_critical_moments: [
          {
            game_id: 'game_0',
            move_number: 18,
            type: 'blunder',
            fen: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR',
            played_move: 'Qh5',
            best_move: 'Nf3',
            eval_swing: 3.25,
            explanation: 'You hung the queen on move 18.',
            player_color: 'white',
            saved_game_id: 42,
          },
        ],
      },
    });

    expect(screen.getByText(/Biggest turning points/i)).toBeInTheDocument();
    expect(screen.getByText('blunder')).toBeInTheDocument();
    expect(screen.getByTestId('fen-board')).toBeInTheDocument();
    expect(screen.getByText(/You played Qh5/i)).toBeInTheDocument();
    expect(screen.getByText(/You hung the queen on move 18/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Saved game analysis/i })).toHaveAttribute(
      'href',
      '/game/42/analysis'
    );
  });

  it('falls back to per-game critical moments when summary is empty', () => {
    renderMoments({ batch_summary: {} });

    expect(screen.getByText(/Move 18 · Game 1/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Open on lichess/i })).toHaveAttribute(
      'href',
      'https://lichess.org/xyz'
    );
    expect(screen.getByRole('link', { name: /Saved game analysis/i })).toHaveAttribute(
      'href',
      '/game/42/analysis'
    );
  });

  it('scrolls to game breakdown on button click', () => {
    renderMoments({ batch_summary: {} });

    fireEvent.click(screen.getByRole('button', { name: /View in breakdown/i }));

    expect(scrollToBatchGame).toHaveBeenCalledWith('game_0');
  });

  it('hides saved game link in read-only mode', () => {
    renderMoments({ batch_summary: {}, readOnly: true });

    expect(screen.queryByRole('link', { name: /Saved game analysis/i })).not.toBeInTheDocument();
  });
});
