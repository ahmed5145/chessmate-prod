import { useEffect, useState } from 'react';
import api from '../services/api';

const INITIAL_CONFIG = {
  loading: true,
  support_email: null,
  signup_bonus_credits: null,
  google_oauth_enabled: false,
  legal_entity_name: '',
  legal_entity_incorporated: false,
  legal_governing_law: 'the State of Delaware, United States',
  legal_entity_address: '',
};

/**
 * Public site metadata from GET /api/v1/public/site-config/ (SUPPORT_EMAIL on EB).
 */
export function useSiteConfig() {
  const [config, setConfig] = useState(INITIAL_CONFIG);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const response = await api.get('/api/v1/public/site-config/');
        const data = response.data || {};
        if (!active) {
          return;
        }
        setConfig({
          loading: false,
          support_email: data.support_email || null,
          signup_bonus_credits: data.signup_bonus_credits,
          google_oauth_enabled: Boolean(data.google_oauth_enabled),
          legal_entity_name: data.legal_entity_name || '',
          legal_entity_incorporated: Boolean(data.legal_entity_incorporated),
          legal_governing_law: data.legal_governing_law || INITIAL_CONFIG.legal_governing_law,
          legal_entity_address: data.legal_entity_address || '',
        });
        setError(null);
      } catch (loadError) {
        if (active) {
          setConfig((prev) => ({ ...prev, loading: false }));
          setError(loadError);
        }
      }
    };

    load();
    return () => {
      active = false;
    };
  }, []);

  return { ...config, error };
}
