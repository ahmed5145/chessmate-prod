import { classifyAnalysisPollingStatus, computeNextPollDelay, shouldPollStatus } from '../gameAnalysisService';

describe('gameAnalysisService polling helpers', () => {
  test('classifies success statuses and 100% progress as success', () => {
    expect(classifyAnalysisPollingStatus('SUCCESS', 42).isSuccess).toBe(true);
    expect(classifyAnalysisPollingStatus('completed', 42).isSuccess).toBe(true);
    expect(classifyAnalysisPollingStatus('pending', 100).isSuccess).toBe(true);
  });

  test('classifies terminal failure statuses', () => {
    expect(classifyAnalysisPollingStatus('FAILED', 20).isTerminalFailure).toBe(true);
    expect(classifyAnalysisPollingStatus('AUTH_ERROR', 0).isTerminalFailure).toBe(true);
    expect(classifyAnalysisPollingStatus('processing', 50).isTerminalFailure).toBe(false);
  });

  test('normalizes status to uppercase', () => {
    expect(classifyAnalysisPollingStatus('processing', 30).normalizedStatus).toBe('PROCESSING');
    expect(classifyAnalysisPollingStatus(undefined, 0).normalizedStatus).toBe('');
  });

  test('resets delay to min when no error', () => {
    const nextDelay = computeNextPollDelay({
      currentDelay: 12000,
      minDelay: 3000,
      maxDelay: 15000,
      hadError: false,
    });

    expect(nextDelay).toBe(3000);
  });

  test('applies exponential backoff and caps at max on errors', () => {
    expect(
      computeNextPollDelay({
        currentDelay: 3000,
        minDelay: 3000,
        maxDelay: 15000,
        hadError: true,
      })
    ).toBe(6000);

    expect(
      computeNextPollDelay({
        currentDelay: 12000,
        minDelay: 3000,
        maxDelay: 15000,
        hadError: true,
      })
    ).toBe(15000);
  });

  test('shouldPollStatus stops polling when progress is 100%', () => {
    expect(shouldPollStatus('PENDING', 100)).toBe(false);
    expect(shouldPollStatus('PROCESSING', 100)).toBe(false);
    expect(shouldPollStatus(undefined, 100)).toBe(false);
  });

  test('shouldPollStatus stops polling on success statuses', () => {
    expect(shouldPollStatus('SUCCESS')).toBe(false);
    expect(shouldPollStatus('COMPLETED')).toBe(false);
    expect(shouldPollStatus('success', 50)).toBe(false);
  });

  test('shouldPollStatus stops polling on terminal failure statuses', () => {
    expect(shouldPollStatus('FAILED')).toBe(false);
    expect(shouldPollStatus('ERROR')).toBe(false);
    expect(shouldPollStatus('AUTH_ERROR')).toBe(false);
    expect(shouldPollStatus('REVOKED')).toBe(false);
    expect(shouldPollStatus('FAILURE')).toBe(false);
  });

  test('shouldPollStatus continues polling for active statuses', () => {
    expect(shouldPollStatus('PENDING')).toBe(true);
    expect(shouldPollStatus('STARTED')).toBe(true);
    expect(shouldPollStatus('PROCESSING')).toBe(true);
    expect(shouldPollStatus('IN_PROGRESS')).toBe(true);
    expect(shouldPollStatus('pending', 25)).toBe(true);
    expect(shouldPollStatus('unknown_status', 50)).toBe(true);
  });
});
