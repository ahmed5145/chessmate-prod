import axios from 'axios';
import { jwtDecode } from 'jwt-decode';
import { toast } from 'react-hot-toast';

jest.mock('react-hot-toast', () => ({
  toast: { error: jest.fn() },
}));

jest.mock('jwt-decode', () => ({
  jwtDecode: jest.fn(),
}));

jest.mock('../../config', () => ({
  API_URL: 'http://localhost:8000',
}));

let requestHandler;
let responseErrorHandler;

const mockApi = {
  interceptors: {
    request: {
      use: jest.fn((handler) => {
        requestHandler = handler;
      }),
    },
    response: {
      use: jest.fn((_success, errorHandler) => {
        responseErrorHandler = errorHandler;
      }),
    },
  },
  defaults: { headers: { common: {} } },
};

jest.mock('axios', () => ({
  __esModule: true,
  default: {
    create: jest.fn(() => mockApi),
    get: jest.fn(),
    post: jest.fn(),
  },
}));

require('../api');

describe('api interceptors', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it('attaches a valid access token to outgoing requests', async () => {
    localStorage.setItem('access_token', 'valid-token');
    jwtDecode.mockReturnValue({ exp: Date.now() / 1000 + 3600 });

    const config = await requestHandler({
      url: '/api/v1/games/',
      method: 'get',
      headers: {},
    });

    expect(config.headers.Authorization).toBe('Bearer valid-token');
  });

  it('reads access token from legacy tokens storage', async () => {
    localStorage.setItem('tokens', JSON.stringify({ access: 'legacy-access', refresh: 'legacy-refresh' }));
    jwtDecode.mockReturnValue({ exp: Date.now() / 1000 + 3600 });

    const config = await requestHandler({
      url: '/api/v1/profile/',
      method: 'get',
      headers: {},
    });

    expect(config.headers.Authorization).toBe('Bearer legacy-access');
  });

  it('shows a toast on network errors', async () => {
    const error = { message: 'Network Error', config: { url: '/api/v1/games/' } };

    await expect(responseErrorHandler(error)).rejects.toEqual(error);

    expect(toast.error).toHaveBeenCalledWith(
      'Unable to connect to the server. Please try again.',
      expect.objectContaining({ id: 'network-error' })
    );
  });

  it('skips token refresh retry for auth endpoints', async () => {
    const error = {
      response: { status: 401 },
      config: { url: '/api/v1/auth/login/', _retry: false },
    };

    await expect(responseErrorHandler(error)).rejects.toEqual(error);
    expect(axios.post).not.toHaveBeenCalled();
  });
});
