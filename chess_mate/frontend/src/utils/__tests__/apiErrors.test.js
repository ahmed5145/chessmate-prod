import { extractApiError } from '../apiErrors';

describe('extractApiError', () => {
  it('returns fallback for empty input', () => {
    expect(extractApiError(null, 'Fallback')).toBe('Fallback');
    expect(extractApiError(undefined, 'Fallback')).toBe('Fallback');
  });

  it('returns plain string errors', () => {
    expect(extractApiError('  Bad request  ', 'Fallback')).toBe('  Bad request  ');
  });

  it('prefers response detail', () => {
    const error = { response: { data: { detail: 'Batch not found' } } };
    expect(extractApiError(error, 'Fallback')).toBe('Batch not found');
  });

  it('reads message and error fields', () => {
    expect(extractApiError({ response: { data: { message: 'Server busy' } } }, 'x')).toBe(
      'Server busy'
    );
    expect(extractApiError({ response: { data: { error: 'Invalid token' } } }, 'x')).toBe(
      'Invalid token'
    );
  });

  it('reads first errors array entry', () => {
    const error = {
      response: {
        data: {
          errors: [{ message: 'Email is required' }],
        },
      },
    };
    expect(extractApiError(error, 'Fallback')).toBe('Email is required');
  });

  it('joins field validation messages', () => {
    const error = {
      response: {
        data: {
          email: ['Enter a valid email.'],
          password: ['Too short.'],
        },
      },
    };
    expect(extractApiError(error, 'Fallback')).toBe(
      'email: Enter a valid email. password: Too short.'
    );
  });

  it('uses Error.message when response is missing', () => {
    expect(extractApiError(new Error('Custom failure'), 'Fallback')).toBe('Custom failure');
  });
});
