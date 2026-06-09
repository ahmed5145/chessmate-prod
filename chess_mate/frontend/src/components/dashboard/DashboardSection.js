import React from 'react';
import { useTheme } from '../../context/ThemeContext';

const DashboardSection = ({ title, description, children, className = '' }) => {
  const { isDarkMode } = useTheme();
  const items = React.Children.toArray(children).filter(Boolean);

  if (items.length === 0) {
    return null;
  }

  return (
    <section className={`mb-10 ${className}`}>
      <header className="mb-4">
        <h2 className={`text-sm font-semibold uppercase tracking-wide ${
          isDarkMode ? 'text-indigo-300' : 'text-indigo-700'
        }`}
        >
          {title}
        </h2>
        {description ? (
          <p className={`mt-1 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            {description}
          </p>
        ) : null}
      </header>
      <div className="space-y-6 [&>section]:mb-0 [&>.MuiPaper-root]:mb-0">
        {children}
      </div>
    </section>
  );
};

export default DashboardSection;
