import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Mail, ArrowLeft } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { useTheme } from '../context/ThemeContext';
import { resendVerificationEmail } from '../services/apiRequests';
import { extractApiError } from '../utils/apiErrors';

const VerifyEmailSent = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { isDarkMode } = useTheme();
  const [resending, setResending] = useState(false);

  const email = location.state?.email || '';
  const emailSent = location.state?.emailSent !== false;

  const handleResend = async () => {
    if (!email || resending) {
      return;
    }
    setResending(true);
    try {
      const result = await resendVerificationEmail(email);
      toast.success(
        result.message || 'If an unverified account exists, a new verification link has been sent.',
        { id: 'resend-verification' }
      );
    } catch (error) {
      toast.error(extractApiError(error, 'Could not resend verification email.'), {
        id: 'resend-verification-error',
      });
    } finally {
      setResending(false);
    }
  };

  if (!email) {
    return (
      <div className={`min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
        <div className="sm:mx-auto sm:w-full sm:max-w-md text-center px-4">
          <p className={isDarkMode ? 'text-gray-300' : 'text-gray-600'}>
            No email address on file. Please register or sign in.
          </p>
          <Link
            to="/register"
            className={`mt-4 inline-block font-medium ${isDarkMode ? 'text-indigo-400' : 'text-indigo-600'}`}
          >
            Create an account
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className={`py-8 px-4 shadow sm:rounded-lg sm:px-10 ${isDarkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'}`}>
          <div className="flex justify-center mb-4">
            <div className={`p-3 rounded-full ${isDarkMode ? 'bg-indigo-900/50' : 'bg-indigo-100'}`}>
              <Mail className={`h-8 w-8 ${isDarkMode ? 'text-indigo-400' : 'text-indigo-600'}`} />
            </div>
          </div>

          <h2 className={`text-center text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Check your inbox
          </h2>

          <p className={`mt-4 text-center text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            We sent a verification link to{' '}
            <span className={`font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>{email}</span>.
            Click the link in that email to activate your account, then sign in.
          </p>

          {!emailSent && (
            <p className={`mt-4 text-center text-sm ${isDarkMode ? 'text-amber-300' : 'text-amber-700'}`}>
              We could not send the email right now. Use the button below to try again, or contact support if the problem continues.
            </p>
          )}

          <div className="mt-6 space-y-3">
            <button
              type="button"
              onClick={handleResend}
              disabled={resending}
              className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${
                resending
                  ? 'bg-indigo-400 cursor-not-allowed'
                  : 'bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500'
              }`}
            >
              {resending ? 'Sending...' : 'Resend verification email'}
            </button>

            <button
              type="button"
              onClick={() => navigate('/login', { state: { email } })}
              className={`w-full flex justify-center items-center gap-2 py-2 px-4 border rounded-md shadow-sm text-sm font-medium ${
                isDarkMode
                  ? 'border-gray-600 text-white hover:bg-gray-700'
                  : 'border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              <ArrowLeft className="h-4 w-4" />
              Back to sign in
            </button>
          </div>

          <p className={`mt-6 text-center text-xs ${isDarkMode ? 'text-gray-500' : 'text-gray-500'}`}>
            Did not receive it? Check your spam folder. The link expires in 7 days.
          </p>
        </div>
      </div>
    </div>
  );
};

export default VerifyEmailSent;
