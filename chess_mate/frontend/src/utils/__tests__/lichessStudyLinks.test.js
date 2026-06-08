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

  it('builds distinct URLs with ECO and player color', () => {
    const whiteUrl = lichessOpeningSearchUrl("Queen's Pawn Game: London System", {
      ecoCode: 'D02',
      playerColor: 'white',
    });
    const blackUrl = lichessOpeningSearchUrl("Queen's Pawn Game: London System", {
      ecoCode: 'D02',
      playerColor: 'black',
    });

    expect(whiteUrl).toContain('London+System+D02+white');
    expect(blackUrl).toContain('London+System+D02+black');
    expect(whiteUrl).not.toBe(blackUrl);
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
    expect(link.url).not.toContain('opening+repertoire');
    expect(link.label).toBe('Study on Lichess');
  });

  it('uses batch repertoire gaps when opening priority has no explicit line name', () => {
    const link = resolvePriorityLichessLink(
      {
        title: 'Study Opening Theory',
        how_to_fix: 'Review your repertoire and prep before the next batch.',
        specific_drill: 'Pick one line from this batch and study it for 15 minutes.',
      },
      {
        batch_summary: {
          repertoire_gaps: [
            {
              opening_name: "Queen's Pawn Game: London System",
              eco_code: 'D02',
              player_color: 'white',
            },
          ],
        },
      }
    );

    expect(link.kind).toBe('opening');
    expect(link.url).toContain('lichess.org/study/search');
    expect(link.url).toContain('London');
    expect(link.url).not.toContain('opening+repertoire');
  });

  it('uses linked game opening when priority cites game ids without naming the line', () => {
    const link = resolvePriorityLichessLink(
      {
        title: 'Study opening theory from game_0',
        how_to_fix: 'Replay the opening phase from the cited game.',
        specific_drill: 'Review game_0 moves 1-12 and compare to model games.',
      },
      {
        per_game_results: [
          {
            game_id: 'game_0',
            opening_name: 'Sicilian Defense: Najdorf Variation',
            eco_code: 'B90',
            player_color: 'black',
          },
        ],
      }
    );

    expect(link.url).toContain('lichess.org/study/search');
    expect(link.url).toContain('Najdorf');
    expect(link.url).not.toContain('opening+repertoire');
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
