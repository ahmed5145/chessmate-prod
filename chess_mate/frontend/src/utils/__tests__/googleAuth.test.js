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
});
