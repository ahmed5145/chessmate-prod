/**
 * Bottom-left toasts when achievements are newly completed.
 */

import { useCallback, useEffect } from 'react';
import { toast } from 'react-hot-toast';
import { useLocation } from 'react-router-dom';
import { useUser } from '../contexts/UserContext';
import { fetchProfileData } from '../services/apiRequests';

const SEEN_ACHIEVEMENTS_KEY = 'chessmate_seen_achievements';

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
  const location = useLocation();

  const checkAchievements = useCallback(async () => {
    if (!user) {
      return;
    }

    try {
      const profile = await fetchProfileData();
      const achievements = Array.isArray(profile?.achievements) ? profile.achievements : [];
      const completed = achievements.filter((item) => item.completed).map((item) => item.name);
      const seen = new Set(loadSeenAchievements());
      const newlyCompleted = completed.filter((name) => !seen.has(name));

      newlyCompleted.forEach((name) => {
        toast.success(`Achievement unlocked: ${name}`, {
          id: `achievement-${name}`,
          duration: 5000,
          position: 'bottom-left',
        });
      });

      if (newlyCompleted.length > 0 || completed.length > 0) {
        saveSeenAchievements(completed);
      }
    } catch {
      /* non-blocking */
    }
  }, [user]);

  useEffect(() => {
    checkAchievements();
  }, [checkAchievements, location.pathname]);

  return null;
};

export default AchievementToast;
