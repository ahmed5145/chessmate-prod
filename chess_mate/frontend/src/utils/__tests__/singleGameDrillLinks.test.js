import {
  buildLichessGameMoveUrl,
  lichessAnalysisFromFen,
  lichessPlyFromMoment,
  resolveSingleGameDrillLink,
} from '../singleGameDrillLinks';

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
    expect(link.url).toContain('lichess.org/study/search');
  });

  it('builds lichess analysis URLs without encoding slashes', () => {
    const fen = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1';
    const url = lichessAnalysisFromFen(fen);
    expect(url).toBe(
      'https://lichess.org/analysis/rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR_b_KQkq_e3_0_1'
    );
    expect(url).not.toContain('%2F');
  });

  it('prefers lichess game replay over FEN analysis when platform URL exists', () => {
    const link = resolveSingleGameDrillLink({
      gameContext: {
        platform_game_url: 'https://lichess.org/AbCdEfGh',
        platform: 'lichess',
      },
      moves: [],
      moment: {
        move_number: 28,
        mover: 'white',
        fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
      },
    });

    expect(link.kind).toBe('moment');
    expect(link.url).toBe('https://lichess.org/AbCdEfGh?move=55');
    expect(link.label).toContain('move 28');
  });

  it('computes ply from mover color', () => {
    expect(lichessPlyFromMoment({ move_number: 14, mover: 'black' })).toBe(28);
    expect(lichessPlyFromMoment({ move_number: 14, mover: 'white' })).toBe(27);
  });

  it('buildLichessGameMoveUrl adds move query param', () => {
    expect(
      buildLichessGameMoveUrl('https://lichess.org/xyz', { move_number: 10, mover: 'black' })
    ).toBe('https://lichess.org/xyz?move=20');
  });
});
