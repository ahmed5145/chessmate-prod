import {
  buildSingleGameAnalysisLink,
  parseSingleGameAnalysisSearch,
} from '../singleGameAnalysisLinks';

describe('singleGameAnalysisLinks', () => {
  it('builds base link without query params', () => {
    expect(buildSingleGameAnalysisLink({ gameId: 42 })).toBe('/game/42/analysis');
  });

  it('builds link with batch and move params', () => {
    expect(
      buildSingleGameAnalysisLink({ gameId: 42, batchId: 7, move: 18, priority: 2 })
    ).toBe('/game/42/analysis?batch=7&move=18&priority=2');
  });

  it('parses search params from location search', () => {
    expect(parseSingleGameAnalysisSearch('?batch=7&move=18&priority=1')).toEqual({
      batchId: '7',
      move: 18,
      priority: 1,
    });
  });
});
