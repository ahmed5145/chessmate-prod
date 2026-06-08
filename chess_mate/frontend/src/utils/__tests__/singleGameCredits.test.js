import {
  hasUsedFirstSingleGameFree,
  qualifiesForFirstSingleGameFree,
} from '../singleGameCredits';

describe('singleGameCredits', () => {
  it('detects unused first free review', () => {
    expect(qualifiesForFirstSingleGameFree({ preferences: {} })).toBe(true);
    expect(hasUsedFirstSingleGameFree({ preferences: { single_game_free_used: true } })).toBe(true);
    expect(qualifiesForFirstSingleGameFree({ preferences: { single_game_free_used: true } })).toBe(false);
  });

  it('never waives re-analyze on the client', () => {
    expect(qualifiesForFirstSingleGameFree({ preferences: {} }, { isReanalyze: true })).toBe(false);
  });
});
