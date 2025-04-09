/**
 * Theme utility functions for ChessMate
 */

/**
 * Get conditional class names based on theme
 * @param {boolean} isDarkMode - Current theme state
 * @param {string} lightClass - Class names for light mode
 * @param {string} darkClass - Class names for dark mode
 * @returns {string} Combined class names
 */
export const getThemeClasses = (isDarkMode, lightClass, darkClass) => {
  return isDarkMode ? darkClass : lightClass;
};

/**
 * Get theme-aware color for a specific component type
 * @param {boolean} isDarkMode - Current theme state
 * @param {string} type - Component type (primary, secondary, success, error, etc.)
 * @returns {string} Color class name
 */
export const getThemeColor = (isDarkMode, type = 'primary') => {
  const colors = {
    primary: {
      light: 'text-primary-600 bg-primary-50',
      dark: 'text-primary-400 bg-primary-900/30'
    },
    secondary: {
      light: 'text-gray-600 bg-gray-100',
      dark: 'text-gray-300 bg-gray-800'
    },
    success: {
      light: 'text-green-600 bg-green-50',
      dark: 'text-green-400 bg-green-900/30'
    },
    error: {
      light: 'text-red-600 bg-red-50',
      dark: 'text-red-400 bg-red-900/30'
    },
    warning: {
      light: 'text-yellow-600 bg-yellow-50',
      dark: 'text-yellow-400 bg-yellow-900/30'
    },
    info: {
      light: 'text-blue-600 bg-blue-50',
      dark: 'text-blue-400 bg-blue-900/30'
    }
  };

  return isDarkMode ? colors[type].dark : colors[type].light;
};

/**
 * Get theme-aware border classes
 * @param {boolean} isDarkMode - Current theme state
 * @param {string} type - Border type (default, primary, etc.)
 * @returns {string} Border class names
 */
export const getThemeBorder = (isDarkMode, type = 'default') => {
  const borders = {
    default: {
      light: 'border-gray-200',
      dark: 'border-gray-700'
    },
    primary: {
      light: 'border-primary-200',
      dark: 'border-primary-700'
    }
  };

  return isDarkMode ? borders[type].dark : borders[type].light;
};

/**
 * Get theme-aware shadow classes
 * @param {boolean} isDarkMode - Current theme state
 * @param {string} size - Shadow size (sm, md, lg, xl)
 * @returns {string} Shadow class names
 */
export const getThemeShadow = (isDarkMode, size = 'md') => {
  const base = isDarkMode ? 'shadow-gray-900/50' : 'shadow-gray-200/50';
  const sizes = {
    sm: 'shadow-sm',
    md: 'shadow',
    lg: 'shadow-lg',
    xl: 'shadow-xl'
  };

  return `${sizes[size]} ${base}`;
};

/**
 * Get theme-aware text classes
 * @param {boolean} isDarkMode - Current theme state
 * @param {string} type - Text type (primary, secondary, etc.)
 * @returns {string} Text class names
 */
export const getThemeText = (isDarkMode, type = 'primary') => {
  const text = {
    primary: {
      light: 'text-gray-900',
      dark: 'text-white'
    },
    secondary: {
      light: 'text-gray-600',
      dark: 'text-gray-300'
    },
    muted: {
      light: 'text-gray-500',
      dark: 'text-gray-400'
    }
  };

  return isDarkMode ? text[type].dark : text[type].light;
};

/**
 * Get theme-aware background classes
 * @param {boolean} isDarkMode - Current theme state
 * @param {string} type - Background type (primary, secondary, etc.)
 * @returns {string} Background class names
 */
export const getThemeBackground = (isDarkMode, type = 'primary') => {
  const backgrounds = {
    primary: {
      light: 'bg-white',
      dark: 'bg-gray-800'
    },
    secondary: {
      light: 'bg-gray-50',
      dark: 'bg-gray-900'
    },
    elevated: {
      light: 'bg-white shadow-lg',
      dark: 'bg-gray-800 shadow-lg shadow-gray-900/50'
    }
  };

  return isDarkMode ? backgrounds[type].dark : backgrounds[type].light;
};

/**
 * Get theme-aware hover classes
 * @param {boolean} isDarkMode - Current theme state
 * @param {string} type - Hover type (primary, secondary, etc.)
 * @returns {string} Hover class names
 */
export const getThemeHover = (isDarkMode, type = 'primary') => {
  const hover = {
    primary: {
      light: 'hover:bg-gray-50',
      dark: 'hover:bg-gray-700'
    },
    secondary: {
      light: 'hover:bg-gray-100',
      dark: 'hover:bg-gray-600'
    },
    highlight: {
      light: 'hover:bg-primary-50',
      dark: 'hover:bg-primary-900/30'
    }
  };

  return isDarkMode ? hover[type].dark : hover[type].light;
};
