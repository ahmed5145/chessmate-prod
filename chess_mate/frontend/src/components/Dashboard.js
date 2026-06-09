import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  Brain,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Clock,
  Sparkles,
  XCircle,
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useUser } from '../contexts/UserContext';
import { formatDate } from '../utils/dateUtils';
import { fetchDashboardData, refreshDashboardCache } from '../services/apiRequests';
import {
  buildHeroMetrics,
  formatTimeControlLabel,
  isGameRowAnalyzed,
  resolveFocusInsight,
  resolveNextAction,
} from '../utils/dashboardFocus';
import {
  resolveDashboardPageCopy,
  resolveDashboardSections,
} from '../utils/dashboardLayout';
import LoadingSpinner from './LoadingSpinner';
import WelcomeGuide from './WelcomeGuide';
import PwaInstallPrompt from './PwaInstallPrompt';
import GamePlatformBadge from './GamePlatformBadge';
import CoachInboxCard from './dashboard/CoachInboxCard';
import DashboardOneThingCard from './dashboard/DashboardOneThingCard';
import DashboardPageHeader from './dashboard/DashboardPageHeader';
import DashboardSection from './dashboard/DashboardSection';
import FixRateCard from './batch/FixRateCard';
import DashboardNotificationsCard from './dashboard/DashboardNotificationsCard';
import PhaseResultHeatmap from './dashboard/PhaseResultHeatmap';
import { resolveOneThingToday } from '../utils/oneThingToday';

const formatResultLabel = (result) => {
  const normalized = String(result || '').toLowerCase();
  if (normalized === 'win') return 'Win';
  if (normalized === 'loss') return 'Loss';
  if (normalized === 'draw') return 'Draw';
  return normalized ? normalized.toUpperCase() : '—';
};

const INSIGHT_ICONS = {
  success: CheckCircle,
  warning: AlertTriangle,
  error: XCircle,
};

const INSIGHT_COLORS = {
  success: 'text-green-500',
  warning: 'text-amber-500',
  error: 'text-red-500',
};

const resolveDashboardOpponent = (game, user) => {
  if (game.opponent && game.opponent !== 'Unknown') {
    return game.opponent;
  }
  const platformUser =
    game.platform === 'chess.com'
      ? user?.chess_com_username
      : game.platform === 'lichess'
        ? user?.lichess_username
        : null;
  const names = [platformUser, user?.username].filter(Boolean);
  for (const name of names) {
    const lower = name.toLowerCase();
    if (game.white && lower === String(game.white).toLowerCase()) {
      return game.black || 'Unknown';
    }
    if (game.black && lower === String(game.black).toLowerCase()) {
      return game.white || 'Unknown';
    }
  }
  return game.white || game.black || 'Unknown';
};

const DashboardSinceLastVisit = ({ sinceLastVisit }) => {
  const { isDarkMode } = useTheme();

  if (!sinceLastVisit?.showBanner || !sinceLastVisit.summaryLines?.length) {
    return null;
  }

  return (
    <section
      className={`mb-6 flex items-start gap-3 rounded-xl border px-4 py-3 ${
        isDarkMode
          ? 'bg-indigo-950/30 border-indigo-800/60'
          : 'bg-indigo-50 border-indigo-200'
      }`}
    >
      <Clock className={`h-4 w-4 mt-0.5 shrink-0 ${isDarkMode ? 'text-indigo-300' : 'text-indigo-600'}`} />
      <div>
        <p className={`text-xs font-semibold uppercase tracking-wide ${
          isDarkMode ? 'text-indigo-200' : 'text-indigo-800'
        }`}>
          Since your last visit
        </p>
        <p className={`text-sm mt-0.5 ${isDarkMode ? 'text-gray-200' : 'text-gray-700'}`}>
          {sinceLastVisit.summaryLines.join(' · ')}
        </p>
      </div>
    </section>
  );
};

const DashboardHero = ({ dashboardData }) => {
  const { isDarkMode } = useTheme();
  const action = resolveNextAction(dashboardData);
  const metrics = buildHeroMetrics(dashboardData);

  return (
    <section
      className={`rounded-2xl p-6 sm:p-8 mb-8 border ${
        isDarkMode
          ? 'bg-gradient-to-br from-gray-800 to-gray-900 border-gray-700'
          : 'bg-gradient-to-br from-white to-indigo-50/60 border-gray-200'
      } shadow-lg`}
    >
      <h2 className={`text-xl sm:text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
        {action.title}
      </h2>
      <p className={`mt-2 max-w-2xl text-sm sm:text-base ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
        {action.description}
      </p>

      {metrics.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {metrics.map((metric) => (
            <span
              key={metric.label}
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
                isDarkMode ? 'bg-gray-700 text-gray-200' : 'bg-white text-gray-700 border border-gray-200'
              }`}
            >
              <span className={isDarkMode ? 'text-gray-400' : 'text-gray-500'}>{metric.label}</span>
              <span>{metric.value}</span>
            </span>
          ))}
        </div>
      )}

      <div className="mt-6 flex flex-col sm:flex-row sm:items-center gap-3">
        <Link
          to={action.ctaTo}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors"
        >
          {action.ctaLabel}
          <ArrowRight className="h-4 w-4" />
        </Link>
        {(action.secondaryLinks || []).map((link) => (
          <Link
            key={link.to}
            to={link.to}
            className={`text-sm font-medium ${
              isDarkMode ? 'text-indigo-300 hover:text-indigo-200' : 'text-indigo-600 hover:text-indigo-700'
            }`}
          >
            {link.label}
          </Link>
        ))}
      </div>
    </section>
  );
};

const DashboardFocusCard = ({ dashboardData }) => {
  const { isDarkMode } = useTheme();
  const focus = resolveFocusInsight(dashboardData);
  const Icon = INSIGHT_ICONS[focus.type] || Sparkles;
  const iconColor = INSIGHT_COLORS[focus.type] || 'text-indigo-500';

  return (
    <article
      className={`rounded-xl p-5 sm:p-6 border ${
        isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
      } shadow-lg`}
    >
      <div className="flex items-center gap-2 mb-3">
        <Brain className={`h-5 w-5 ${isDarkMode ? 'text-indigo-400' : 'text-indigo-600'}`} />
        <h3 className={`text-base font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
          From your latest report
        </h3>
      </div>

      <div className="flex items-start gap-3">
        <Icon className={`h-5 w-5 mt-0.5 shrink-0 ${iconColor}`} />
        <div className="min-w-0 flex-1">
          {focus.meta ? (
            <p className={`text-xs mb-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              {focus.meta}
            </p>
          ) : null}
          <p className={`text-sm leading-relaxed ${isDarkMode ? 'text-gray-200' : 'text-gray-700'}`}>
            {focus.text}
          </p>
          {focus.href && focus.actionLabel ? (
            <Link
              to={focus.href}
              className={`inline-flex items-center gap-1 mt-3 text-sm font-medium ${
                isDarkMode ? 'text-indigo-300 hover:text-indigo-200' : 'text-indigo-600 hover:text-indigo-700'
              }`}
            >
              {focus.actionLabel}
              <ChevronRight className="h-4 w-4" />
            </Link>
          ) : null}
        </div>
      </div>
    </article>
  );
};

const RecentActivityRow = ({ game, user }) => {
  const { isDarkMode } = useTheme();
  const opponent = resolveDashboardOpponent(game, user);
  const analyzed = isGameRowAnalyzed(game);

  return (
    <Link
      to={`/game/${game.id}/analysis`}
      className={`flex items-center justify-between gap-3 px-4 py-3 rounded-lg transition-colors ${
        isDarkMode ? 'hover:bg-gray-700/80' : 'hover:bg-gray-50'
      }`}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-sm font-medium truncate ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            vs {opponent}
          </span>
          <GamePlatformBadge platform={game.platform} isDarkMode={isDarkMode} />
          <span className={`text-xs font-medium uppercase ${
            game.result === 'win'
              ? 'text-green-600 dark:text-green-400'
              : game.result === 'loss'
                ? 'text-red-600 dark:text-red-400'
                : isDarkMode ? 'text-gray-400' : 'text-gray-500'
          }`}>
            {formatResultLabel(game.result)}
          </span>
        </div>
        <p className={`text-xs mt-0.5 truncate ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          {game.opening_name || 'Unknown opening'}
          {game.date_played ? ` · ${formatDate(game.date_played)}` : ''}
        </p>
      </div>
      <span className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${
        analyzed
          ? (isDarkMode ? 'bg-green-900/40 text-green-300' : 'bg-green-100 text-green-800')
          : (isDarkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600')
      }`}>
        {analyzed ? 'Analyzed' : 'Unanalyzed'}
      </span>
    </Link>
  );
};

const DashboardRecentActivity = ({ games, user }) => {
  const { isDarkMode } = useTheme();
  const recentGames = (Array.isArray(games) ? games : []).slice(0, 3);

  return (
    <section
      className={`rounded-xl border ${
        isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
      } shadow-lg overflow-hidden`}
    >
      <div className={`flex items-center justify-between px-5 py-4 border-b ${
        isDarkMode ? 'border-gray-700' : 'border-gray-100'
      }`}>
        <h2 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
          Recent games
        </h2>
        <Link
          to="/games"
          className={`text-sm font-medium ${
            isDarkMode ? 'text-indigo-300 hover:text-indigo-200' : 'text-indigo-600 hover:text-indigo-700'
          }`}
        >
          View all
        </Link>
      </div>

      {recentGames.length > 0 ? (
        <div className={`divide-y ${isDarkMode ? 'divide-gray-700' : 'divide-gray-100'}`}>
          {recentGames.map((game, index) => (
            <RecentActivityRow key={game.id || index} game={game} user={user} />
          ))}
        </div>
      ) : (
        <div className="px-5 py-8 text-center">
          <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            No games yet.{' '}
            <Link to="/fetch-games" className="text-indigo-500 hover:text-indigo-400 font-medium">
              Import your games
            </Link>
          </p>
        </div>
      )}
    </section>
  );
};

const DashboardMoreStats = ({ dashboardData }) => {
  const { isDarkMode } = useTheme();
  const [expanded, setExpanded] = useState(false);
  const timeControls = dashboardData?.time_control_performance || dashboardData?.performance?.time_controls || {};
  const platforms = dashboardData?.platform_stats || dashboardData?.performance?.platforms || {};
  const timeControlEntries = Object.entries(timeControls).filter(([, data]) => Number(data?.total) > 0);
  const platformEntries = Object.entries(platforms).filter(([, data]) => Number(data?.total) > 0);

  if (timeControlEntries.length === 0 && platformEntries.length === 0) {
    return null;
  }

  return (
    <div>
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        className={`flex w-full items-center justify-between rounded-xl border px-5 py-4 text-left transition-colors ${
          isDarkMode
            ? 'bg-gray-800 border-gray-700 hover:bg-gray-700/80'
            : 'bg-white border-gray-200 hover:bg-gray-50'
        }`}
      >
        <span className={`text-sm font-medium ${isDarkMode ? 'text-gray-200' : 'text-gray-800'}`}>
          More stats
        </span>
        <ChevronDown className={`h-4 w-4 transition-transform ${expanded ? 'rotate-180' : ''} ${
          isDarkMode ? 'text-gray-400' : 'text-gray-500'
        }`} />
      </button>

      {expanded && (
        <div className={`mt-3 grid grid-cols-1 md:grid-cols-2 gap-4`}>
          {timeControlEntries.length > 0 && (
            <div className={`rounded-xl border p-4 ${
              isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
            }`}>
              <h3 className={`text-sm font-semibold mb-3 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                By time control
              </h3>
              <ul className="space-y-2">
                {timeControlEntries.map(([key, data]) => (
                  <li key={key} className="flex justify-between text-sm">
                    <span className={isDarkMode ? 'text-gray-300' : 'text-gray-600'}>
                      {formatTimeControlLabel(key)}
                    </span>
                    <span className={isDarkMode ? 'text-gray-200' : 'text-gray-800'}>
                      {data.total} games · {data.win_rate}% wins
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {platformEntries.length > 0 && (
            <div className={`rounded-xl border p-4 ${
              isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
            }`}>
              <h3 className={`text-sm font-semibold mb-3 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                By platform
              </h3>
              <ul className="space-y-2">
                {platformEntries.map(([key, data]) => (
                  <li key={key} className="flex justify-between text-sm">
                    <span className={isDarkMode ? 'text-gray-300' : 'text-gray-600'}>
                      {key === 'chess.com' ? 'Chess.com' : key === 'lichess' ? 'Lichess' : key}
                    </span>
                    <span className={isDarkMode ? 'text-gray-200' : 'text-gray-800'}>
                      {data.total} games · {data.win_rate}% wins
                    </span>
                  </li>
                ))}
              </ul>
              <Link
                to="/profile"
                className={`inline-block mt-3 text-xs font-medium ${
                  isDarkMode ? 'text-indigo-300' : 'text-indigo-600'
                }`}
              >
                Full stats on Profile →
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const Dashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [oneThingHidden, setOneThingHidden] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { isDarkMode } = useTheme();
  const { user } = useUser();
  const [lastUpdate, setLastUpdate] = useState(Date.now());

  useEffect(() => {
    loadDashboardData();
  }, [lastUpdate]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const data = await fetchDashboardData();
      setDashboardData(data);
      setError(null);
    } catch (loadError) {
      console.error('Error loading dashboard data:', loadError);
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const refreshDashboardData = () => {
    setLastUpdate(Date.now());
  };

  useEffect(() => {
    const handleGameImported = async () => {
      await refreshDashboardCache();
      refreshDashboardData();
    };

    const handleCreditUpdate = () => {
      refreshDashboardData();
    };

    window.addEventListener('game-imported', handleGameImported);
    window.addEventListener('credits-updated', handleCreditUpdate);

    return () => {
      window.removeEventListener('game-imported', handleGameImported);
      window.removeEventListener('credits-updated', handleCreditUpdate);
    };
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <div className={`min-h-screen ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'} flex items-center justify-center`}>
        <div className={`p-6 rounded-xl ${isDarkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'} shadow-lg`}>
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <p className={`text-center ${isDarkMode ? 'text-red-400' : 'text-red-600'}`}>
            {error}
          </p>
          <button
            type="button"
            onClick={loadDashboardData}
            className="mt-4 w-full px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!dashboardData) {
    return null;
  }

  const sections = resolveDashboardSections(dashboardData, user);
  const pageCopy = resolveDashboardPageCopy(sections.stage, user?.username || 'there');

  return (
    <div className={`min-h-screen ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'} py-8`}>
      <WelcomeGuide />
      <PwaInstallPrompt batchesCompleted={dashboardData.batches_completed || 0} />
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <DashboardPageHeader eyebrow={pageCopy.eyebrow} subtitle={pageCopy.subtitle} />

        <DashboardHero dashboardData={dashboardData} />

        {sections.showSinceLastVisit ? (
          <DashboardSinceLastVisit sinceLastVisit={dashboardData.sinceLastVisit} />
        ) : null}

        <DashboardNotificationsCard />

        {sections.showCoachSection ? (
          <DashboardSection
            title={sections.coachSection.title}
            description={sections.coachSection.description}
          >
            {sections.showOneThingToday && !oneThingHidden ? (
              <DashboardOneThingCard
                oneThing={resolveOneThingToday(dashboardData)}
                onSnooze={() => setOneThingHidden(true)}
              />
            ) : null}
            <CoachInboxCard
              priorityInbox={dashboardData.priority_inbox}
              onInboxUpdated={(payload) => {
                if (payload?.priority_inbox) {
                  setDashboardData((current) => ({
                    ...current,
                    priority_inbox: payload.priority_inbox,
                  }));
                }
              }}
            />
          </DashboardSection>
        ) : null}

        {sections.showProgressSection ? (
          <DashboardSection
            title="Your progress"
            description="Track patterns you fixed and where losses cluster by phase."
          >
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
              <FixRateCard fixRate={dashboardData.fix_rate} compact variant="dashboard" />
              <PhaseResultHeatmap phaseHeatmap={dashboardData.phase_heatmap} />
            </div>
          </DashboardSection>
        ) : null}

        {sections.showFocusSection ? (
          <DashboardSection
            title="Coach insight"
            description="A deeper read from your latest batch analysis."
          >
            <DashboardFocusCard dashboardData={dashboardData} />
          </DashboardSection>
        ) : null}

        <DashboardSection
          title="Your games"
          description={
            sections.stage === 'new'
              ? 'Import games to populate your library.'
              : 'Jump back into recent games or run another batch when you have new material.'
          }
        >
          <DashboardRecentActivity games={dashboardData.recent_games} user={user} />
          {sections.showMoreStats ? (
            <DashboardMoreStats dashboardData={dashboardData} />
          ) : null}
        </DashboardSection>
      </div>
    </div>
  );
};

export default Dashboard;
