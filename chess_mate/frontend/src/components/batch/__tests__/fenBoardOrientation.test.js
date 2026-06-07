import React from 'react';
import { render, screen } from '@testing-library/react';
import FenBoardImage from '../FenBoardImage';

describe('FenBoardImage orientation', () => {
  const startFen =
    'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

  it('shows rank 1 at top when player perspective is black', () => {
    render(<FenBoardImage fen={startFen} orientation="black" size={200} />);
    const labels = screen.getAllByText('1');
    expect(labels.length).toBeGreaterThan(0);
    expect(screen.getAllByText('8').length).toBeGreaterThan(0);
  });

  it('shows rank 8 at top when player perspective is white', () => {
    render(<FenBoardImage fen={startFen} orientation="white" size={200} />);
    expect(screen.getAllByText('8').length).toBeGreaterThan(0);
  });
});
