import {
  mapClassificationToFeedbackTone,
  playMoveFeedbackTone,
  readSoundEnabled,
  SOUND_STORAGE_KEY,
  triggerMoveFeedbackHaptic,
  writeSoundEnabled,
} from '../singleGameMoveSound';

describe('singleGameMoveSound', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('maps classifications to feedback tones', () => {
    expect(mapClassificationToFeedbackTone('blunder')).toBe('error');
    expect(mapClassificationToFeedbackTone('missed_win')).toBe('error');
    expect(mapClassificationToFeedbackTone('brilliant')).toBe('positive');
    expect(mapClassificationToFeedbackTone('best')).toBe('positive');
    expect(mapClassificationToFeedbackTone('neutral')).toBe('neutral');
  });

  it('defaults sound off until user opts in', () => {
    expect(readSoundEnabled()).toBe(false);
    writeSoundEnabled(true);
    expect(localStorage.getItem(SOUND_STORAGE_KEY)).toBe('1');
    expect(readSoundEnabled()).toBe(true);
    writeSoundEnabled(false);
    expect(readSoundEnabled()).toBe(false);
  });

  it('does not play tone when sound is disabled', () => {
    const start = jest.fn();
    const stop = jest.fn();
    const createOscillator = jest.fn(() => ({
      type: 'sine',
      frequency: { value: 0 },
      connect: jest.fn(),
      start,
      stop,
    }));
    const createGain = jest.fn(() => ({
      gain: {
        setValueAtTime: jest.fn(),
        exponentialRampToValueAtTime: jest.fn(),
      },
      connect: jest.fn(),
    }));

    window.AudioContext = jest.fn(() => ({
      state: 'running',
      currentTime: 0,
      createOscillator,
      createGain,
      destination: {},
    }));

    playMoveFeedbackTone('blunder');
    expect(createOscillator).not.toHaveBeenCalled();

    writeSoundEnabled(true);
    playMoveFeedbackTone('blunder', { force: true });
    expect(createOscillator).toHaveBeenCalled();
    expect(start).toHaveBeenCalled();
    expect(stop).toHaveBeenCalled();
  });

  it('vibrates only for severe errors', () => {
    navigator.vibrate = jest.fn();
    triggerMoveFeedbackHaptic('blunder');
    triggerMoveFeedbackHaptic('missed_win');
    triggerMoveFeedbackHaptic('mistake');
    expect(navigator.vibrate).toHaveBeenCalledTimes(2);
    expect(navigator.vibrate).toHaveBeenCalledWith(10);
  });
});
