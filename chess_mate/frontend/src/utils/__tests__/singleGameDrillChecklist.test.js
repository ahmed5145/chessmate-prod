import {
  buildDrillChecklistItems,
  countChecked,
  drillChecklistStorageKey,
  readDrillChecklistState,
  writeDrillChecklistState,
} from '../singleGameDrillChecklist';

describe('singleGameDrillChecklist', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('builds up to four checklist items from coaching and drill link', () => {
    const items = buildDrillChecklistItems({
      coaching: {
        do_today: 'Play 10 fork puzzles.',
        takeaway: 'You lost the center early.',
      },
      worstMoment: { move_number: 14 },
      drillLink: { label: 'Replay move 14 on Lichess', url: 'https://lichess.org/analysis/abc' },
    });

    expect(items).toHaveLength(4);
    expect(items[0].id).toBe('do_today');
    expect(items[1].id).toBe('replay_moment');
    expect(items[2].id).toBe('lichess_drill');
    expect(items[3].id).toBe('takeaway');
  });

  it('persists checklist state in localStorage', () => {
    const key = drillChecklistStorageKey(42, '2026-06-08T12:00:00Z');
    expect(key).toContain('sg_drill_42_');

    writeDrillChecklistState(key, { do_today: true });
    expect(readDrillChecklistState(key)).toEqual({ do_today: true });
    expect(countChecked([{ id: 'do_today' }, { id: 'replay_moment' }], { do_today: true })).toBe(1);
  });
});
