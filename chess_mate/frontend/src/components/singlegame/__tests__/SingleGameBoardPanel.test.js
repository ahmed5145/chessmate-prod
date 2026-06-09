import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import SingleGameBoardPanel from '../SingleGameBoardPanel';

jest.mock('../../../context/ThemeContext', () => ({
  useTheme: () => ({ isDarkMode: false }),
}));

jest.mock('../../batch/FenBoardImage', () => function MockFenBoard({ fen }) {
  return <div data-testid="fen-board">{fen}</div>;
});

jest.mock('../../analysis/EvalChart', () => function MockEvalChart() {
  return <div data-testid="eval-chart" />;
});

const sampleMoves = [
  {
    moveNumber: 1,
    san: 'e4',
    fen: 'fen-after-e4',
    classification: 'good',
    isCritical: false,
    isWhite: true,
    displayLabel: '1. e4',
  },
  {
    moveNumber: 1,
    san: 'e5',
    fen: 'fen-after-e5',
    classification: 'best',
    isCritical: true,
    isWhite: false,
    displayLabel: '1... e5',
  },
  {
    moveNumber: 2,
    san: 'Nf3',
    fen: 'fen-after-nf3',
    classification: 'inaccuracy',
    isCritical: false,
    isWhite: true,
    displayLabel: '2. Nf3',
  },
];

describe('SingleGameBoardPanel', () => {
  it('opens expanded view and steps through moves with arrow keys', () => {
    render(
      <SingleGameBoardPanel
        moves={sampleMoves}
        initialMoveNumber={1}
        playerColor="white"
      />
    );

    expect(screen.getByTestId('fen-board')).toHaveTextContent('fen-after-e4');

    fireEvent.click(screen.getByRole('button', { name: /expand position review/i }));

    expect(screen.getByRole('dialog', { name: /expanded position review/i })).toBeInTheDocument();
    expect(screen.getAllByText(/1\. e4/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/2 moves/i).length).toBeGreaterThan(0);

    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(screen.getAllByTestId('fen-board')[0]).toHaveTextContent('fen-after-e5');

    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(screen.getAllByTestId('fen-board')[0]).toHaveTextContent('fen-after-nf3');

    fireEvent.keyDown(window, { key: 'ArrowLeft' });
    expect(screen.getAllByTestId('fen-board')[0]).toHaveTextContent('fen-after-e5');

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('dialog', { name: /expanded position review/i })).not.toBeInTheDocument();
  });
});
