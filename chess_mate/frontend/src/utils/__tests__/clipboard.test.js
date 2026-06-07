import { copyTextToClipboard } from '../clipboard';

describe('copyTextToClipboard', () => {
  const originalClipboard = navigator.clipboard;
  const originalExecCommand = document.execCommand;

  beforeEach(() => {
    document.body.innerHTML = '';
  });

  afterEach(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: originalClipboard,
    });
    document.execCommand = originalExecCommand;
  });

  it('returns false for empty text', async () => {
    await expect(copyTextToClipboard('')).resolves.toBe(false);
    await expect(copyTextToClipboard(null)).resolves.toBe(false);
  });

  it('uses navigator.clipboard when available', async () => {
    const writeText = jest.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });

    await expect(copyTextToClipboard('share-url')).resolves.toBe(true);
    expect(writeText).toHaveBeenCalledWith('share-url');
  });

  it('falls back to execCommand when clipboard write fails', async () => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: jest.fn().mockRejectedValue(new Error('denied')),
      },
    });
    document.execCommand = jest.fn().mockReturnValue(true);

    await expect(copyTextToClipboard('fallback-text')).resolves.toBe(true);
    expect(document.execCommand).toHaveBeenCalledWith('copy');
    expect(document.body.querySelector('textarea')).toBeNull();
  });

  it('returns false when execCommand fails', async () => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: undefined,
    });
    document.execCommand = jest.fn().mockReturnValue(false);

    await expect(copyTextToClipboard('nope')).resolves.toBe(false);
  });
});
