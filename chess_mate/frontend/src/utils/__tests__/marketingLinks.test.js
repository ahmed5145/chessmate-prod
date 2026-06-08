import {
  buildLoginHref,
  buildRegisterHref,
  getMarketingSourceFromSearch,
  MARKETING_SOURCES,
} from '../marketingLinks';

describe('marketingLinks', () => {
  it('builds register href with encoded source', () => {
    expect(buildRegisterHref(MARKETING_SOURCES.LANDING_EXAMPLE)).toBe(
      '/register?from=landing-example'
    );
  });

  it('builds login href with encoded source', () => {
    expect(buildLoginHref(MARKETING_SOURCES.LANDING_HERO)).toBe(
      '/login?from=landing-hero'
    );
  });

  it('reads marketing source from search params', () => {
    expect(getMarketingSourceFromSearch('?from=landing-example')).toBe('landing-example');
    expect(getMarketingSourceFromSearch('')).toBeNull();
  });
});
