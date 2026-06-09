import React, { useEffect, useState } from 'react';
import { Box, Button, IconButton, Paper, Typography } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import { trackMarketingEvent } from '../utils/marketingAnalytics';

const DISMISS_KEY = 'chessmate_pwa_install_dismissed_at';
const SNOOZE_MS = 30 * 24 * 60 * 60 * 1000;

export const isMobileInstallContext = () => {
  if (typeof window === 'undefined') {
    return false;
  }
  const coarsePointer = window.matchMedia?.('(pointer: coarse)')?.matches;
  const narrow = window.matchMedia?.('(max-width: 768px)')?.matches;
  const touch = (navigator.maxTouchPoints || 0) > 0;
  return Boolean((coarsePointer || narrow) && touch);
};

export const shouldShowPwaInstallPrompt = (batchesCompleted = 0) => {
  if (!isMobileInstallContext()) {
    return false;
  }
  if (Number(batchesCompleted) < 1) {
    return false;
  }
  const dismissedAt = localStorage.getItem(DISMISS_KEY);
  if (dismissedAt) {
    const ts = Date.parse(dismissedAt);
    if (!Number.isNaN(ts) && Date.now() - ts < SNOOZE_MS) {
      return false;
    }
  }
  return true;
};

const PwaInstallPrompt = ({ batchesCompleted = 0 }) => {
  const [visible, setVisible] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [isIOS, setIsIOS] = useState(false);

  useEffect(() => {
    setIsIOS(/iphone|ipad|ipod/i.test(navigator.userAgent));
    setVisible(shouldShowPwaInstallPrompt(batchesCompleted));

    const onBeforeInstall = (event) => {
      event.preventDefault();
      setDeferredPrompt(event);
    };
    window.addEventListener('beforeinstallprompt', onBeforeInstall);
    return () => window.removeEventListener('beforeinstallprompt', onBeforeInstall);
  }, [batchesCompleted]);

  useEffect(() => {
    if (visible) {
      trackMarketingEvent('pwa_install_prompt_shown', { batches_completed: batchesCompleted });
    }
  }, [visible, batchesCompleted]);

  const dismiss = (reason) => {
    localStorage.setItem(DISMISS_KEY, new Date().toISOString());
    setVisible(false);
    trackMarketingEvent('pwa_install_dismissed', { reason });
  };

  const handleInstall = async () => {
    if (!deferredPrompt) {
      return;
    }
    deferredPrompt.prompt();
    const choice = await deferredPrompt.userChoice;
    if (choice?.outcome === 'accepted') {
      trackMarketingEvent('pwa_install_accepted');
    } else {
      trackMarketingEvent('pwa_install_dismissed', { reason: 'native_decline' });
    }
    setDeferredPrompt(null);
    setVisible(false);
  };

  if (!visible) {
    return null;
  }

  return (
    <Paper
      elevation={4}
      sx={{
        position: 'fixed',
        bottom: { xs: 16, sm: 24 },
        left: { xs: 16, sm: 24 },
        right: { xs: 16, sm: 'auto' },
        zIndex: 1400,
        maxWidth: 420,
        p: 2,
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
        <Box sx={{ flex: 1 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
            Add ChessMate to your home screen
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {isIOS
              ? 'Tap Share, then “Add to Home Screen” for one-tap coach access.'
              : 'Install the app for faster return visits after batch coaching.'}
          </Typography>
          {!isIOS && deferredPrompt ? (
            <Button
              size="small"
              variant="contained"
              sx={{ mt: 1.5 }}
              onClick={handleInstall}
            >
              Add to home screen
            </Button>
          ) : null}
        </Box>
        <IconButton size="small" aria-label="Dismiss install prompt" onClick={() => dismiss('close')}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>
    </Paper>
  );
};

export default PwaInstallPrompt;
