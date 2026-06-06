import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';
import api from '../services/api';

const DEFAULT_SUPPORT = 'support@chess-mate.online';

const SiteFooter = () => {
  const { isDarkMode } = useTheme();
  const [supportEmail, setSupportEmail] = useState(DEFAULT_SUPPORT);

  useEffect(() => {
    const load = async () => {
      try {
        const response = await api.get('/api/v1/public/site-config/');
        if (response.data?.support_email) {
          setSupportEmail(response.data.support_email);
        }
      } catch (error) {
        console.warn('Using default support email:', error);
      }
    };
    load();
  }, []);

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
          <a href={`mailto:${supportEmail}`} className="hover:underline">
            Support
          </a>
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
