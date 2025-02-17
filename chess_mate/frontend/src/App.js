import React from 'react';
import { Toaster } from 'react-hot-toast';
import { ThemeProvider } from './context/ThemeContext';
import { UserProvider } from './contexts/UserContext';
import AppRoutes from './routes/AppRoutes';
import Navbar from './components/Navbar';
import './App.css';

function App() {
  return (
    <ThemeProvider>
      <UserProvider>
        <div className="min-h-screen flex flex-col">
          <Navbar />
          <main className="flex-1 pt-16">
            <AppRoutes />
          </main>
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
    </ThemeProvider>
  );
}

export default App;
