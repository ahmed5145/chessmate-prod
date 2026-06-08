export const MARKETING_SOURCES = {
  LANDING_EXAMPLE: 'landing-example',
  LANDING_HERO: 'landing-hero',
  EXAMPLE_PAGE: 'example-batch-report',
  HOW_IT_WORKS: 'how-it-works',
  SHARED_REPORT: 'shared-report',
};

export const buildRegisterHref = (source = MARKETING_SOURCES.LANDING_EXAMPLE) => (
  `/register?from=${encodeURIComponent(source)}`
);

export const buildLoginHref = (source = MARKETING_SOURCES.LANDING_EXAMPLE) => (
  `/login?from=${encodeURIComponent(source)}`
);

export const getMarketingSourceFromSearch = (search = '') => {
  if (!search) {
    return null;
  }
  const params = new URLSearchParams(search.startsWith('?') ? search : `?${search}`);
  const from = params.get('from');
  return from?.trim() || null;
};
