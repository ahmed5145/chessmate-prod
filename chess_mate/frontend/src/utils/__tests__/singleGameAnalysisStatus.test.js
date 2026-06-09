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

  it('passes through progress messages with background hint', () => {
    const result = humanizeAnalysisStatusMessage('Analyzing move 12 of 40', 35);

    expect(result.status).toBe('Analyzing move 12 of 40');
    expect(result.detail).toMatch(/background/i);
  });
});
