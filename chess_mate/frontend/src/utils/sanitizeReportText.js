import { formatNumber } from './formatNumber';

/** Round long float literals embedded in coaching/explanation strings. */
export const sanitizeReportFloats = (text) => {
  if (!text || typeof text !== 'string') {
    return text;
  }
  return text.replace(/(\d+\.\d{3,})/g, (match) => formatNumber(match, 2));
};
