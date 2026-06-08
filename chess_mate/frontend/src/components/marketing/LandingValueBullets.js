import React from 'react';
import { BarChart3, Share2, Target, Zap } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

const BULLETS = [
  {
    icon: BarChart3,
    title: 'Cross-game patterns',
    description: 'See the same mistake across multiple games — not isolated one-game engine lines.',
  },
  {
    icon: Target,
    title: 'Actionable priorities',
    description: 'Ranked fixes with drills tied to your openings and tactics.',
  },
  {
    icon: Zap,
    title: 'Drills & Lichess links',
    description: 'Practice suggestions mapped to your real positions and repertoire gaps.',
  },
  {
    icon: Share2,
    title: 'Shareable report',
    description: 'Send a read-only link to a coach or study group — no account required to view.',
  },
];

const LandingValueBullets = () => {
  const { isDarkMode } = useTheme();

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-8">
      {BULLETS.map(({ icon: Icon, title, description }) => (
        <div
          key={title}
          className={`rounded-xl p-4 border ${
            isDarkMode ? 'bg-gray-800/60 border-gray-700' : 'bg-white border-gray-200 shadow-sm'
          }`}
        >
          <div className="flex gap-3">
            <Icon className={`h-5 w-5 shrink-0 mt-0.5 ${isDarkMode ? 'text-indigo-400' : 'text-indigo-600'}`} />
            <div>
              <h3 className={`font-semibold text-sm mb-1 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                {title}
              </h3>
              <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                {description}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default LandingValueBullets;
