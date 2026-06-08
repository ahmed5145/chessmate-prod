/**
 * Lightweight marketing events — hook to analytics (GTM, etc.) via window listener.
 */

export const trackMarketingEvent = (event, detail = {}) => {
  if (typeof window === 'undefined') {
    return;
  }
  window.dispatchEvent(new CustomEvent('chessmate:marketing', {
    detail: { event, ...detail, ts: Date.now() },
  }));
};
