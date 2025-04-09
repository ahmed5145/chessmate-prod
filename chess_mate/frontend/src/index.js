import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { UserProvider } from './contexts/UserContext';
import { initSentry } from './utils/sentry';
import * as Sentry from "@sentry/react";
import App from './App';
import './index.css';

// Initialize Sentry
initSentry();

const root = ReactDOM.createRoot(document.getElementById('root'));

// Wrap App with Sentry error boundary
const SentryApp = () => (
    <Sentry.ErrorBoundary
        fallback={<div className="error-boundary">An error has occurred</div>}
        showDialog
    >
        <BrowserRouter
            future={{
                v7_startTransition: true,
                v7_relativeSplatPath: true
            }}
        >
            <ThemeProvider>
                <UserProvider>
                    <App />
                </UserProvider>
            </ThemeProvider>
        </BrowserRouter>
    </Sentry.ErrorBoundary>
);

root.render(<SentryApp />);
