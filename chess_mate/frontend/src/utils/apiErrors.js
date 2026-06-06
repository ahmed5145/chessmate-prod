/**
 * Normalize API/validation errors into a single user-facing string.
 */
export const extractApiError = (error, fallback = 'Something went wrong. Please try again.') => {
  if (!error) {
    return fallback;
  }

  if (typeof error === 'string' && error.trim()) {
    return error;
  }

  const responseData = error.response?.data;
  if (responseData) {
    const fromResponse = formatErrorPayload(responseData);
    if (fromResponse) {
      return fromResponse;
    }
  }

  if (error instanceof Error && error.message && !error.message.includes('Network Error')) {
    return error.message;
  }

  const fromPayload = formatErrorPayload(error);
  if (fromPayload) {
    return fromPayload;
  }

  return fallback;
};

const formatErrorPayload = (payload) => {
  if (!payload || typeof payload !== 'object') {
    return null;
  }

  if (typeof payload.detail === 'string' && payload.detail.trim()) {
    return payload.detail;
  }

  if (Array.isArray(payload.errors) && payload.errors.length > 0) {
    const first = payload.errors[0];
    if (typeof first === 'string' && first.trim()) {
      return first;
    }
    if (first && typeof first.message === 'string' && first.message.trim()) {
      return first.message;
    }
  }

  if (typeof payload.message === 'string' && payload.message.trim()) {
    return payload.message;
  }

  if (typeof payload.error === 'string' && payload.error.trim()) {
    return payload.error;
  }

  const fieldMessages = [];
  for (const [key, value] of Object.entries(payload)) {
    if (['status', 'data', 'code'].includes(key)) {
      continue;
    }
    if (Array.isArray(value)) {
      const joined = value.filter(Boolean).join(', ');
      if (joined) {
        fieldMessages.push(`${key}: ${joined}`);
      }
    } else if (typeof value === 'string' && value.trim()) {
      fieldMessages.push(value);
    }
  }

  return fieldMessages.length ? fieldMessages.join(' ') : null;
};
