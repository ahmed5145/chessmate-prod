import { lichessOpeningSearchUrl, resolvePriorityLichessLink } from '../lichessStudyLinks';

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

  it('strips move-tree suffixes from verbose opening headers', () => {
    const url = lichessOpeningSearchUrl(
      'Sicilian Defense Open Dragon Classical Attack...8.O O O O 9.f4 Qb6'
    );
    expect(url).toContain(
      'q=Sicilian+Defense+Open+Dragon+Classical+Attack'
    );
    expect(url).not.toContain('9.f4');
    expect(url).not.toContain('Qb6');
  });
});

describe('resolvePriorityLichessLink', () => {
  it('maps hanging-piece priorities to Lichess puzzle training', () => {
    const link = resolvePriorityLichessLink({
      title: 'Thematic Tactical Training on Hanging Pieces',
      how_to_fix: 'Practice recognizing hanging pieces.',
      specific_drill: '20 themed tactics on hanging piece.',
    });
    expect(link.kind).toBe('puzzle');
    expect(link.url).toContain('lichess.org/training/hangingPiece');
    expect(link.label).toBe('Train on Lichess');
  });

  it('maps opening priorities to Lichess study search', () => {
    const link = resolvePriorityLichessLink({
      title: 'Deepen Opening Theory on London System',
      how_to_fix: 'Study specific lines and ideas from the London System.',
      specific_drill: 'Review 5 top games played by masters in the London System.',
    });
    expect(link.kind).toBe('opening');
    expect(link.url).toContain('lichess.org/study/search');
    expect(link.url).toContain('London');
    expect(link.label).toBe('Study on Lichess');
  });

  it('maps endgame priorities to Lichess endgame practice', () => {
    const link = resolvePriorityLichessLink({
      title: 'General Endgame Technique Improvement',
      how_to_fix: 'Focus on king activation in conversions.',
      specific_drill: 'Review fundamental endgame techniques online.',
    });
    expect(link.kind).toBe('endgame');
    expect(link.url).toContain('lichess.org/learn');
    expect(link.label).toBe('Practice on Lichess');
  });
});
