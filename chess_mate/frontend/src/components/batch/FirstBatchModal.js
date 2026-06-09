import React, { useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Typography,
} from '@mui/material';
import { updateUserProfile } from '../../services/apiRequests';
import { trackMarketingEvent } from '../../utils/marketingAnalytics';

const prefersReducedMotion = () => (
  typeof window !== 'undefined'
  && window.matchMedia
  && window.matchMedia('(prefers-reduced-motion: reduce)').matches
);

const ConfettiBurst = () => {
  if (prefersReducedMotion()) {
    return null;
  }

  const pieces = Array.from({ length: 18 }, (_, index) => ({
    id: index,
    left: `${(index * 5.5) % 100}%`,
    delay: `${(index % 6) * 0.08}s`,
    color: ['#4f46e5', '#22c55e', '#f59e0b', '#ec4899'][index % 4],
  }));

  return (
    <Box
      aria-hidden
      sx={{
        pointerEvents: 'none',
        position: 'absolute',
        inset: 0,
        overflow: 'hidden',
      }}
    >
      {pieces.map((piece) => (
        <Box
          key={piece.id}
          sx={{
            position: 'absolute',
            top: -8,
            left: piece.left,
            width: 8,
            height: 14,
            bgcolor: piece.color,
            borderRadius: '2px',
            animation: `firstBatchConfetti 1.4s ease-out ${piece.delay} forwards`,
            '@keyframes firstBatchConfetti': {
              '0%': { transform: 'translateY(0) rotate(0deg)', opacity: 1 },
              '100%': { transform: 'translateY(220px) rotate(280deg)', opacity: 0 },
            },
          }}
        />
      ))}
    </Box>
  );
};

const FirstBatchModal = ({
  open,
  celebration = {},
  onDismiss,
  onCelebrationComplete,
  referralLink = null,
}) => {
  const [dismissing, setDismissing] = useState(false);

  useEffect(() => {
    if (open) {
      trackMarketingEvent('first_batch_celebration_shown', {
        batch_id: celebration.batch_id,
      });
    }
  }, [open, celebration.batch_id]);

  const handleDismiss = async () => {
    if (dismissing) {
      return;
    }
    setDismissing(true);
    try {
      await updateUserProfile({
        preferences: { first_batch_celebrated_at: new Date().toISOString() },
      });
      trackMarketingEvent('first_batch_celebration_dismissed', {
        batch_id: celebration.batch_id,
      });
      onDismiss?.();
      onCelebrationComplete?.();
    } finally {
      setDismissing(false);
    }
  };

  const handleCtaClick = () => {
    trackMarketingEvent('first_batch_celebration_cta', {
      batch_id: celebration.batch_id,
    });
    handleDismiss();
  };

  if (!open || !celebration?.show) {
    return null;
  }

  return (
    <Dialog
      open={open}
      onClose={handleDismiss}
      maxWidth="sm"
      fullWidth
      PaperProps={{ sx: { position: 'relative', overflow: 'hidden' } }}
    >
      <ConfettiBurst />
      <DialogTitle sx={{ fontWeight: 800, pr: 4 }}>
        Your first Batch Coach report is ready
      </DialogTitle>
      <DialogContent>
        <Typography variant="body1" sx={{ mb: 2 }}>
          {celebration.headline}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Your coach picked proof games and priorities — start with #1 for the fastest improvement loop.
        </Typography>
        {referralLink ? (
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2 }}>
            Know a chess friend? Share your invite link from Credits after you review priority #1.
          </Typography>
        ) : null}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2, flexWrap: 'wrap', gap: 1 }}>
        <Button onClick={handleDismiss} disabled={dismissing}>
          Browse report
        </Button>
        <Button
          variant="contained"
          component={RouterLink}
          to={celebration.cta_href || '/dashboard'}
          onClick={handleCtaClick}
          disabled={dismissing}
        >
          {celebration.cta_label || 'Review your #1 priority'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default FirstBatchModal;
