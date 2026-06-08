import { initMarketingAnalytics, trackMarketingEvent } from '../marketingAnalytics';

describe('marketingAnalytics', () => {
  beforeEach(() => {
    window.dataLayer = [];
    delete window.gtag;
  });

  it('pushes chessmate events to dataLayer', () => {
    trackMarketingEvent('preview_visible', { source: 'landing-example' });

    expect(window.dataLayer).toHaveLength(1);
    expect(window.dataLayer[0]).toMatchObject({
      event: 'chessmate_preview_visible',
      chessmate_event: 'preview_visible',
      source: 'landing-example',
    });
  });

  it('forwards events to gtag when configured', () => {
    const gtag = jest.fn();
    window.gtag = gtag;
    initMarketingAnalytics();

    trackMarketingEvent('cta_click', { location: 'landing_footer' });

    expect(gtag).toHaveBeenCalledWith(
      'event',
      'cta_click',
      expect.objectContaining({ location: 'landing_footer' }),
    );
  });
});
