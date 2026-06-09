import {
  formatSingleGameStreakCopy,
  normalizeStreakState,
  shouldShowSingleGameStreak,
} from '../singleGameStreak';

describe('singleGameStreak', () => {
  it('hides streak below two games', () => {
    expect(shouldShowSingleGameStreak({ count: 1 })).toBe(false);
    expect(formatSingleGameStreakCopy({ count: 1 })).toBeNull();
  });

  it('formats streak copy in plain English', () => {
    expect(formatSingleGameStreakCopy({ count: 3 })).toBe(
      '3 games without a 1+ pawn blunder'
    );
    expect(normalizeStreakState({ count: 2, last_game_id: 9 }).lastGameId).toBe(9);
  });
});
