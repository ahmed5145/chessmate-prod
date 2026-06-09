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

const TONE_FREQUENCIES = {
  error: 220,
  positive: 660,
  neutral: 440,
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

export const playMoveFeedbackTone = (classification, { force = false } = {}) => {
  if (!force && (!readSoundEnabled() || prefersReducedMotionFeedback())) {
    return;
  }

  const ctx = getAudioContext();
  if (!ctx) {
    return;
  }

  const tone = mapClassificationToFeedbackTone(classification);
  const frequency = TONE_FREQUENCIES[tone];

  if (ctx.state === 'suspended') {
    ctx.resume().catch(() => {});
  }

  const oscillator = ctx.createOscillator();
  const gain = ctx.createGain();
  oscillator.type = 'sine';
  oscillator.frequency.value = frequency;
  gain.gain.setValueAtTime(0.08, ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.08);
  oscillator.connect(gain);
  gain.connect(ctx.destination);
  oscillator.start(ctx.currentTime);
  oscillator.stop(ctx.currentTime + 0.09);
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
