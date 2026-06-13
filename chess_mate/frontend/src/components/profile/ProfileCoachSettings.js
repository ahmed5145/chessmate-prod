import React, { useEffect, useState } from 'react';
import { Settings } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { getUserProfile, updateUserProfile } from '../../services/apiRequests';

const DEFAULT_PREFERENCES = {
  wants_weekly_digest: false,
  wants_spaced_repetition_email: false,
  wants_reactivation_email: false,
  coach_persona: 'encouraging',
};

const ToggleRow = ({ label, description, checked, onChange, isDarkMode, ariaLabel }) => (
  <div className="flex items-center justify-between gap-4">
    <span className="flex min-w-0 flex-col">
      <span className={`text-sm font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
        {label}
      </span>
      {description ? (
        <span className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          {description}
        </span>
      ) : null}
    </span>
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel || label}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 ${
        checked ? 'bg-indigo-600' : isDarkMode ? 'bg-gray-600' : 'bg-gray-200'
      }`}
    >
      <span
        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ${
          checked ? 'translate-x-5' : 'translate-x-0'
        }`}
      />
    </button>
  </div>
);

const ProfileCoachSettings = ({ isDarkMode }) => {
  const [preferences, setPreferences] = useState(DEFAULT_PREFERENCES);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await getUserProfile();
        if (cancelled) {
          return;
        }
        setPreferences((prev) => ({
          ...prev,
          ...(data?.preferences || {}),
        }));
      } catch (error) {
        console.error('Error loading coach preferences:', error);
        if (!cancelled) {
          toast.error('Failed to load coach preferences');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const handlePreferenceChange = (key, value) => {
    setPreferences((prev) => ({
      ...prev,
      [key]: value !== undefined ? value : !prev[key],
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateUserProfile({ preferences });
      toast.success('Coach preferences saved');
    } catch (error) {
      console.error('Error saving coach preferences:', error);
      toast.error(error?.error || error?.detail || 'Failed to save preferences');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <section
        className={`mb-8 rounded-xl border p-6 ${
          isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
        } shadow-lg`}
        aria-label="Coach preferences"
      >
        <p className={isDarkMode ? 'text-gray-400' : 'text-gray-500'}>Loading coach preferences…</p>
      </section>
    );
  }

  return (
    <section
      className={`mb-8 rounded-xl border p-6 ${
        isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
      } shadow-lg`}
      aria-label="Coach preferences"
    >
      <div className="flex items-center gap-2 mb-1">
        <Settings className={`h-5 w-5 ${isDarkMode ? 'text-indigo-300' : 'text-indigo-600'}`} />
        <h2 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
          Coach preferences
        </h2>
      </div>
      <p className={`text-sm mb-6 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
        Email toggles default off. Coach tone applies to your next batch or single-game analysis.
      </p>

      <div className="space-y-5">
        <ToggleRow
          label="Weekly Coach Digest"
          description="One Tuesday summary email per week (inbox, streak, progress)"
          checked={Boolean(preferences.wants_weekly_digest)}
          onChange={(value) => handlePreferenceChange('wants_weekly_digest', value)}
          isDarkMode={isDarkMode}
          ariaLabel="Weekly Coach Digest"
        />
        <ToggleRow
          label="Spaced Moment Reminders"
          description="One gentle nudge per week about a critical moment (skipped when weekly digest sends)"
          checked={Boolean(preferences.wants_spaced_repetition_email)}
          onChange={(value) => handlePreferenceChange('wants_spaced_repetition_email', value)}
          isDarkMode={isDarkMode}
          ariaLabel="Spaced Moment Reminders"
        />
        <div className="flex items-center justify-between gap-4">
          <span className="flex min-w-0 flex-col">
            <span className={`text-sm font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Coach tone
            </span>
            <span className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              Direct = blunt and short; Encouraging = supportive
            </span>
          </span>
          <select
            aria-label="Coach tone"
            value={preferences.coach_persona || 'encouraging'}
            onChange={(event) => handlePreferenceChange('coach_persona', event.target.value)}
            className={`rounded-md border px-2 py-1 text-sm ${
              isDarkMode
                ? 'border-gray-600 bg-gray-700 text-white'
                : 'border-gray-300 bg-white text-gray-900'
            }`}
          >
            <option value="encouraging">Encouraging</option>
            <option value="direct">Direct</option>
          </select>
        </div>
        <ToggleRow
          label="Reactivation reminders"
          description="One email per 30 days if you have been inactive (opt-in)"
          checked={Boolean(preferences.wants_reactivation_email)}
          onChange={(value) => handlePreferenceChange('wants_reactivation_email', value)}
          isDarkMode={isDarkMode}
          ariaLabel="Reactivation reminders"
        />
      </div>

      <div className="mt-6 flex justify-end">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className={`inline-flex items-center rounded-lg px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors ${
            saving ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {saving ? 'Saving…' : 'Save preferences'}
        </button>
      </div>
    </section>
  );
};

export default ProfileCoachSettings;
