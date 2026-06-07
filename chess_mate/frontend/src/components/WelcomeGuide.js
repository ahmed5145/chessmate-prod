import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { X, Coins, Download, Brain, BarChart3, Trophy } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useUser } from '../contexts/UserContext';
import api from '../services/api';
import { updateUserProfile } from '../services/apiRequests';

const getPreferences = (user) => user?.preferences || user?.profile?.preferences || {};

export const shouldShowWelcomeGuide = (user) => {
  const preferences = getPreferences(user);
  return preferences.welcome_guide_seen !== true;
};

const WelcomeGuide = () => {
  const { isDarkMode } = useTheme();
  const { user, setUser, refreshUserData } = useUser();
  const [visible, setVisible] = useState(false);
  const [signupBonusCredits, setSignupBonusCredits] = useState(15);
  const [dismissing, setDismissing] = useState(false);
  const [locallyDismissed, setLocallyDismissed] = useState(false);

  useEffect(() => {
    if (!user || locallyDismissed) {
      if (!user) {
        setVisible(false);
      }
      return;
    }
    setVisible(shouldShowWelcomeGuide(user));
  }, [user, locallyDismissed]);

  useEffect(() => {
    let cancelled = false;
    api.get('/api/v1/public/site-config/')
      .then((response) => {
        if (!cancelled && response.data?.signup_bonus_credits) {
          setSignupBonusCredits(response.data.signup_bonus_credits);
        }
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, []);

  const handleDismiss = async () => {
    if (dismissing) {
      return;
    }
    setDismissing(true);
    setLocallyDismissed(true);
    setVisible(false);

    if (setUser && user) {
      const currentPreferences = getPreferences(user);
      setUser({
        ...user,
        preferences: { ...currentPreferences, welcome_guide_seen: true },
      });
    }

    try {
      await updateUserProfile({ preferences: { welcome_guide_seen: true } });
      if (refreshUserData) {
        await refreshUserData();
      }
    } catch (error) {
      setLocallyDismissed(false);
      setVisible(true);
      toast.error('Could not save your preference. Please try again.');
    } finally {
      setDismissing(false);
    }
  };

  if (!visible) {
    return null;
  }

  const creditLabel = signupBonusCredits === 1 ? 'credit' : 'credits';

  return (
    <div
      className="fixed bottom-4 right-4 z-50 w-full max-w-md px-4 sm:px-0 sm:max-w-sm"
      role="dialog"
      aria-labelledby="welcome-guide-title"
      aria-describedby="welcome-guide-description"
    >
      <div
        className={`rounded-2xl shadow-2xl border overflow-hidden ${
          isDarkMode ? 'bg-gray-800 border-indigo-700/50' : 'bg-white border-indigo-200'
        }`}
      >
        <div className={`px-4 py-3 flex items-start justify-between gap-3 ${
          isDarkMode ? 'bg-indigo-950/60' : 'bg-indigo-600'
        }`}>
          <div className="flex items-center gap-2 min-w-0">
            <Trophy className={`h-5 w-5 shrink-0 ${isDarkMode ? 'text-indigo-300' : 'text-indigo-100'}`} />
            <div>
              <h2
                id="welcome-guide-title"
                className={`text-sm font-semibold ${isDarkMode ? 'text-white' : 'text-white'}`}
              >
                Welcome to ChessMate
              </h2>
              <p className={`text-xs mt-0.5 ${isDarkMode ? 'text-indigo-200/90' : 'text-indigo-100'}`}>
                {signupBonusCredits} free {creditLabel} to get started
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleDismiss}
            disabled={dismissing}
            className={`p-1 rounded-md shrink-0 ${
              isDarkMode ? 'text-indigo-200 hover:bg-indigo-900/50' : 'text-indigo-100 hover:bg-indigo-500'
            }`}
            aria-label="Dismiss welcome guide"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-4 py-4">
          <p
            id="welcome-guide-description"
            className={`text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}
          >
            You have <strong className={isDarkMode ? 'text-white' : 'text-gray-900'}>{signupBonusCredits} {creditLabel}</strong>{' '}
            on us. Each credit covers one imported game analysis, or use several for a Batch Coach report.
          </p>

          <ul className={`mt-4 space-y-2 text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            <li className="flex items-start gap-2">
              <Download className={`h-4 w-4 mt-0.5 shrink-0 ${isDarkMode ? 'text-indigo-400' : 'text-indigo-600'}`} />
              <span><strong>Import games</strong> from Chess.com or Lichess</span>
            </li>
            <li className="flex items-start gap-2">
              <BarChart3 className={`h-4 w-4 mt-0.5 shrink-0 ${isDarkMode ? 'text-indigo-400' : 'text-indigo-600'}`} />
              <span><strong>Analyze a game</strong> for accuracy, mistakes, and engine lines</span>
            </li>
            <li className="flex items-start gap-2">
              <Brain className={`h-4 w-4 mt-0.5 shrink-0 ${isDarkMode ? 'text-indigo-400' : 'text-indigo-600'}`} />
              <span><strong>Batch Coach</strong> finds patterns across 5–30 games</span>
            </li>
            <li className="flex items-start gap-2">
              <Coins className={`h-4 w-4 mt-0.5 shrink-0 ${isDarkMode ? 'text-indigo-400' : 'text-indigo-600'}`} />
              <span>Check your balance anytime under <strong>Credits</strong></span>
            </li>
          </ul>

          <div className="mt-4 flex flex-col sm:flex-row gap-2">
            <Link
              to="/fetch-games"
              onClick={handleDismiss}
              className="flex-1 text-center text-sm font-medium px-3 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition-colors"
            >
              Import games
            </Link>
            <Link
              to="/batch-analysis"
              onClick={handleDismiss}
              className={`flex-1 text-center text-sm font-medium px-3 py-2 rounded-lg border transition-colors ${
                isDarkMode
                  ? 'border-gray-600 text-gray-200 hover:bg-gray-700'
                  : 'border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              Try Batch Coach
            </Link>
          </div>

          <button
            type="button"
            onClick={handleDismiss}
            disabled={dismissing}
            className={`mt-3 w-full text-xs ${isDarkMode ? 'text-gray-500 hover:text-gray-400' : 'text-gray-500 hover:text-gray-600'}`}
          >
            Got it, don&apos;t show again
          </button>
        </div>
      </div>
    </div>
  );
};

export default WelcomeGuide;
