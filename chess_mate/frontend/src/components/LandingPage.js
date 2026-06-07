import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Crown, Download, Layers, FileText } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useUser } from '../contexts/UserContext';
import api from '../services/api';

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

const LandingPage = () => {
  const { isDarkMode } = useTheme();
  const { user } = useUser();
  const [signupBonus, setSignupBonus] = useState(15);

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
            Your last 10 games.
            <br />
            <span className={isDarkMode ? 'text-indigo-300' : 'text-indigo-600'}>One coaching report.</span>
          </h1>

          <p className={`text-lg sm:text-xl mb-8 max-w-2xl mx-auto ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            Import from Chess.com or Lichess, pick 5–10 recent games, and get cross-game patterns —
            openings, blunders, drills, and a coach-style action plan. Not just one-game engine lines.
          </p>

          <p className={`text-sm mb-10 ${isDarkMode ? 'text-indigo-200' : 'text-indigo-700'}`}>
            New accounts get <strong>{signupBonus} free credits</strong> (~{Math.floor(signupBonus / 10)} batch report
            {Math.floor(signupBonus / 10) === 1 ? '' : 's'} at 10 games each).
          </p>

          {!user ? (
            <div className="flex flex-col sm:flex-row justify-center gap-4">
              <Link
                to="/register"
                className="inline-flex items-center justify-center px-8 py-4 text-lg font-medium rounded-xl text-white bg-indigo-600 hover:bg-indigo-700 shadow-lg"
              >
                Get started free
              </Link>
              <Link
                to="/login"
                className={`inline-flex items-center justify-center px-8 py-4 text-lg font-medium rounded-xl border shadow-lg ${
                  isDarkMode
                    ? 'border-gray-600 text-white hover:bg-gray-800'
                    : 'border-gray-300 text-gray-700 hover:bg-white'
                }`}
              >
                Sign in
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

      <div className={`py-20 ${isDarkMode ? 'bg-gray-800/40' : 'bg-white'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className={`text-3xl font-bold mb-3 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              How it works
            </h2>
            <Link
              to="/how-batch-coach-works"
              className={`text-sm font-medium underline underline-offset-2 ${
                isDarkMode ? 'text-indigo-300 hover:text-indigo-200' : 'text-indigo-600 hover:text-indigo-800'
              }`}
            >
              Full Batch Coach guide →
            </Link>
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
              description="Select 5–10 games — your last blitz week, or a manual mix. Batch coach analysis is included."
              isDarkMode={isDarkMode}
            />
            <Step
              number="3"
              title="Read your report"
              description="Stockfish depth 14 + AI coaching: recurring mistakes, opening gaps, drills, and shareable link."
              isDarkMode={isDarkMode}
            />
          </div>
        </div>
      </div>

      <div className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-center">
            <div className={`p-6 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'} shadow`}>
              <Download className={`w-8 h-8 mx-auto mb-3 ${isDarkMode ? 'text-indigo-300' : 'text-indigo-600'}`} />
              <p className={`font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>Chess.com & Lichess</p>
            </div>
            <div className={`p-6 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'} shadow`}>
              <Layers className={`w-8 h-8 mx-auto mb-3 ${isDarkMode ? 'text-indigo-300' : 'text-indigo-600'}`} />
              <p className={`font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>5–30 game batches</p>
            </div>
            <div className={`p-6 rounded-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'} shadow`}>
              <FileText className={`w-8 h-8 mx-auto mb-3 ${isDarkMode ? 'text-indigo-300' : 'text-indigo-600'}`} />
              <p className={`font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>Shareable coach report</p>
            </div>
          </div>
        </div>
      </div>

      {!user && (
        <div className="pb-24 text-center">
          <p className={`mb-6 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            Feedback welcome — we&apos;re actively improving the beta.
          </p>
          <Link
            to="/register"
            className="inline-flex items-center px-8 py-4 text-lg font-medium rounded-xl text-white bg-indigo-600 hover:bg-indigo-700"
          >
            Try batch coach free
          </Link>
        </div>
      )}
    </div>
  );
};

export default LandingPage;
