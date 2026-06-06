import React from 'react';
import { Toaster } from 'react-hot-toast';
import { ThemeProvider as TailwindThemeProvider, useTheme } from './context/ThemeContext';
import { ThemeProvider as MuiThemeProvider, createTheme } from '@mui/material/styles';
import { UserProvider } from './contexts/UserContext';
import AppRoutes from './routes/AppRoutes';
import Navbar from './components/Navbar';
import SiteFooter from './components/SiteFooter';
import './App.css';

// Inner component that uses Tailwind theme context and provides MUI theme
function AppContent() {
  const { isDarkMode } = useTheme();

  // Create MUI theme based on Tailwind dark mode state
  const muiTheme = createTheme({
    palette: {
      mode: isDarkMode ? 'dark' : 'light',
    },
  });

  return (
    <MuiThemeProvider theme={muiTheme}>
      <UserProvider>
        <div className="min-h-screen flex flex-col">
          <Navbar />
          <main className="flex-1 pt-16">
            <AppRoutes />
          </main>
          <SiteFooter />
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
      </UserProvider>
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
