/** User-facing message for regenerate-coaching API failures. */

export const formatRegenerateCoachingError = (error) => {
  const payload = error?.code ? error : error?.response?.data || error;

  if (payload?.code === 'COACH_001') {
    return (
      payload.message
      || 'Coaching refresh limit reached for today. Try again tomorrow.'
    );
  }

  if (typeof payload?.detail === 'string') {
    return payload.detail;
  }

  if (payload?.message) {
    return payload.message;
  }

  return 'Could not refresh coaching. Try again in a few minutes.';
};
