/**
 * Lightweight marketing events — GA4 gtag + dataLayer (see docs/product/PRODUCT_ANALYTICS_AUDIT.md).
 */

/** GA4 measurement ID — must match index.html gtag config. */
export const GA_MEASUREMENT_ID = 'G-3NLTQ3XH2Y';

let analyticsInitialized = false;

/** SPA route changes: send page_path to GA4 (initial HTML load is covered by gtag config). */
export const trackPageView = (pagePath, pageTitle) => {
  if (typeof window === 'undefined' || typeof window.gtag !== 'function') {
    return;
  }
  window.gtag('config', GA_MEASUREMENT_ID, {
    page_path: pagePath,
    page_title: pageTitle || document.title,
  });
};

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
