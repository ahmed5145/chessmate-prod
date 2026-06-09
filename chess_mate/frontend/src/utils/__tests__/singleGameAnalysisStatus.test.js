import { humanizeAnalysisStatusMessage } from '../singleGameAnalysisStatus';

describe('humanizeAnalysisStatusMessage', () => {
  it('rewrites queued worker messages for users', () => {
    const result = humanizeAnalysisStatusMessage('Task queued, waiting for worker availability', 0);

    expect(result.status).toMatch(/queued/i);
    expect(result.detail).toMatch(/background worker/i);
    expect(result.queued).toBe(true);
  });

  it('rewrites rate-limit messages without failing the review', () => {
    const result = humanizeAnalysisStatusMessage('Rate limit exceeded. Please try again in 16 seconds.', 55);

    expect(result.status).toMatch(/pause/i);
    expect(result.detail).toMatch(/still running/i);
    expect(result.queued).toBe(false);
  });

  it('converts ply-based progress to full-move counts', () => {
    const result = humanizeAnalysisStatusMessage('Analyzing move 21/21', 90);

    expect(result.status).toBe('Analyzing move 11 of 11');
    expect(result.detail).toMatch(/depth-20/i);
  });
});
