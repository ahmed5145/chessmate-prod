import { API_URL } from '../config';

export const buildGoogleAuthStartUrl = ({ referralCode = null, rememberMe = true } = {}) => {
  const base = (API_URL || window.location.origin).replace(/\/$/, '');
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
