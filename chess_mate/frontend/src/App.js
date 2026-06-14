import React, { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { initMarketingAnalytics, trackPageView } from './utils/marketingAnalytics';
import { Toaster } from 'react-hot-toast';
import { ThemeProvider as TailwindThemeProvider, useTheme } from './context/ThemeContext';
import { ThemeProvider as MuiThemeProvider, createTheme } from '@mui/material/styles';
import AppRoutes from './routes/AppRoutes';
import Navbar from './components/Navbar';
import SiteFooter from './components/SiteFooter';
import AchievementToast from './components/AchievementToast';
import './App.css';

// Inner component that uses Tailwind theme context and provides MUI theme
function AppContent() {
  const location = useLocation();
  const { isDarkMode } = useTheme();

  useEffect(() => {
    initMarketingAnalytics();
  }, []);

  useEffect(() => {
    trackPageView(`${location.pathname}${location.search}`);
  }, [location]);

  // Create MUI theme based on Tailwind dark mode state
  const muiTheme = createTheme({
    palette: {
      mode: isDarkMode ? 'dark' : 'light',
    },
  });

  return (
    <MuiThemeProvider theme={muiTheme}>
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1 pt-16">
          <AppRoutes key={`${location.pathname}${location.key}`} />
        </main>
        <SiteFooter />
        <AchievementToast />
        <Toaster
          position="top-right"
          toastOptions={{
            success: {
              style: {
                background: 'var(--success-bg)',
                color: 'var(--success-color)',
              },
            },
            error: {
              style: {
                background: 'var(--error-bg)',
                color: 'var(--error-color)',
              },
            },
          }}
        />
      </div>
    </MuiThemeProvider>
  );
}

function App() {
  return (
    <TailwindThemeProvider>
      <AppContent />
    </TailwindThemeProvider>
  );
}

export default App;
