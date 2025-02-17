import React from 'react';
import { useTheme } from '../context/ThemeContext';

export const Loader = () => {
  const { isDarkMode } = useTheme();
  
  return (
    <div className="flex items-center justify-center">
      <div className={`animate-spin rounded-full h-8 w-8 border-b-2 ${
        isDarkMode ? 'border-primary-400' : 'border-primary-500'
      }`}></div>
    </div>
  );
};

export default Loader; 