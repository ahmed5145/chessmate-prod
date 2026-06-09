export const SOUND_STORAGE_KEY = 'sg_sound_enabled';

export const readSoundEnabled = () => {
  if (typeof window === 'undefined' || !window.localStorage) {
    return false;
  }
  return window.localStorage.getItem(SOUND_STORAGE_KEY) === '1';
};

export const writeSoundEnabled = (enabled) => {
  if (typeof window === 'undefined' || !window.localStorage) {
    return;
  }
  if (enabled) {
    window.localStorage.setItem(SOUND_STORAGE_KEY, '1');
  } else {
    window.localStorage.removeItem(SOUND_STORAGE_KEY);
  }
};

export const prefersReducedMotionFeedback = () => {
  if (typeof window === 'undefined' || !window.matchMedia) {
    return false;
  }
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
};

export const mapClassificationToFeedbackTone = (classification) => {
  const key = String(classification || 'neutral').toLowerCase().replace(/\s+/g, '_');
  if (['blunder', 'missed_win', 'mistake', 'inaccuracy'].includes(key)) {
    return 'error';
  }
  if (['best', 'brilliant', 'good', 'book'].includes(key)) {
    return 'positive';
  }
  return 'neutral';
};

const TONE_NOTES = {
  neutral: [{ frequency: 520, type: 'triangle', gain: 0.05, duration: 0.05 }],
  positive: [
    { frequency: 660, type: 'triangle', gain: 0.045, duration: 0.05 },
    { frequency: 880, type: 'triangle', gain: 0.04, duration: 0.07, delay: 0.045 },
  ],
  error: [
    { frequency: 280, type: 'square', gain: 0.04, duration: 0.07 },
    { frequency: 180, type: 'square', gain: 0.035, duration: 0.09, delay: 0.06 },
  ],
};

let audioContext = null;

const getAudioContext = () => {
  if (typeof window === 'undefined') {
    return null;
  }
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtx) {
    return null;
  }
  if (!audioContext) {
    audioContext = new AudioCtx();
  }
  return audioContext;
};

const playToneNote = (ctx, { frequency, type, gain, duration, delay = 0 }) => {
  const startAt = ctx.currentTime + delay;
  const oscillator = ctx.createOscillator();
  const gainNode = ctx.createGain();
  oscillator.type = type;
  oscillator.frequency.setValueAtTime(frequency, startAt);
  gainNode.gain.setValueAtTime(0.0001, startAt);
  gainNode.gain.exponentialRampToValueAtTime(Math.max(gain, 0.0002), startAt + 0.008);
  gainNode.gain.exponentialRampToValueAtTime(0.0001, startAt + duration);
  oscillator.connect(gainNode);
  gainNode.connect(ctx.destination);
  oscillator.start(startAt);
  oscillator.stop(startAt + duration + 0.01);
};

export const playMoveFeedbackTone = (classification, { force = false } = {}) => {
  if (!force && (!readSoundEnabled() || prefersReducedMotionFeedback())) {
    return;
  }

  const ctx = getAudioContext();
  if (!ctx) {
    return;
  }

  const tone = mapClassificationToFeedbackTone(classification);
  const notes = TONE_NOTES[tone] || TONE_NOTES.neutral;

  if (ctx.state === 'suspended') {
    ctx.resume().catch(() => {});
  }

  notes.forEach((note) => playToneNote(ctx, note));
};

export const triggerMoveFeedbackHaptic = (classification) => {
  if (typeof navigator === 'undefined' || typeof navigator.vibrate !== 'function') {
    return;
  }
  const key = String(classification || '').toLowerCase().replace(/\s+/g, '_');
  if (key === 'blunder' || key === 'missed_win') {
    navigator.vibrate(10);
  }
};

export const emitMoveNavigationFeedback = (classification) => {
  playMoveFeedbackTone(classification);
  triggerMoveFeedbackHaptic(classification);
};
