import { buildOpeningStudyQuery, compactOpeningName } from '../openingNameCompact';

describe('compactOpeningName', () => {
  it('removes ellipsis move trees', () => {
    expect(
      compactOpeningName('Sicilian Defense Open Dragon Classical Attack...8.O O O O 9.f4 Qb6')
    ).toBe('Sicilian Defense Open Dragon Classical Attack');
  });

  it('keeps readable variation labels', () => {
    expect(compactOpeningName("Queen's Pawn Game: London System")).toBe(
      "Queen's Pawn Game: London System"
    );
  });

  it('drops trailing comma-separated move segments', () => {
    expect(
      compactOpeningName('Sicilian Defense: Dragon Variation, Yugoslav Attack, 10.O-O-O')
    ).toBe('Sicilian Defense: Dragon Variation, Yugoslav Attack');
  });
});

describe('buildOpeningStudyQuery', () => {
  it('prefers variation after colon for study search', () => {
    expect(
      buildOpeningStudyQuery("Queen's Pawn Game: London System")
    ).toBe('London System');
  });

  it('appends ECO code when not already in the query', () => {
    expect(
      buildOpeningStudyQuery('Sicilian Defense: Dragon Variation', 'B70')
    ).toBe('Dragon Variation B70');
  });

  it('appends player color for side-specific study search', () => {
    expect(
      buildOpeningStudyQuery('Caro-Kann Defense', 'B12', 'black')
    ).toBe('Caro-Kann Defense B12 black');
  });

  it('falls back to generic query when name is empty', () => {
    expect(buildOpeningStudyQuery('')).toBe('chess opening');
  });
});
