import * as Sentry from "@sentry/react";
import { BrowserTracing } from "@sentry/tracing";
import { Replay } from "@sentry/replay";

export const initSentry = () => {
    Sentry.init({
        dsn: "https://3d7c7ff1a11b4807bad79ca77b1f7056@o4508725935276032.ingest.us.sentry.io/4508725939404800",
        integrations: [
            new BrowserTracing({
                // Reduce transaction sampling
                tracingOrigins: ['localhost', 'ec2-3-133-97-72.us-east-2.compute.amazonaws.com'],
                tracesSampleRate: 0.2
            }),
            new Replay({
                // Configure what events to capture
                maskAllText: true,
                blockAllMedia: true,
            }),
        ],
        // Reduce overall trace sample rate
        tracesSampleRate: 0.2,
        
        // Configure Replay sample rates directly in init options
        replaysSessionSampleRate: 0.1, // Reduce session capture rate
        replaysOnErrorSampleRate: 1.0, // Keep high error capture rate

        // Enable performance monitoring with reduced sampling
        enablePerformanceMonitoring: true,

        // Configure allowed domains for session replay
        allowUrls: [
            'ec2-3-133-97-72.us-east-2.compute.amazonaws.com',
            window.location.hostname
        ],

        // Configure what to ignore in session replay
        ignoreErrors: [
            'ResizeObserver loop limit exceeded',
            'Network request failed',
            /^Script error\.?$/,
            /^Javascript error: Script error\.? on line 0$/,
            // Add more common errors to ignore
            'Loading chunk failed',
            'Failed to fetch',
            'NetworkError',
            'AbortError',
            'ChunkLoadError'
        ],

        // Add additional context
        beforeSend(event) {
            // Don't send events from localhost
            if (window.location.hostname === 'localhost') {
                return null;
            }

            // Add environment info
            event.environment = process.env.NODE_ENV || 'production';

            return event;
        }
    });
};
