import React, { useEffect, useMemo, useState } from 'react';
import { Settings } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { getUserProfile, updateUserProfile } from '../../services/apiRequests';

const DEFAULT_PREFERENCES = {
  wants_weekly_digest: false,
  wants_spaced_repetition_email: false,
  wants_reactivation_email: false,
  coach_persona: 'encouraging',
};

const COACH_PREF_KEYS = [
  'wants_weekly_digest',
  'wants_spaced_repetition_email',
  'wants_reactivation_email',
  'coach_persona',
];

const pickCoachPrefs = (prefs = {}) => {
  const source = prefs || {};
  return COACH_PREF_KEYS.reduce((acc, key) => {
    acc[key] = source[key] ?? DEFAULT_PREFERENCES[key];
    return acc;
  }, {});
};

const prefsEqual = (left, right) => (
  COACH_PREF_KEYS.every((key) => left[key] === right[key])
);

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

const ToneSelector = ({ value, onChange, isDarkMode }) => {
  const options = [
    { id: 'encouraging', label: 'Encouraging' },
    { id: 'direct', label: 'Direct' },
  ];

  return (
    <div
      role="group"
      aria-label="Coach tone"
      className={`inline-flex shrink-0 rounded-lg border p-0.5 ${
        isDarkMode ? 'border-gray-600 bg-gray-900/60' : 'border-gray-200 bg-gray-100'
      }`}
    >
      {options.map((option) => {
        const selected = value === option.id;
        return (
          <button
            key={option.id}
            type="button"
            aria-pressed={selected}
            onClick={() => onChange(option.id)}
            className={`rounded-md px-3 py-1.5 text-sm font-semibold transition-colors ${
              selected
                ? (isDarkMode
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-white text-indigo-700 shadow-sm')
                : (isDarkMode
                  ? 'text-gray-300 hover:text-white'
                  : 'text-gray-600 hover:text-gray-900')
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
};

const ProfileCoachSettings = ({ isDarkMode }) => {
  const [preferences, setPreferences] = useState(DEFAULT_PREFERENCES);
  const [savedPreferences, setSavedPreferences] = useState(DEFAULT_PREFERENCES);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const isDirty = useMemo(
    () => !prefsEqual(preferences, savedPreferences),
    [preferences, savedPreferences]
  );

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await getUserProfile();
        if (cancelled) {
          return;
        }
        const loaded = pickCoachPrefs(data?.preferences);
        setPreferences(loaded);
        setSavedPreferences(loaded);
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
    if (!isDirty || saving) {
      return;
    }
    setSaving(true);
    try {
      const response = await updateUserProfile({ preferences });
      const merged = pickCoachPrefs(response?.preferences || preferences);
      setPreferences(merged);
      setSavedPreferences(merged);
      toast.success('Coach preferences saved');
    } catch (error) {
      console.error('Error saving coach preferences:', error);
      const retryAfter = error?.retry_after;
      if (error?.code === 'PROFILE_001' || retryAfter) {
        toast.error(
          error?.message
          || `Too many updates. Try again in ${retryAfter || 'a few'} seconds.`
        );
      } else {
        toast.error(error?.error || error?.detail || 'Failed to save preferences');
      }
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
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <span className="flex min-w-0 flex-col">
            <span className={`text-sm font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Coach tone
            </span>
            <span className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              Direct = blunt and short; Encouraging = supportive
            </span>
          </span>
          <ToneSelector
            value={preferences.coach_persona || 'encouraging'}
            onChange={(value) => handlePreferenceChange('coach_persona', value)}
            isDarkMode={isDarkMode}
          />
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

      <div className="mt-6 flex flex-wrap items-center justify-end gap-3">
        {isDirty ? (
          <span className={`text-xs ${isDarkMode ? 'text-amber-300' : 'text-amber-700'}`}>
            Unsaved changes
          </span>
        ) : null}
        <button
          type="button"
          onClick={handleSave}
          disabled={!isDirty || saving}
          className={`inline-flex items-center rounded-lg px-4 py-2 text-sm font-semibold text-white transition-colors ${
            !isDirty || saving
              ? 'bg-indigo-400 cursor-not-allowed opacity-70'
              : 'bg-indigo-600 hover:bg-indigo-700'
          }`}
        >
          {saving ? 'Saving…' : 'Save preferences'}
        </button>
      </div>
    </section>
  );
};

export default ProfileCoachSettings;
