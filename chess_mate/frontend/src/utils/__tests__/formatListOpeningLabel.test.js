import { formatListOpeningLabel } from '../formatListOpeningLabel';

describe('formatListOpeningLabel', () => {
  it('returns compact opening name when known', () => {
    expect(
      formatListOpeningLabel({
        opening_name: "Queen's Pawn Game: London System",
        eco_code: 'D02',
      })
    ).toBe("Queen's Pawn Game: London System");
  });

  it('resolves ECO when opening name is unknown', () => {
    const label = formatListOpeningLabel({
      opening_name: 'Unknown Opening',
      eco_code: 'B73',
    });
    expect(label).toContain('Dragon');
    expect(label).not.toBe('Unknown Opening');
  });

  it('uses em dash when no opening data', () => {
    expect(formatListOpeningLabel({ opening_name: 'Unknown Opening' })).toBe('—');
  });
});
