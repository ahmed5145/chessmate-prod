// Base API URL: empty = same-origin; paths already include /api/v1/...
// Dev: set REACT_APP_API_URL=http://localhost:8000 in .env
export const API_URL = process.env.REACT_APP_API_URL || '';

// Other configuration constants can be added here
export const VERSION = '1.0.0';
