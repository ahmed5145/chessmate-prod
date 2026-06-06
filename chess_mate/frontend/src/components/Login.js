import React, { useState, useEffect, useRef } from "react";
import { useNavigate, Link, useSearchParams, useLocation } from "react-router-dom";
import { loginUser, resendVerificationEmail } from "../services/apiRequests";
import { KeyRound, Mail } from "lucide-react";
import { toast } from "react-hot-toast";
import { useTheme } from "../context/ThemeContext";
import { useUser } from '../contexts/UserContext';
import { extractApiError } from '../utils/apiErrors';

const Login = () => {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState(location.state?.email || "");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [showUnverifiedHelp, setShowUnverifiedHelp] = useState(false);
  const navigate = useNavigate();
  const { isDarkMode } = useTheme();
  const { setUser } = useUser();

  const verifiedToastShown = useRef(false);

  useEffect(() => {
    const verified = searchParams.get('verified');
    if (!verified || verifiedToastShown.current) {
      return;
    }

    if (verified === 'success') {
      verifiedToastShown.current = true;
      toast.success('Email verified! You can sign in now.', { id: 'email-verified' });
    } else if (verified === 'already') {
      verifiedToastShown.current = true;
      toast.success('Your email is already verified. You can sign in.', { id: 'email-verified' });
    }

    if (verified === 'success' || verified === 'already') {
      // Cosmetic query param only — strip it so the URL cannot be mistaken for proof of verification.
      navigate('/login', { replace: true, state: location.state });
    }
  }, [searchParams, navigate, location.state]);

  const handleResendVerification = async () => {
    if (!email || resending) {
      return;
    }
    setResending(true);
    try {
      const result = await resendVerificationEmail(email);
      toast.success(
        result.message || 'If an unverified account exists, a new verification link has been sent.',
        { id: 'login-resend-verification' }
      );
    } catch (error) {
      toast.error(extractApiError(error, 'Could not resend verification email.'), {
        id: 'login-resend-verification-error',
      });
    } finally {
      setResending(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) {
      return;
    }
    setLoading(true);

    try {
      const result = await loginUser(email, password);

      if (result.success) {
        setUser(result.user);
        toast.success("Login successful!", { id: "login-success" });
        navigate('/dashboard', { state: { showWelcome: true } });
      } else {
        setLoading(false);
      }
    } catch (error) {
      const message = extractApiError(error, 'An unexpected error occurred. Please try again.');
      const isUnverified = /not verified/i.test(message);
      setShowUnverifiedHelp(isUnverified);
      toast.error(message, { id: 'login-error' });
      setLoading(false);
    }
  };

  return (
    <div className={`min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <h2 className={`mt-6 text-center text-3xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
          Sign in to your account
        </h2>
        <p className={`mt-2 text-center text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          Don't have an account?{" "}
          <Link
            to="/register"
            className={`font-medium ${isDarkMode ? 'text-indigo-400 hover:text-indigo-300' : 'text-indigo-600 hover:text-indigo-500'} focus:outline-none focus:underline transition ease-in-out duration-150`}
          >
            Register here
          </Link>
        </p>
      </div>

      <div className={`mt-8 sm:mx-auto sm:w-full sm:max-w-md ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
        <div className={`py-8 px-4 shadow sm:rounded-lg sm:px-10 ${isDarkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'}`}>
          <form onSubmit={handleSubmit} className={`space-y-6 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            <div className={`${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              <label htmlFor="email" className={`block text-sm font-medium ${isDarkMode ? 'text-gray-200' : 'text-gray-700'}`}>
                Email address
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className={`h-5 w-5 ${isDarkMode ? 'text-gray-400' : 'text-gray-400'}`} />
                </div>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  className={`block w-full pl-10 sm:text-sm rounded-md border ${
                    isDarkMode
                      ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400 focus:ring-indigo-500 focus:border-indigo-500'
                      : 'bg-white border-gray-300 placeholder-gray-400 focus:ring-indigo-500 focus:border-indigo-500'
                  }`}
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className={`block text-sm font-medium ${isDarkMode ? 'text-gray-200' : 'text-gray-700'}`}>
                Password
              </label>
              <div className="mt-1 relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <KeyRound className={`h-5 w-5 ${isDarkMode ? 'text-gray-400' : 'text-gray-400'}`} />
                </div>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  className={`block w-full pl-10 sm:text-sm rounded-md border ${
                    isDarkMode
                      ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400 focus:ring-indigo-500 focus:border-indigo-500'
                      : 'bg-white border-gray-300 placeholder-gray-400 focus:ring-indigo-500 focus:border-indigo-500'
                  }`}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="text-sm">
                <Link
                  to="/forgot-password"
                  className={`font-medium ${isDarkMode ? 'text-indigo-400 hover:text-indigo-300' : 'text-indigo-600 hover:text-indigo-500'}`}
                >
                  Forgot your password?
                </Link>
              </div>
            </div>

            {showUnverifiedHelp && (
              <div className={`rounded-md p-4 text-sm ${isDarkMode ? 'bg-amber-900/30 text-amber-200' : 'bg-amber-50 text-amber-800'}`}>
                <p>Your email is not verified yet. Check your inbox for the verification link, or resend it below.</p>
                <button
                  type="button"
                  onClick={handleResendVerification}
                  disabled={resending || !email}
                  className={`mt-2 font-medium underline ${resending ? 'opacity-60 cursor-not-allowed' : ''}`}
                >
                  {resending ? 'Sending...' : 'Resend verification email'}
                </button>
              </div>
            )}

            <div>
              <button
                type="submit"
                disabled={loading}
                className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${
                  loading
                    ? 'bg-indigo-400 cursor-not-allowed'
                    : 'bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500'
                }`}
              >
                {loading ? 'Signing in...' : 'Sign in'}
              </button>
            </div>
          </form>

          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className={`w-full border-t ${isDarkMode ? 'border-gray-600' : 'border-gray-300'}`} />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className={`px-2 ${isDarkMode ? 'bg-gray-800 text-gray-400' : 'bg-white text-gray-500'}`}>
                  Or
                </span>
              </div>
            </div>

            <div className="mt-6">
              <Link
                to="/register"
                className={`w-full flex justify-center py-2 px-4 border rounded-md shadow-sm text-sm font-medium ${
                  isDarkMode
                    ? 'border-gray-600 text-white hover:bg-gray-700'
                    : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                }`}
              >
                Create new account
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
