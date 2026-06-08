import { setPageMeta, DEFAULT_SITE_TITLE } from '../pageMeta';

describe('pageMeta', () => {
  beforeEach(() => {
    document.head.innerHTML = '';
    document.title = DEFAULT_SITE_TITLE;
  });

  it('sets document title and description meta', () => {
    setPageMeta({
      title: 'Example report',
      description: 'Batch Coach demo',
      path: '/example/batch-report',
    });

    expect(document.title).toBe('Example report · ChessMate');
    expect(document.querySelector('meta[name="description"]').getAttribute('content')).toBe('Batch Coach demo');
    expect(document.querySelector('meta[property="og:title"]').getAttribute('content')).toBe('Example report · ChessMate');
    expect(document.querySelector('link[rel="canonical"]').getAttribute('href')).toContain('/example/batch-report');
  });
});
