import { API_URL } from '../config';

const resolveApiBase = () => {
  const configured = (API_URL || '').replace(/\/$/, '');
  if (configured) {
    return configured;
  }
  // CRA dev server (:3000) — OAuth must hit Django on :8000, not the SPA origin.
  if (
    typeof window !== 'undefined'
    && (window.location.port === '3000' || window.location.hostname === 'localhost')
  ) {
    return 'http://localhost:8000';
  }
  if (typeof window !== 'undefined') {
    return window.location.origin.replace(/\/$/, '');
  }
  return '';
};

export const buildGoogleAuthStartUrl = ({ referralCode = null, rememberMe = true } = {}) => {
  const base = resolveApiBase();
  const params = new URLSearchParams();
  if (referralCode) {
    params.set('ref', referralCode);
  }
  if (!rememberMe) {
    params.set('remember_me', 'false');
  }
  const query = params.toString();
  return `${base}/api/v1/auth/google/start/${query ? `?${query}` : ''}`;
};

export const parseGoogleCallbackHash = (hash = '') => {
  const raw = hash.startsWith('#') ? hash.slice(1) : hash;
  if (!raw) {
    return null;
  }
  const params = new URLSearchParams(raw);
  const access = params.get('access');
  const refresh = params.get('refresh');
  if (!access || !refresh) {
    return null;
  }
  return { access, refresh };
};
