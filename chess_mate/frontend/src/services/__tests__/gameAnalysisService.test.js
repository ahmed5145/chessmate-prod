import { classifyAnalysisPollingStatus, computeNextPollDelay } from '../gameAnalysisService';

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
});
