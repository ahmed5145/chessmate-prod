# ChessMate Theme System Documentation

## Overview
ChessMate uses a robust theme system built with React Context and Tailwind CSS. The system supports both light and dark modes, with seamless transitions and system preference detection.

## Theme Implementation

### Core Components

1. **ThemeContext (`src/context/ThemeContext.js`)**
   - Manages the application's theme state
   - Provides theme toggling functionality
   - Persists theme preference in localStorage
   - Syncs with system color scheme preferences

2. **Tailwind Configuration (`tailwind.config.js`)**
   - Uses `darkMode: 'class'` for class-based dark mode switching
   - Defines custom color palette including chess-specific colors
   - Implements custom animations and transitions
   - Extends theme with chess-specific utilities

### Color Palette

```javascript
colors: {
  primary: {
    50: '#f0f9ff',
    100: '#e0f2fe',
    200: '#bae6fd',
    300: '#7dd3fc',
    400: '#38bdf8',
    500: '#0ea5e9',
    600: '#0284c7',
    700: '#0369a1',
    800: '#075985',
    900: '#0c4a6e',
  },
  chess: {
    light: '#f0d9b5',
    dark: '#b58863',
  }
}
```

### CSS Variables

The theme system uses CSS variables for dynamic values:

```css
:root {
  /* Light mode */
  --success-bg: #dcfce7;
  --success-color: #166534;
  --error-bg: #fee2e2;
  --error-color: #991b1b;
  --toast-bg: #ffffff;
  --toast-color: #1f2937;
}

.dark {
  /* Dark mode */
  --success-bg: #065f46;
  --success-color: #d1fae5;
  --error-bg: #7f1d1d;
  --error-color: #fecaca;
  --toast-bg: #1f2937;
  --toast-color: #f3f4f6;
}
```

## Usage

### Theme Hook

```javascript
import { useTheme } from '../context/ThemeContext';

const Component = () => {
  const { isDarkMode, toggleDarkMode } = useTheme();
  
  return (
    <div className={isDarkMode ? 'dark' : 'light'}>
      {/* Component content */}
    </div>
  );
};
```

### Conditional Styling

```javascript
// Using template literals
className={`p-4 rounded-xl ${
  isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
}`}

// Using Tailwind dark mode variant
className="bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
```

### Animations

The theme system includes smooth transitions for theme changes:

```css
/* Base transitions */
.transition-theme {
  transition: background-color 0.3s ease-in-out, color 0.3s ease-in-out;
}

/* Custom animations */
.animate-fade-in {
  animation: fadeIn 0.5s ease-out;
}
```

## Best Practices

1. **Component Theming**
   - Use Tailwind's dark mode variant (`dark:`) for simple color switches
   - Use the `useTheme` hook for complex conditional rendering
   - Maintain consistent color patterns across components

2. **Performance**
   - Theme changes are batched and optimized
   - CSS variables are used for frequently updated values
   - Transitions are disabled for users who prefer reduced motion

3. **Accessibility**
   - Color contrast ratios meet WCAG guidelines
   - Theme preferences respect system settings
   - Smooth transitions with `prefers-reduced-motion` support

## Theme Components

The following components are theme-aware and automatically adapt to theme changes:

- Navbar
- Dashboard cards and widgets
- Form elements
- Buttons and interactive elements
- Toast notifications
- Loading indicators
- Charts and visualizations

## Contributing

When adding new themed components:

1. Use existing color variables and classes when possible
2. Add dark mode variants for all visual elements
3. Test components in both light and dark modes
4. Ensure smooth transitions between themes
5. Maintain accessibility standards

## Testing

Theme-related tests should cover:

1. Theme persistence
2. System preference detection
3. Manual theme toggling
4. Component rendering in both themes
5. Transition animations
6. Accessibility compliance 