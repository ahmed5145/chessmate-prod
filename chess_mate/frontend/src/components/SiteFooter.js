import React from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';
import { useSiteConfig } from '../hooks/useSiteConfig';

const SiteFooter = () => {
  const { isDarkMode } = useTheme();
  const { support_email, loading } = useSiteConfig();

  return (
    <footer
      className={`border-t ${
        isDarkMode ? 'border-gray-800 bg-gray-900 text-gray-400' : 'border-gray-200 bg-white text-gray-600'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm">
        <div className="flex items-center gap-2">
          <span className={`font-semibold ${isDarkMode ? 'text-gray-200' : 'text-gray-800'}`}>ChessMate</span>
          <span className={`px-2 py-0.5 rounded text-xs ${isDarkMode ? 'bg-indigo-900 text-indigo-200' : 'bg-indigo-100 text-indigo-700'}`}>
            Beta
          </span>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-4">
          {support_email ? (
            <a href={`mailto:${support_email}`} className="hover:underline">
              Support
            </a>
          ) : !loading ? (
            <span className="opacity-70">Support</span>
          ) : null}
          <Link to="/terms" className="hover:underline">
            Terms
          </Link>
          <Link to="/privacy" className="hover:underline">
            Privacy
          </Link>
        </div>
        <p className="text-xs text-center sm:text-right">
          © {new Date().getFullYear()} ChessMate
        </p>
      </div>
    </footer>
  );
};

export default SiteFooter;
