/**
 * Bottom-right ChessMate-style popups when achievements are newly completed.
 */

import { useCallback, useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Trophy, X } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useUser } from '../contexts/UserContext';
import { fetchProfileData } from '../services/apiRequests';

const SEEN_ACHIEVEMENTS_KEY = 'chessmate_seen_achievements';
const POPUP_DURATION_MS = 6000;

const loadSeenAchievements = () => {
  try {
    const raw = localStorage.getItem(SEEN_ACHIEVEMENTS_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
};

const saveSeenAchievements = (names) => {
  localStorage.setItem(SEEN_ACHIEVEMENTS_KEY, JSON.stringify(names));
};

const AchievementToast = () => {
  const { user } = useUser();
  const { isDarkMode } = useTheme();
  const location = useLocation();
  const [queue, setQueue] = useState([]);

  const dismissAchievement = useCallback((name) => {
    setQueue((prev) => prev.filter((item) => item.name !== name));
  }, []);

  const checkAchievements = useCallback(async () => {
    if (!user) {
      return;
    }

    try {
      const profile = await fetchProfileData();
      const achievements = Array.isArray(profile?.achievements) ? profile.achievements : [];
      const completed = achievements.filter((item) => item.completed);
      const seen = new Set(loadSeenAchievements());
      const newlyCompleted = completed.filter((item) => !seen.has(item.name));

      if (newlyCompleted.length > 0) {
        setQueue((prev) => {
          const existing = new Set(prev.map((item) => item.name));
          const additions = newlyCompleted
            .filter((item) => !existing.has(item.name))
            .map((item) => ({
              name: item.name,
              description: item.description || 'Keep playing to unlock more achievements.',
            }));
          return [...prev, ...additions];
        });
      }

      if (newlyCompleted.length > 0 || completed.length > 0) {
        saveSeenAchievements(completed.map((item) => item.name));
      }
    } catch {
      /* non-blocking */
    }
  }, [user]);

  useEffect(() => {
    checkAchievements();
  }, [checkAchievements, location.pathname]);

  useEffect(() => {
    if (queue.length === 0) {
      return undefined;
    }

    const timers = queue.map((item) =>
      window.setTimeout(() => dismissAchievement(item.name), POPUP_DURATION_MS)
    );

    return () => {
      timers.forEach((timerId) => window.clearTimeout(timerId));
    };
  }, [queue, dismissAchievement]);

  if (queue.length === 0) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 z-[60] flex flex-col gap-3 w-full max-w-sm px-4 sm:px-0 pointer-events-none">
      {queue.map((achievement) => (
        <div
          key={achievement.name}
          className="pointer-events-auto"
          role="status"
          aria-live="polite"
        >
          <div
            className={`rounded-2xl shadow-2xl border overflow-hidden ${
              isDarkMode ? 'bg-gray-800 border-amber-700/50' : 'bg-white border-amber-200'
            }`}
          >
            <div
              className={`px-4 py-3 flex items-start justify-between gap-3 ${
                isDarkMode ? 'bg-amber-950/60' : 'bg-amber-500'
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <Trophy
                  className={`h-5 w-5 shrink-0 ${
                    isDarkMode ? 'text-amber-300' : 'text-amber-50'
                  }`}
                />
                <div className="min-w-0">
                  <p
                    className={`text-sm font-semibold truncate ${
                      isDarkMode ? 'text-white' : 'text-white'
                    }`}
                  >
                    Achievement unlocked
                  </p>
                  <p
                    className={`text-xs mt-0.5 truncate ${
                      isDarkMode ? 'text-amber-200/90' : 'text-amber-50'
                    }`}
                  >
                    {achievement.name}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => dismissAchievement(achievement.name)}
                className={`p-1 rounded-md shrink-0 ${
                  isDarkMode
                    ? 'text-amber-200 hover:bg-amber-900/50'
                    : 'text-amber-50 hover:bg-amber-400'
                }`}
                aria-label={`Dismiss ${achievement.name} achievement`}
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="px-4 py-3">
              <p className={`text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
                {achievement.description}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default AchievementToast;
