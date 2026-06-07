import { lichessOpeningSearchUrl } from '../lichessStudyLinks';

describe('lichessOpeningSearchUrl', () => {
  it('links to Lichess study search sorted by popularity', () => {
    const url = lichessOpeningSearchUrl("Queen's Pawn");
    expect(url).toBe("https://lichess.org/study/search?order=hot&q=Queen%27s+Pawn");
  });

  it('falls back to a generic opening query', () => {
    const url = lichessOpeningSearchUrl('');
    expect(url).toContain('lichess.org/study/search');
    expect(url).toContain('order=hot');
  });
});
