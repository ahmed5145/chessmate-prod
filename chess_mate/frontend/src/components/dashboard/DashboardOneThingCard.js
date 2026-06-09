import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Target } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { snoozeOneThingToday } from '../../utils/oneThingToday';
import { trackMarketingEvent } from '../../utils/marketingAnalytics';

const DashboardOneThingCard = ({ oneThing, onSnooze }) => {
  const { isDarkMode } = useTheme();
  const [hidden, setHidden] = useState(false);

  if (!oneThing || hidden) {
    return null;
  }

  const handleSnooze = () => {
    snoozeOneThingToday();
    trackMarketingEvent('one_thing_today_snooze', { source: oneThing.source });
    setHidden(true);
    if (typeof onSnooze === 'function') {
      onSnooze();
    }
  };

  return (
    <section
      className={`mb-8 rounded-xl border overflow-hidden ${
        isDarkMode
          ? 'bg-gradient-to-br from-indigo-950/50 to-gray-900 border-indigo-800/60'
          : 'bg-gradient-to-br from-indigo-50 to-white border-indigo-200'
      } shadow-lg`}
    >
      <div className={`flex items-center justify-between gap-3 px-5 py-4 border-b ${
        isDarkMode ? 'border-indigo-900/60' : 'border-indigo-100'
      }`}>
        <div className="flex items-center gap-2">
          <Target className={`h-5 w-5 ${isDarkMode ? 'text-indigo-300' : 'text-indigo-600'}`} />
          <h2 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            One thing today
          </h2>
        </div>
        <button
          type="button"
          onClick={handleSnooze}
          className={`text-xs font-medium ${
            isDarkMode ? 'text-indigo-300 hover:text-indigo-200' : 'text-indigo-600 hover:text-indigo-800'
          }`}
        >
          Snooze 24h
        </button>
      </div>

      <div className="px-5 py-4">
        <p className={`text-base font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
          {oneThing.headline}
        </p>
        {oneThing.subline ? (
          <p className={`mt-1 text-sm ${isDarkMode ? 'text-indigo-200/80' : 'text-indigo-800/80'}`}>
            {oneThing.subline}
          </p>
        ) : null}
        <Link
          to={oneThing.ctaTo}
          onClick={() => trackMarketingEvent('one_thing_today_click', { source: oneThing.source })}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors"
        >
          {oneThing.ctaLabel}
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </section>
  );
};

export default DashboardOneThingCard;
