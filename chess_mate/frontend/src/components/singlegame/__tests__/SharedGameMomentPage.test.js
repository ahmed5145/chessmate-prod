import React from 'react';
import { render, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import SharedGameMomentPage from '../SharedGameMomentPage';
import { getPublicGameMoment } from '../../../services/gameAnalysisService';

jest.mock('../../../services/gameAnalysisService', () => ({
  getPublicGameMoment: jest.fn(),
}));

jest.mock('../../batch/FenBoardImage', () => function MockFenBoardImage() {
  return null;
});

jest.mock('../EngineMetaNote', () => function MockEngineMetaNote() {
  return null;
});

/* eslint-disable testing-library/no-node-access -- OG meta tags live in document.head */
const getMetaContent = (selector) => document.querySelector(selector)?.getAttribute('content') ?? null;
const metaExists = (selector) => document.querySelector(selector);

describe('SharedGameMomentPage', () => {
  beforeEach(() => {
    getPublicGameMoment.mockReset();
    document.title = '';
    document.head.innerHTML = '';
  });

  it('sets text-only share meta tags from moment payload', async () => {
    getPublicGameMoment.mockResolvedValue({
      moment: { move_number: 12, eval_swing: -2.4, played_move: 'Nf3', best_move: 'Nd2' },
      game_context: { opening_name: 'Sicilian', result: 'loss', player_color: 'black' },
      coaching: {
        takeaway: 'You lost the center on move 12',
        do_today: 'Practice knight retreats in the Sicilian.',
      },
    });

    render(
      <MemoryRouter initialEntries={['/share/game-moment/abc123']}>
        <Routes>
          <Route path="/share/game-moment/:shareToken" element={<SharedGameMomentPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(document.title).toContain('You lost the center on move 12');
    });

    expect(getMetaContent('meta[property="og:title"]')).toContain('You lost the center on move 12');
    expect(getMetaContent('meta[property="og:description"]')).toContain('Move 12');
    expect(getMetaContent('meta[property="og:description"]')).toContain('Sicilian');
    expect(getMetaContent('meta[name="twitter:card"]')).toBe('summary');
    expect(metaExists('meta[property="og:image"]')).toBeNull();
  });
});
