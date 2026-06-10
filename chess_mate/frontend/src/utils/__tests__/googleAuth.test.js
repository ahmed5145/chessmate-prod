import { buildGoogleAuthStartUrl, parseGoogleCallbackHash } from '../googleAuth';

describe('googleAuth', () => {
  it('builds start URL with referral and remember_me', () => {
    const url = buildGoogleAuthStartUrl({ referralCode: 'abc', rememberMe: false });
    expect(url).toContain('/api/v1/auth/google/start/');
    expect(url).toContain('ref=abc');
    expect(url).toContain('remember_me=false');
  });

  it('parses callback hash tokens', () => {
    const tokens = parseGoogleCallbackHash('#access=abc&refresh=def');
    expect(tokens).toEqual({ access: 'abc', refresh: 'def' });
  });

  it('defaults to localhost:8000 when SPA runs on port 3000', () => {
    const original = window.location;
    delete window.location;
    window.location = { port: '3000', hostname: 'localhost', origin: 'http://localhost:3000' };
    const url = buildGoogleAuthStartUrl();
    expect(url).toMatch(/^http:\/\/localhost:8000\/api\/v1\/auth\/google\/start\//);
    window.location = original;
  });
});
