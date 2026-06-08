import { initMarketingAnalytics, trackMarketingEvent, trackSingleGameEvent } from '../marketingAnalytics';

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

  it('tags single-game events with surface metadata', () => {
    trackSingleGameEvent('single_game_view', { game_id: '42' });

    expect(window.dataLayer[0]).toMatchObject({
      chessmate_event: 'single_game_view',
      surface: 'single_game',
      game_id: '42',
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
