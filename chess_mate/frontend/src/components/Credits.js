import React, { useState, useEffect, useContext } from 'react';
import { toast } from 'react-hot-toast';
import { CreditCard } from 'lucide-react';
import { UserContext } from '../contexts/UserContext';
import { useTheme } from '../context/ThemeContext';
import api from '../services/api';
import { confirmPurchase } from '../services/apiRequests';
import { extractApiError } from '../utils/apiErrors';

const FALLBACK_PACKAGES = [
  {
    id: 'basic',
    name: 'Coach Starter',
    credits: 50,
    price_display: '$9.99',
    description: 'Buy credits once — import your first batch of games',
    popular: false,
    features: [
      'One-time purchase (not a subscription)',
      '50 game imports (1 credit per game)',
      'Credits never expire',
      '~5 Batch Coach reports (10 games each)',
    ]
  },
  {
    id: 'pro',
    name: 'Coach Plus',
    credits: 100,
    price_display: '$17.99',
    description: 'Buy credits once for regular Batch Coach',
    popular: true,
    features: [
      'One-time purchase (not a subscription)',
      '100 game imports',
      'Credits never expire',
      '~10 Batch Coach reports (10 games each)',
    ]
  },
  {
    id: 'premium',
    name: 'Coach Pro',
    credits: 250,
    price_display: '$39.99',
    description: 'Buy credits once for a serious improvement loop',
    popular: false,
    features: [
      'One-time purchase (not a subscription)',
      '250 game imports',
      'Credits never expire',
      '~25 Batch Coach reports (10 games each)',
    ]
  }
];

const DEFAULT_CREDIT_MODEL = {
  credits_per_imported_game: 1,
  batch_credits_per_game: 0,
  signup_bonus_credits: 15,
  single_game_analysis_credits: 1,
  batch_games_recommended: 10,
  batch_included: true,
  summary_points: [
    '1 credit per game import from Chess.com or Lichess',
    'Batch Coach is included once games are on your account',
    'New accounts receive 15 free credits',
    'Optional single-game deep analysis costs 1 credit per game',
    'Credits are sold as one-time packs — not a subscription',
    'Purchased credits do not expire while your account stays active',
  ],
};

const Credits = () => {
  const [loading, setLoading] = useState(false);
  const [confirmingPayment, setConfirmingPayment] = useState(false);
  const [packages, setPackages] = useState(FALLBACK_PACKAGES);
  const [creditModel, setCreditModel] = useState(DEFAULT_CREDIT_MODEL);
  const { credits, fetchUserData } = useContext(UserContext);
  const { isDarkMode } = useTheme();

  useEffect(() => {
    fetchUserData();
  }, [fetchUserData]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get('session_id');
    if (!sessionId) {
      return;
    }

    const finalize = async () => {
      setConfirmingPayment(true);
      try {
        const result = await confirmPurchase(sessionId);
        const added = result.credits_added ?? result.credits ?? 0;
        if (result.already_confirmed) {
          toast.success('Payment was already applied to your account.');
        } else {
          toast.success(`Added ${added} credits to your account.`);
        }
        await fetchUserData();
      } catch (error) {
        console.error('Credit purchase confirm failed:', error);
        toast.error(extractApiError(error, 'Could not confirm payment. Contact support if you were charged.'), {
          duration: 8000,
        });
      } finally {
        setConfirmingPayment(false);
        params.delete('session_id');
        const next = `${window.location.pathname}${params.toString() ? `?${params}` : ''}`;
        window.history.replaceState({}, '', next);
      }
    };

    finalize();
  }, [fetchUserData]);

  useEffect(() => {
    const loadPackages = async () => {
      try {
        const response = await api.get('/api/v1/credits/packages/');
        const data = response.data || {};
        if (Array.isArray(data.packages) && data.packages.length > 0) {
          setPackages(data.packages);
        }
        if (Array.isArray(data.summary_points) && data.summary_points.length > 0) {
          setCreditModel({
            credits_per_imported_game: data.credits_per_imported_game ?? 1,
            batch_credits_per_game: data.batch_credits_per_game ?? 0,
            signup_bonus_credits: data.signup_bonus_credits ?? 15,
            single_game_analysis_credits: data.single_game_analysis_credits ?? 1,
            batch_games_recommended: data.batch_games_recommended ?? 10,
            batch_included: data.batch_included ?? data.batch_credits_per_game === 0,
            summary_points: data.summary_points,
          });
        }
      } catch (error) {
        console.warn('Using fallback credit packages:', error);
      }
    };
    loadPackages();
  }, []);

  const handlePurchase = async (packageId) => {
    setLoading(true);
    try {
      const accessToken = localStorage.getItem('tokens')
        ? JSON.parse(localStorage.getItem('tokens')).access
        : null;
      if (!accessToken) {
        toast.error('Please log in to purchase credits');
        return;
      }

      const response = await api.post(
        '/api/v1/purchase-credits/',
        { package_id: packageId },
        {
          headers: {
            Authorization: `Bearer ${accessToken}`
          }
        }
      );

      if (!response.data.checkout_url) {
        throw new Error('No checkout URL received');
      }

      window.location.href = response.data.checkout_url;
    } catch (error) {
      console.error('Error processing request:', error);
      toast.error(error.response?.data?.detail || error.message || 'Failed to process request');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 ${isDarkMode ? 'bg-gray-900' : 'bg-white'}`}>
      {confirmingPayment && (
        <div className={`mb-6 rounded-md px-4 py-3 text-sm ${
          isDarkMode ? 'bg-indigo-900 text-indigo-100' : 'bg-indigo-50 text-indigo-800'
        }`}>
          Confirming your payment with Stripe…
        </div>
      )}

      <div className="sm:flex sm:flex-col sm:align-center">
        <h2 className={`text-3xl font-extrabold ${isDarkMode ? 'text-white' : 'text-gray-900'} sm:text-center`}>
          Buy credits once
        </h2>
        <p className={`mt-2 text-base font-medium ${isDarkMode ? 'text-indigo-300' : 'text-indigo-700'} sm:text-center`}>
          Not a subscription — credits never expire
        </p>
        <p className={`mt-3 text-lg ${isDarkMode ? 'text-gray-300' : 'text-gray-500'} sm:text-center`}>
          Credits import games from Chess.com or Lichess. Batch Coach is included once games are on your account.
        </p>
        <div className="mt-4 text-center">
          <span className={`inline-flex items-center px-4 py-2 rounded-md ${
            isDarkMode ? 'bg-indigo-900 text-indigo-200' : 'bg-indigo-50 text-indigo-700'
          }`}>
            <CreditCard className="h-5 w-5 mr-2" />
            You currently have {credits} credits available
          </span>
        </div>
      </div>

      <div className={`mt-10 rounded-xl border p-6 ${
        isDarkMode ? 'border-gray-700 bg-gray-800/60' : 'border-gray-200 bg-gray-50'
      }`}>
        <h3 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
          How credits work
        </h3>
        <p className={`mt-2 text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
          Credits pay for game imports. Batch Coach cross-game analysis is bundled once games are stored
          {creditModel.batch_included ? ' at no extra charge' : ''}.
          Typical workflow: import {creditModel.batch_games_recommended} games, run one batch report, repeat.
        </p>
        <ul className={`mt-4 space-y-2 text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
          {(creditModel.summary_points || []).map((point) => (
            <li key={point} className="flex gap-2">
              <span className={isDarkMode ? 'text-indigo-300' : 'text-indigo-600'} aria-hidden>•</span>
              <span>{point}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-12 space-y-4 sm:mt-16 sm:space-y-0 sm:grid sm:grid-cols-2 sm:gap-6 lg:max-w-4xl lg:mx-auto xl:max-w-none xl:mx-0 xl:grid-cols-3">
        {packages.map((pkg) => (
          <div
            key={pkg.id}
            className={`rounded-lg shadow-sm divide-y ${
              isDarkMode
                ? 'bg-gray-800 divide-gray-700'
                : 'divide-gray-200 bg-white'
            } ${
              pkg.popular
                ? 'border-2 border-indigo-500 relative'
                : isDarkMode
                  ? 'border border-gray-700'
                  : 'border border-gray-200'
            }`}
          >
            {pkg.popular && (
              <div className="absolute top-0 right-0 -translate-y-1/2 translate-x-1/2">
                <span className={`inline-flex rounded-full px-4 py-1 text-xs font-semibold ${
                  isDarkMode ? 'bg-indigo-900 text-indigo-200' : 'bg-indigo-100 text-indigo-600'
                }`}>
                  Most Popular
                </span>
              </div>
            )}
            <div className="p-6">
              <h3 className={`text-lg leading-6 font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                {pkg.name}
              </h3>
              <p className={`mt-4 text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-500'}`}>
                {pkg.description}
              </p>
              <p className="mt-8">
                <span className={`text-4xl font-extrabold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                  {pkg.price_display || `$${pkg.price}`}
                </span>
              </p>
              <p className={`mt-2 text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-500'}`}>
                {pkg.credits} credits
                {pkg.batch_reports_approx
                  ? ` · ~${pkg.batch_reports_approx} batch reports`
                  : ''}
              </p>
              <button
                type="button"
                onClick={() => handlePurchase(pkg.id)}
                disabled={loading}
                className={`mt-8 block w-full text-white font-medium py-2 px-4 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors ${
                  pkg.popular
                    ? 'bg-indigo-600 hover:bg-indigo-700 focus:ring-indigo-500'
                    : isDarkMode
                      ? 'bg-gray-600 hover:bg-gray-700 focus:ring-gray-500'
                      : 'bg-gray-600 hover:bg-gray-700 focus:ring-gray-500'
                } ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {loading ? 'Processing...' : 'Purchase Credits'}
              </button>
            </div>
            <div className="px-6 pt-6 pb-8">
              <h4 className={`text-sm font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                What&apos;s included
              </h4>
              <ul className="mt-6 space-y-4">
                {(pkg.features || []).map((feature, index) => (
                  <li key={index} className="flex space-x-3">
                    <svg
                      className={`flex-shrink-0 h-5 w-5 ${isDarkMode ? 'text-green-400' : 'text-green-500'}`}
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                      aria-hidden="true"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <span className={`text-sm ${isDarkMode ? 'text-gray-300' : 'text-gray-500'}`}>
                      {feature}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Credits;
