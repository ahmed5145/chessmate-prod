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

describe('SharedGameMomentPage', () => {
  beforeEach(() => {
    getPublicGameMoment.mockReset();
    document.title = '';
    document.head.querySelectorAll('meta[property^="og:"], meta[name^="twitter:"]').forEach((el) => {
      el.remove();
    });
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

    const ogTitle = document.querySelector('meta[property="og:title"]');
    const ogDescription = document.querySelector('meta[property="og:description"]');
    const twitterCard = document.querySelector('meta[name="twitter:card"]');
    const ogImage = document.querySelector('meta[property="og:image"]');

    expect(ogTitle?.getAttribute('content')).toContain('You lost the center on move 12');
    expect(ogDescription?.getAttribute('content')).toContain('Move 12');
    expect(ogDescription?.getAttribute('content')).toContain('Sicilian');
    expect(twitterCard?.getAttribute('content')).toBe('summary');
    expect(ogImage).toBeNull();
  });
});
