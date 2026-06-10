import React, { useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { useTheme } from '../context/ThemeContext';
import { useUser } from '../contexts/UserContext';
import api from '../services/api';
import { getUserProfile } from '../services/apiRequests';
import { setTokens } from '../services/authService';
import { parseGoogleCallbackHash } from '../utils/googleAuth';
import { getRememberMePreference } from '../utils/tokenStorage';

const GoogleAuthCallback = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isDarkMode } = useTheme();
  const { setUser } = useUser();
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) {
      return;
    }
    handled.current = true;

    const error = searchParams.get('error');
    const message = searchParams.get('message');
    if (error) {
      toast.error(message || 'Google sign-in failed.', { id: 'google-auth-error' });
      navigate('/login', { replace: true });
      return;
    }

    const tokens = parseGoogleCallbackHash(window.location.hash);
    if (!tokens) {
      toast.error('Google sign-in did not return valid tokens.', { id: 'google-auth-missing' });
      navigate('/login', { replace: true });
      return;
    }

    const rememberMe = getRememberMePreference();
    setTokens(tokens.access, tokens.refresh, { rememberMe });
    api.defaults.headers.common.Authorization = `Bearer ${tokens.access}`;

    window.history.replaceState(null, '', '/auth/google/callback');

    getUserProfile()
      .then((profileData) => {
        if (profileData) {
          setUser(profileData);
        }
        toast.success('Signed in with Google!', { id: 'google-auth-success' });
        navigate('/dashboard', { replace: true, state: { showWelcome: true } });
      })
      .catch(() => {
        toast.success('Signed in with Google!', { id: 'google-auth-success' });
        navigate('/dashboard', { replace: true, state: { showWelcome: true } });
      });
  }, [navigate, searchParams, setUser]);

  return (
    <div className={`min-h-screen flex items-center justify-center ${isDarkMode ? 'bg-gray-900 text-white' : 'bg-gray-50 text-gray-900'}`}>
      <p className="text-sm">Completing Google sign-in…</p>
    </div>
  );
};

export default GoogleAuthCallback;
