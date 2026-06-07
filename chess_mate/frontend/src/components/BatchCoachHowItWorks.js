import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Brain,
  BarChart3,
  Crown,
  Download,
  Layers,
  Share2,
  Sparkles,
  Target,
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useUser } from '../contexts/UserContext';
import api from '../services/api';

const Feature = ({ icon: Icon, title, description, isDarkMode }) => (
  <div
    className={`rounded-xl p-6 border ${
      isDarkMode ? 'bg-gray-800/80 border-gray-700' : 'bg-white border-gray-200 shadow-sm'
    }`}
  >
    <Icon className={`h-8 w-8 mb-3 ${isDarkMode ? 'text-indigo-400' : 'text-indigo-600'}`} />
    <h3 className={`text-lg font-semibold mb-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
      {title}
    </h3>
    <p className={isDarkMode ? 'text-gray-300' : 'text-gray-600'}>{description}</p>
  </div>
);

const BatchCoachHowItWorks = () => {
  const { isDarkMode } = useTheme();
  const { user } = useUser();
  const [signupBonus, setSignupBonus] = useState(15);

  useEffect(() => {
    let cancelled = false;
    api.get('/api/v1/public/site-config/')
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
  const sampleReports = Math.max(1, Math.floor(signupBonus / 10));

  return (
    <div className={`min-h-screen ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <section
        className={`relative overflow-hidden border-b ${
          isDarkMode ? 'border-gray-800' : 'border-indigo-100'
        }`}
      >
        <div
          className={`absolute inset-0 ${
            isDarkMode
              ? 'bg-gradient-to-br from-gray-900 via-indigo-950/40 to-gray-900'
              : 'bg-gradient-to-br from-indigo-50 via-white to-gray-50'
          }`}
        />
        <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-14 text-center">
          <span
            className={`inline-block px-3 py-1 rounded-full text-sm font-medium mb-5 ${
              isDarkMode ? 'bg-indigo-900 text-indigo-200' : 'bg-indigo-100 text-indigo-800'
            }`}
          >
            Batch Coach · how it works
          </span>
          <div className="flex justify-center mb-5">
            <Crown className={`h-14 w-14 ${isDarkMode ? 'text-indigo-400' : 'text-indigo-600'}`} />
          </div>
          <h1 className={`text-3xl sm:text-4xl font-extrabold mb-4 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Your games, analyzed together — not one at a time
          </h1>
          <p className={`text-lg max-w-2xl mx-auto mb-8 ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            A friend shared a Batch Coach report with you. Here&apos;s what ChessMate does: Stockfish depth 14
            on every game, plus AI coaching that finds patterns across 5–30 games — openings you leak points in,
            recurring tactics you miss, and a training plan tied to real positions.
          </p>
          {!user ? (
            <div className="flex flex-col sm:flex-row justify-center gap-3">
              <Link
                to="/register"
                className="inline-flex items-center justify-center px-8 py-3.5 text-base font-semibold rounded-xl text-white bg-indigo-600 hover:bg-indigo-700 shadow-lg"
              >
                Get your own report — free
              </Link>
              <Link
                to="/login"
                className={`inline-flex items-center justify-center px-8 py-3.5 text-base font-semibold rounded-xl border ${
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
              to="/batch-analysis"
              className="inline-flex items-center justify-center px-8 py-3.5 text-base font-semibold rounded-xl text-white bg-indigo-600 hover:bg-indigo-700 shadow-lg"
            >
              Start a batch
            </Link>
          )}
          <p className={`mt-5 text-sm ${isDarkMode ? 'text-indigo-200' : 'text-indigo-700'}`}>
            New accounts get <strong>{signupBonus} free {creditLabel}</strong> — enough for about{' '}
            {sampleReports} batch report{sampleReports === 1 ? '' : 's'} at 10 games each.
          </p>
        </div>
      </section>

      <section className="py-14">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className={`text-2xl font-bold text-center mb-8 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            What you get in every report
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <Feature
              icon={BarChart3}
              title="Cross-game patterns"
              description="See recurring blunders, phase weaknesses, and opening records — not isolated one-game engine lines."
              isDarkMode={isDarkMode}
            />
            <Feature
              icon={Brain}
              title="AI coaching narrative"
              description="Executive summary, priorities, and a week-by-week training outline based on your actual mistakes."
              isDarkMode={isDarkMode}
            />
            <Feature
              icon={Target}
              title="Critical moments with diagrams"
              description="Top swings with board positions, best moves, and explanations so you know what to review."
              isDarkMode={isDarkMode}
            />
            <Feature
              icon={Share2}
              title="Shareable link"
              description="Send your report to a coach or friend — they can read it without an account."
              isDarkMode={isDarkMode}
            />
          </div>
        </div>
      </section>

      <section className={`py-14 ${isDarkMode ? 'bg-gray-800/40' : 'bg-white'}`}>
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className={`text-2xl font-bold text-center mb-8 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Three steps to your report
          </h2>
          <ol className="space-y-6">
            {[
              {
                icon: Download,
                title: 'Import from Chess.com or Lichess',
                body: 'Link your account and pull recent games. Import uses credits; batch analysis is included once games are in your library.',
              },
              {
                icon: Layers,
                title: 'Pick 5–30 games for a batch',
                body: 'Your last blitz week, a slump stretch, or a hand-picked mix — Batch Coach needs at least 5 games to find patterns.',
              },
              {
                icon: Sparkles,
                title: 'Read, drill, share',
                body: 'Open the report when ready (we can email you). Study Lichess drills from your weaknesses and share a read-only link.',
              },
            ].map((step, index) => (
              <li
                key={step.title}
                className={`flex gap-4 rounded-xl p-5 border ${
                  isDarkMode ? 'border-gray-700 bg-gray-800/60' : 'border-gray-200 bg-gray-50'
                }`}
              >
                <div
                  className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full font-bold ${
                    isDarkMode ? 'bg-indigo-900 text-indigo-200' : 'bg-indigo-100 text-indigo-700'
                  }`}
                >
                  {index + 1}
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <step.icon className={`h-5 w-5 ${isDarkMode ? 'text-indigo-400' : 'text-indigo-600'}`} />
                    <h3 className={`font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                      {step.title}
                    </h3>
                  </div>
                  <p className={isDarkMode ? 'text-gray-300' : 'text-gray-600'}>{step.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="py-16 text-center">
        <div className="max-w-xl mx-auto px-4">
          <h2 className={`text-2xl font-bold mb-3 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Ready to see your own patterns?
          </h2>
          <p className={`mb-6 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Join free, import a few games, and run your first Batch Coach report in minutes.
          </p>
          {!user ? (
            <Link
              to="/register"
              className="inline-flex items-center px-8 py-4 text-lg font-semibold rounded-xl text-white bg-indigo-600 hover:bg-indigo-700 shadow-lg"
            >
              Create free account
            </Link>
          ) : (
            <Link
              to="/batch-analysis"
              className="inline-flex items-center px-8 py-4 text-lg font-semibold rounded-xl text-white bg-indigo-600 hover:bg-indigo-700 shadow-lg"
            >
              Go to Batch Coach
            </Link>
          )}
        </div>
      </section>
    </div>
  );
};

export default BatchCoachHowItWorks;
