import { formatGamePlatformLabel } from '../gamePlatformLabel';

describe('formatGamePlatformLabel', () => {
  it('maps known platform ids', () => {
    expect(formatGamePlatformLabel('chess.com')).toBe('Chess.com');
    expect(formatGamePlatformLabel('lichess')).toBe('Lichess');
  });

  it('returns null for missing or unknown platforms', () => {
    expect(formatGamePlatformLabel(null)).toBeNull();
    expect(formatGamePlatformLabel('unknown')).toBeNull();
  });
});
