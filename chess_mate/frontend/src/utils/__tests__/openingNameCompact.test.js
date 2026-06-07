import { compactOpeningName } from '../openingNameCompact';

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
