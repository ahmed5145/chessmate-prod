import React, { useEffect, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Container,
  Paper,
  Typography,
} from '@mui/material';
import BatchReportSections from '../batch/BatchReportSections';
import { getDemoBatchReport } from '../../content/demoBatchReport';
import { buildRegisterHref, MARKETING_SOURCES } from '../../utils/marketingLinks';
import { trackMarketingEvent } from '../../utils/marketingAnalytics';
import api from '../../services/api';

const ExampleBatchReportPage = () => {
  const [signupBonus, setSignupBonus] = useState(15);
  const batchReport = getDemoBatchReport();

  useEffect(() => {
    trackMarketingEvent('full_example_page_view', { source: MARKETING_SOURCES.EXAMPLE_PAGE });

    let cancelled = false;
    const configRequest = api.get?.('/api/v1/public/site-config/');
    if (!configRequest?.then) {
      return undefined;
    }
    configRequest
      .then((response) => {
        if (!cancelled && response.data?.signup_bonus_credits) {
          setSignupBonus(response.data.signup_bonus_credits);
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const creditLabel = signupBonus === 1 ? 'credit' : 'credits';
  const registerHref = buildRegisterHref(MARKETING_SOURCES.EXAMPLE_PAGE);

  return (
    <Box
      className="batch-report-page"
      sx={{ minHeight: '100vh', py: 4, bgcolor: 'background.default', width: '100%', maxWidth: '100%', overflowX: 'clip' }}
    >
      <Container maxWidth="lg">
        <Paper
          className="batch-report-no-print"
          elevation={0}
          sx={(theme) => ({
            p: { xs: 2, sm: 2.5 },
            mb: 3,
            borderRadius: 2,
            border: '1px solid',
            borderColor: theme.palette.mode === 'dark' ? 'rgba(99, 102, 241, 0.35)' : 'rgba(99, 102, 241, 0.25)',
            background:
              theme.palette.mode === 'dark'
                ? 'linear-gradient(135deg, #1e1b4b 0%, #312e81 45%, #1f2937 100%)'
                : 'linear-gradient(135deg, #eef2ff 0%, #ffffff 55%, #f8fafc 100%)',
          })}
        >
          <Typography variant="overline" sx={{ color: 'primary.main', letterSpacing: 1.2 }}>
            Example Batch Coach report
          </Typography>
          <Typography variant="h5" sx={{ fontWeight: 800, mt: 0.5, mb: 1 }}>
            See what you get after analyzing 8 games
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: 720 }}>
            This is a read-only demo with anonymized players. Sign up to run Batch Coach on your own
            Chess.com or Lichess games — priorities, opening gaps, drills, and a training plan.
          </Typography>
          <Alert severity="info" sx={{ mb: 2 }}>
            Example only · anonymized games · your real report stays private unless you share it
          </Alert>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            <Button
              component={RouterLink}
              to={registerHref}
              variant="contained"
              onClick={() => trackMarketingEvent('cta_click', {
                location: 'example_page_header',
                source: MARKETING_SOURCES.EXAMPLE_PAGE,
              })}
              sx={{ bgcolor: '#4f46e5', textTransform: 'none', fontWeight: 600, '&:hover': { bgcolor: '#4338ca' } }}
            >
              Get your own report — {signupBonus} free {creditLabel}
            </Button>
            <Button
              component={RouterLink}
              to="/"
              variant="outlined"
              sx={{ textTransform: 'none', fontWeight: 600 }}
            >
              Back to home
            </Button>
          </Box>
        </Paper>

        <BatchReportSections
          batchReport={batchReport}
          status={batchReport.status}
          readOnly
        />
      </Container>

      <Box
        className="batch-report-no-print"
        sx={{
          position: 'sticky',
          bottom: 0,
          left: 0,
          right: 0,
          py: 1.5,
          px: 2,
          mt: 4,
          borderTop: 1,
          borderColor: 'divider',
          bgcolor: 'background.paper',
          display: 'flex',
          justifyContent: 'center',
          zIndex: 10,
        }}
      >
        <Button
          component={RouterLink}
          to={registerHref}
          variant="contained"
          size="large"
          onClick={() => trackMarketingEvent('cta_click', {
            location: 'example_page_sticky',
            source: MARKETING_SOURCES.EXAMPLE_PAGE,
          })}
          sx={{ bgcolor: '#4f46e5', textTransform: 'none', fontWeight: 700, '&:hover': { bgcolor: '#4338ca' } }}
        >
          Get your own Batch Coach report
        </Button>
      </Box>
    </Box>
  );
};

export default ExampleBatchReportPage;
