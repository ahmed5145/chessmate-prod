import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Brain,
  Crown,
  Download,
  FileText,
  Layers,
  Shield,
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useUser } from '../contexts/UserContext';
import api from '../services/api';
import BatchReportPreview from './marketing/BatchReportPreview';
import LandingValueBullets from './marketing/LandingValueBullets';
import { buildLoginHref, buildRegisterHref, MARKETING_SOURCES } from '../utils/marketingLinks';
import { trackMarketingEvent } from '../utils/marketingAnalytics';
import { PAGE_META, usePageMeta } from '../utils/pageMeta';

const Step = ({ number, title, description, isDarkMode }) => (
  <div className={`p-6 rounded-xl ${isDarkMode ? 'bg-gray-800' : 'bg-white'} shadow-lg`}>
    <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold mb-4 ${
      isDarkMode ? 'bg-indigo-900 text-indigo-200' : 'bg-indigo-100 text-indigo-700'
    }`}>
      {number}
    </div>
    <h3 className={`text-lg font-bold mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>{title}</h3>
    <p className={isDarkMode ? 'text-gray-300' : 'text-gray-600'}>{description}</p>
  </div>
);

const TRUST_ITEMS = [
  {
    icon: Download,
    title: 'Chess.com & Lichess',
    description: 'Import recent games with one linked account.',
  },
  {
    icon: Layers,
    title: '5–30 game batches',
    description: 'Pick a stretch of games — Batch Coach finds patterns across them.',
  },
  {
    icon: FileText,
    title: 'Shareable coach report',
    description: 'Read-only link for coaches, friends, or study groups.',
  },
];

const LandingPage = () => {
  const { isDarkMode } = useTheme();
  const { user } = useUser();
  const [signupBonus, setSignupBonus] = useState(15);

  usePageMeta(PAGE_META.landing);

  useEffect(() => {
    trackMarketingEvent('landing_view', { source: MARKETING_SOURCES.LANDING_HERO });
  }, []);

  useEffect(() => {
    const load = async () => {
      try {
        const response = await api.get('/api/v1/public/site-config/');
        if (response.data?.signup_bonus_credits) {
          setSignupBonus(response.data.signup_bonus_credits);
        }
      } catch (error) {
        console.warn('Using default signup bonus:', error);
      }
    };
    load();
  }, []);

  const importGames = signupBonus;
  const exampleHref = '/example/batch-report';

  return (
    <div className={`min-h-screen ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <div className="relative overflow-hidden">
        <div className={`absolute inset-0 ${
          isDarkMode
            ? 'bg-gradient-to-br from-gray-900 via-indigo-950/30 to-gray-900'
            : 'bg-gradient-to-br from-gray-50 via-indigo-50/40 to-gray-50'
        }`} />

        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-16 text-center">
          <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium mb-6 ${
            isDarkMode ? 'bg-indigo-900 text-indigo-200' : 'bg-indigo-100 text-indigo-800'
          }`}>
            Beta — now open at chess-mate.online
          </span>

          <div className="flex justify-center mb-6">
            <Crown className={`h-16 w-16 ${isDarkMode ? 'text-indigo-400' : 'text-indigo-600'}`} />
          </div>

          <h1 className={`text-4xl sm:text-5xl font-extrabold mb-6 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Your recent games.
            <br />
            <span className={isDarkMode ? 'text-indigo-300' : 'text-indigo-600'}>One coaching report.</span>
          </h1>

          <p className={`text-lg sm:text-xl mb-4 max-w-2xl mx-auto ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            Import from Chess.com or Lichess, pick 5–30 games, and get cross-game patterns —
            openings, blunders, drills, and a coach-style action plan.
          </p>

          <p className={`text-base mb-4 max-w-xl mx-auto font-medium ${isDarkMode ? 'text-indigo-200' : 'text-indigo-700'}`}>
            Not engine lines per move — patterns across your games.
          </p>
          <p className={`text-sm mb-8 max-w-lg mx-auto ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            Drill into any cited game with a depth-20 review — your first single-game deep review is free.
          </p>

          <p className={`text-sm mb-10 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            New accounts get <strong className={isDarkMode ? 'text-indigo-200' : 'text-indigo-700'}>{signupBonus} free credits</strong>
            {' '}(import up to {importGames} games at 1 credit each — Batch Coach included).
            {' '}Engine stats plus AI coaching across 5–30 games.
          </p>

          {!user ? (
            <div className="flex flex-col items-center gap-4">
              <div className="flex flex-col sm:flex-row justify-center gap-4 w-full sm:w-auto">
                <Link
                  to={buildRegisterHref(MARKETING_SOURCES.LANDING_HERO)}
                  onClick={() => trackMarketingEvent('cta_click', {
                    location: 'landing_hero',
                    source: MARKETING_SOURCES.LANDING_HERO,
                  })}
                  className="inline-flex items-center justify-center px-8 py-4 text-lg font-semibold rounded-xl text-white bg-indigo-600 hover:bg-indigo-700 shadow-lg"
                >
                  Get your own report — free
                </Link>
                <Link
                  to={exampleHref}
                  onClick={() => trackMarketingEvent('full_example_open', {
                    location: 'landing_hero',
                    source: MARKETING_SOURCES.LANDING_HERO,
                  })}
                  className={`inline-flex items-center justify-center gap-2 px-8 py-4 text-lg font-semibold rounded-xl border shadow-lg ${
                    isDarkMode
                      ? 'border-indigo-500/50 text-indigo-100 hover:bg-indigo-950/40'
                      : 'border-indigo-200 text-indigo-700 hover:bg-indigo-50'
                  }`}
                >
                  View full example report
                  <ArrowRight className="h-5 w-5" />
                </Link>
              </div>
              <Link
                to={buildLoginHref(MARKETING_SOURCES.LANDING_HERO)}
                className={`text-sm font-medium hover:underline ${
                  isDarkMode ? 'text-gray-400 hover:text-gray-300' : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                Already have an account? Sign in
              </Link>
            </div>
          ) : (
            <Link
              to="/dashboard"
              className="inline-flex items-center justify-center px-8 py-4 text-lg font-medium rounded-xl text-white bg-indigo-600 hover:bg-indigo-700 shadow-lg"
            >
              Go to dashboard
            </Link>
          )}
        </div>
      </div>

      <div className={`py-16 ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-2">
            <h2 className={`text-2xl sm:text-3xl font-bold mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              See a real Batch Coach report
            </h2>
            <p className={`text-sm max-w-lg mx-auto ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Engine stats, top priorities, phase breakdown, coaching insights, and a 4-week plan — preview below.
            </p>
          </div>
          <BatchReportPreview />
          <LandingValueBullets />
          <p className={`mt-6 flex items-start justify-center gap-2 text-xs max-w-lg mx-auto text-center ${
            isDarkMode ? 'text-gray-500' : 'text-gray-500'
          }`}>
            <Shield className="h-4 w-4 shrink-0 mt-0.5" aria-hidden />
            <span>
              Example uses anonymized players. Your report stays private unless you choose to share it.
            </span>
          </p>
        </div>
      </div>

      <div className={`py-20 ${isDarkMode ? 'bg-gray-800/40' : 'bg-white'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className={`text-3xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              How it works
            </h2>
            <Link
              to="/how-batch-coach-works"
              className={`inline-flex items-center gap-2 mt-4 px-6 py-3 rounded-full text-sm font-semibold transition-all ${
                isDarkMode
                  ? 'bg-indigo-600 text-white hover:bg-indigo-500 shadow-lg shadow-indigo-950/40'
                  : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-md'
              }`}
            >
              <Brain className="h-4 w-4 shrink-0" />
              <span>See the full Batch Coach guide</span>
              <ArrowRight className="h-4 w-4 shrink-0" />
            </Link>
            <p className={`text-sm mt-4 max-w-md mx-auto ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              Import → pick 5–30 games → read your report. Scroll up to preview an example first.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <Step
              number="1"
              title="Import games"
              description="Connect Chess.com or Lichess and pull in recent games (1 credit per game imported)."
              isDarkMode={isDarkMode}
            />
            <Step
              number="2"
              title="Pick a batch"
              description="Select 5–30 games — your last blitz week, or a manual mix. Batch Coach is included."
              isDarkMode={isDarkMode}
            />
            <Step
              number="3"
              title="Read your report"
              description="Open priorities, opening gaps, drills, and a training plan — or compare with the example report above."
              isDarkMode={isDarkMode}
            />
          </div>
        </div>
      </div>

      <div className={`py-16 ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {TRUST_ITEMS.map(({ icon: Icon, title, description }) => (
              <div
                key={title}
                className={`p-6 rounded-xl text-center ${
                  isDarkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200 shadow-sm'
                }`}
              >
                <Icon className={`w-8 h-8 mx-auto mb-3 ${isDarkMode ? 'text-indigo-300' : 'text-indigo-600'}`} />
                <p className={`font-semibold mb-1 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>{title}</p>
                <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>{description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {!user && (
        <div className="pb-24 text-center px-4">
          <h2 className={`text-2xl font-bold mb-3 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Ready for your own coaching report?
          </h2>
          <p className={`mb-6 max-w-md mx-auto ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            {signupBonus} free credits to import games and run Batch Coach. Feedback welcome — we&apos;re actively improving the beta.
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-3">
            <Link
              to={buildRegisterHref(MARKETING_SOURCES.LANDING_EXAMPLE)}
              onClick={() => trackMarketingEvent('cta_click', {
                location: 'landing_footer',
                source: MARKETING_SOURCES.LANDING_EXAMPLE,
              })}
              className="inline-flex items-center justify-center px-8 py-4 text-lg font-semibold rounded-xl text-white bg-indigo-600 hover:bg-indigo-700 shadow-lg"
            >
              Get your own report — free
            </Link>
            <Link
              to={exampleHref}
              onClick={() => trackMarketingEvent('full_example_open', {
                location: 'landing_footer',
                source: MARKETING_SOURCES.LANDING_EXAMPLE,
              })}
              className={`inline-flex items-center justify-center gap-2 px-8 py-4 text-lg font-semibold rounded-xl border ${
                isDarkMode
                  ? 'border-gray-600 text-white hover:bg-gray-800'
                  : 'border-gray-300 text-gray-700 hover:bg-white'
              }`}
            >
              View example report
              <ArrowRight className="h-5 w-5" />
            </Link>
          </div>
        </div>
      )}
    </div>
  );
};

export default LandingPage;
