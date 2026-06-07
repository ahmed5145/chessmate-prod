import {
  collectPracticeNextLinks,
  getRemainingStudyDrillLinks,
} from '../practiceNextLinks';

describe('collectPracticeNextLinks', () => {
  const coachingReport = {
    top_3_priorities: [
      {
        rank: 1,
        title: 'Stop hanging pieces',
        why_it_matters: 'You lost material in game_0.',
        how_to_fix: 'Scan for undefended pieces.',
        specific_drill: 'Do 15 hanging-piece puzzles.',
      },
      {
        rank: 2,
        title: 'Fork awareness',
        why_it_matters: 'Forks hurt you.',
        how_to_fix: 'Look for knight forks.',
        specific_drill: 'Practice fork puzzles.',
      },
    ],
  };

  const batchSummary = {
    recurring_weaknesses: [
      { pattern: 'pin' },
      { pattern: 'fork' },
      { pattern: 'skewer' },
    ],
  };

  it('includes priority #1 drill and up to two unique batch links', () => {
    const links = collectPracticeNextLinks({
      coaching_report: coachingReport,
      batch_summary: batchSummary,
      per_game_results: [],
    });

    expect(links.length).toBe(3);
    expect(links[0].source).toBe('priority');
    expect(links[0].headline).toBe('Priority #1 drill');
    expect(links[1].source).toBe('batch');
    expect(links[2].source).toBe('batch');
    expect(new Set(links.map((link) => link.url)).size).toBe(3);
  });
});

describe('getRemainingStudyDrillLinks', () => {
  it('omits links already shown in the practice strip', () => {
    const batchReport = {
      coaching_report: {
        top_3_priorities: [
          {
            rank: 1,
            title: 'Forks',
            why_it_matters: 'x',
            how_to_fix: 'x',
            specific_drill: 'x',
          },
        ],
      },
      batch_summary: {
        recurring_weaknesses: [{ pattern: 'pin' }, { pattern: 'fork' }],
      },
    };

    const remaining = getRemainingStudyDrillLinks(batchReport);
    expect(remaining.length).toBe(0);
  });

  it('keeps extra drill links beyond the practice strip', () => {
    const batchReport = {
      batch_summary: {
        recurring_weaknesses: [
          { pattern: 'pin' },
          { pattern: 'fork' },
          { pattern: 'skewer' },
        ],
      },
    };

    const remaining = getRemainingStudyDrillLinks(batchReport);
    expect(remaining.length).toBe(1);
    expect(remaining[0].label).toMatch(/Skewer/i);
  });
});
