import { resolveSingleGameDrillLink } from '../singleGameDrillLinks';

describe('singleGameDrillLinks', () => {
  it('prefers opening study when opening inaccuracies exist', () => {
    const link = resolveSingleGameDrillLink({
      gameContext: { opening_name: 'French Defense', eco_code: 'C00' },
      moves: [{ moveNumber: 8, classification: 'mistake', fen: 'fen-here' }],
      moment: { move_number: 20, fen: 'other-fen' },
    });

    expect(link.kind).toBe('opening');
    expect(link.label).toContain('French Defense');
    expect(link.label).toContain('inaccurac');
  });
});
