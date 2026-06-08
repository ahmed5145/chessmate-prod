import { useEffect, useState } from 'react';
import api from '../services/api';
import { getPublicBatchReport } from '../services/apiRequests';
import { getDemoBatchReport } from '../content/demoBatchReport';

/**
 * Prefer live demo share token from site-config; fall back to static anonymized fixture.
 */
export const useExampleBatchReport = () => {
  const [batchReport, setBatchReport] = useState(null);
  const [reportSource, setReportSource] = useState('static');
  const [loading, setLoading] = useState(true);
  const [signupBonus, setSignupBonus] = useState(15);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      let bonus = 15;
      let demoToken = '';

      try {
        const configResponse = await api.get('/api/v1/public/site-config/');
        if (!cancelled) {
          bonus = configResponse.data?.signup_bonus_credits || bonus;
          demoToken = (configResponse.data?.demo_batch_share_token || '').trim();
          setSignupBonus(bonus);
        }
      } catch {
        // Static fixture still works offline.
      }

      if (demoToken && !cancelled) {
        try {
          const liveReport = await getPublicBatchReport(demoToken);
          if (!cancelled && liveReport) {
            setBatchReport(liveReport);
            setReportSource('live');
            setLoading(false);
            return;
          }
        } catch {
          // Fall through to static demo.
        }
      }

      if (!cancelled) {
        setBatchReport(getDemoBatchReport());
        setReportSource('static');
        setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return { batchReport, reportSource, loading, signupBonus };
};

export default useExampleBatchReport;
