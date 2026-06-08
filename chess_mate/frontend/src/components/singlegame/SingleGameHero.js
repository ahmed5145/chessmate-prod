import React from 'react';
import { useTheme } from '../../context/ThemeContext';

const SingleGameHero = ({ coaching = {} }) => {
  const { isDarkMode } = useTheme();
  const takeaway = coaching.takeaway;
  const doToday = coaching.do_today;

  if (!takeaway && !doToday) {
    return null;
  }

  return (
    <div
      className={`mb-6 rounded-lg border p-4 ${
        isDarkMode ? 'bg-indigo-950/30 border-indigo-800/50' : 'bg-indigo-50 border-indigo-100'
      }`}
    >
      {takeaway ? (
        <p className={`text-base font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
          {takeaway}
        </p>
      ) : null}
      {doToday ? (
        <p className={`mt-2 text-sm ${isDarkMode ? 'text-indigo-200' : 'text-indigo-900'}`}>
          <span className="font-semibold">Do today:</span> {doToday}
        </p>
      ) : null}
    </div>
  );
};

export default SingleGameHero;
