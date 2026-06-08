/**
 * Lightweight marketing events — hook to analytics (GTM, gtag) via window listener.
 */

let analyticsInitialized = false;

const pushToDataLayer = (event, detail = {}) => {
  if (typeof window === 'undefined') {
    return;
  }
  const { event: _eventKey, ...rest } = detail;
  window.dataLayer = window.dataLayer || [];
  window.dataLayer.push({
    ...rest,
    event: `chessmate_${event}`,
    chessmate_event: event,
  });
};

export const initMarketingAnalytics = () => {
  if (analyticsInitialized || typeof window === 'undefined') {
    return;
  }
  analyticsInitialized = true;

  window.addEventListener('chessmate:marketing', (nativeEvent) => {
    const { event, ts, ...detail } = nativeEvent.detail || {};
    if (!event || typeof window.gtag !== 'function') {
      return;
    }
    window.gtag('event', event, { send_to: 'default', ...detail, ts });
  });
};

export const trackMarketingEvent = (event, detail = {}) => {
  if (typeof window === 'undefined') {
    return;
  }
  const payload = { event, ...detail, ts: Date.now() };
  pushToDataLayer(event, payload);
  window.dispatchEvent(new CustomEvent('chessmate:marketing', {
    detail: payload,
  }));
};

/** Product analytics for single-game analysis funnel. */
export const trackSingleGameEvent = (event, detail = {}) => {
  trackMarketingEvent(event, { surface: 'single_game', ...detail });
};
