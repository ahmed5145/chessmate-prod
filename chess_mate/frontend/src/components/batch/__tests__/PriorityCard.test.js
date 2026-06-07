import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import PriorityCard from '../PriorityCard';
import { scrollToBatchGame } from '../../../utils/batchGameLinks';

jest.mock('../LichessActionButton', () => function MockLichessButton({ label }) {
  return <a href="https://lichess.org/study/mock">{label}</a>;
});

jest.mock('../../../utils/batchGameLinks', () => ({
  ...jest.requireActual('../../../utils/batchGameLinks'),
  scrollToBatchGame: jest.fn(),
}));

const basePriority = {
  rank: 1,
  title: 'Stop leaving pieces hanging in game_0',
  why_it_matters: 'You lost material twice in game_0.',
  how_to_fix: 'Scan for undefended pieces before every move.',
  specific_drill: 'Practice: Do 10 hanging-piece puzzles.',
};

const perGameResults = [
  {
    game_id: 'game_0',
    white: 'Alice',
    black: 'Bob',
    player_color: 'white',
    platform: 'lichess',
    platform_game_url: 'https://lichess.org/abc123',
  },
];

describe('PriorityCard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders nothing for incomplete priority data', () => {
    const { container } = render(<PriorityCard priority={{ rank: 1, title: 'Only title' }} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('humanizes game ids and renders drill plus action links', () => {
    render(<PriorityCard priority={basePriority} per_game_results={perGameResults} />);

    expect(screen.getByText(/Stop leaving pieces hanging in Game 1/i)).toBeInTheDocument();
    expect(screen.getByText(/You lost material twice in Game 1/i)).toBeInTheDocument();
    expect(screen.getByText(/Do 10 hanging-piece puzzles/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Train on Lichess/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Open on Lichess/i })).toHaveAttribute(
      'href',
      'https://lichess.org/abc123'
    );
  });

  it('scrolls to linked game when view button is clicked', () => {
    render(<PriorityCard priority={basePriority} per_game_results={perGameResults} showLichessLink={false} />);

    fireEvent.click(screen.getByRole('button', { name: /View Game 1/i }));

    expect(scrollToBatchGame).toHaveBeenCalledWith('game_0');
  });
});
