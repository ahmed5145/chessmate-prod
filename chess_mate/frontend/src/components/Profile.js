import React, { useState, useEffect } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Trophy,
  Target,
  Brain,
  Lock,
  TrendingUp,
  XCircle,
  AlertTriangle,
  Layout,
  Coins,
  Activity
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { useTheme } from '../context/ThemeContext';
import { fetchProfileData } from '../services/apiRequests';
import { default as LoadingSpinner } from '../components/LoadingSpinner';
import ProfileLinkedAccounts from './profile/ProfileLinkedAccounts';
import ProfileCoachSettings from './profile/ProfileCoachSettings';


const StatCard = ({ title, value, icon: Icon, trend, color = 'indigo' }) => {
  const { isDarkMode } = useTheme();
  const trendColor = trend > 0 ? 'text-green-500' : trend < 0 ? 'text-red-500' : 'text-gray-500';

  return (
    <div className={`p-6 rounded-xl transition-all duration-200 hover:scale-[1.02] ${
      isDarkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'
    } shadow-lg`}>
      <div className="flex items-center justify-between">
        <div className={`p-3 rounded-lg ${isDarkMode ? `bg-${color}-900/30` : `bg-${color}-100`}`}>
          <Icon className={`h-6 w-6 ${isDarkMode ? `text-${color}-400` : `text-${color}-600`}`} />
        </div>
        {trend !== undefined && (
          <div className={`flex items-center ${trendColor}`}>
            <TrendingUp className={`h-4 w-4 ${trend > 0 ? '' : 'rotate-180'} mr-1`} />
            <span className="text-sm font-medium">{Math.abs(trend)}%</span>
          </div>
        )}
      </div>
      <div className="mt-4">
        <h3 className={`text-lg font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>{value}</h3>
        <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>{title}</p>
      </div>
    </div>
  );
};

const ProgressChart = ({ data, title }) => {
  const { isDarkMode } = useTheme();
  const maxValue = Math.max(...data.map(d => d.value), 1);

  return (
    <div className={`p-6 rounded-xl ${isDarkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'} shadow-lg`}>
      <h3 className={`text-lg font-semibold mb-4 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
        {title}
      </h3>
      <div className="space-y-4">
        {data.map((item, index) => (
          <div key={index}>
            <div className="flex justify-between text-sm mb-1">
              <span className={isDarkMode ? 'text-gray-400' : 'text-gray-600'}>
                {item.label}
              </span>
              <span className={isDarkMode ? 'text-gray-300' : 'text-gray-700'}>
                {item.value}%
              </span>
            </div>
            <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                style={{ width: `${(item.value / maxValue) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const AchievementsSection = ({ achievements }) => {
  const { isDarkMode } = useTheme();
  const [showModal, setShowModal] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState(null);

  if (!achievements?.length) {
    return (
      <p className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
        Play and analyze games to start earning achievements.
      </p>
    );
  }

  // Group achievements by category
  const categories = {
    games: {
      title: 'Game Milestones',
      icon: Layout,
      items: achievements.filter(a => a.name.includes('Player'))
    },
    rating: {
      title: 'Rating Achievements',
      icon: TrendingUp,
      items: achievements.filter(a => a.name.includes('Rating') || a.name.includes('Star'))
    },
    streaks: {
      title: 'Win Streaks',
      icon: Activity,
      items: achievements.filter(a => a.name.includes('Streak') || a.name.includes('Unstoppable'))
    },
    analysis: {
      title: 'Analysis Mastery',
      icon: Brain,
      items: achievements.filter(a => a.name.includes('Analyst') || a.name.includes('Thinker') || a.name.includes('Student'))
    },
    batch: {
      title: 'Batch Coach',
      icon: Brain,
      items: achievements.filter(a => a.name.includes('Batch') || a.name.includes('Roster') || a.name.includes('Sharp') || a.name.includes('Elite'))
    },
    platform: {
      title: 'Platform Integration',
      icon: Target,
      items: achievements.filter(a => a.name.includes('Chess.com') || a.name.includes('Lichess'))
    }
  };

  // Calculate total achievements and completed achievements
  const totalAchievements = achievements.length;
  const completedAchievements = achievements.filter(a => a.completed).length;

  const AchievementModal = () => (
    <div className={`fixed inset-0 z-50 overflow-y-auto ${showModal ? 'block' : 'hidden'}`}>
      <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 transition-opacity" aria-hidden="true">
          <div className={`absolute inset-0 ${isDarkMode ? 'bg-gray-900' : 'bg-gray-500'} opacity-75`}></div>
        </div>

        <div className={`inline-block align-bottom rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-3xl sm:w-full ${
          isDarkMode ? 'bg-gray-800' : 'bg-white'
        }`}>
          <div className="px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div className="sm:flex sm:items-start">
              <div className="mt-3 text-center sm:mt-0 sm:text-left w-full">
                <div className="flex justify-between items-center mb-4 gap-2">
                  <div className="min-w-0">
                    <h3 className={`text-lg leading-6 font-medium truncate ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                      {selectedCategory ? categories[selectedCategory].title : 'All Achievements'}
                    </h3>
                    {selectedCategory ? (
                      <p className={`text-sm mt-0.5 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                        {categories[selectedCategory].items.length} achievements in this category
                      </p>
                    ) : null}
                  </div>
                  <button
                    onClick={() => {
                      setSelectedCategory(null);
                      setShowModal(false);
                    }}
                    className={`rounded-md p-2 ${
                      isDarkMode
                        ? 'hover:bg-gray-700 text-gray-400 hover:text-gray-300'
                        : 'hover:bg-gray-100 text-gray-500 hover:text-gray-600'
                    }`}
                  >
                    <XCircle className="h-5 w-5" />
                  </button>
                </div>

                <div className="mt-4 space-y-4">
                  {selectedCategory ? (
                    <>
                      <button
                        type="button"
                        onClick={() => setSelectedCategory(null)}
                        className={`w-full inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors ${
                          isDarkMode
                            ? 'bg-gray-700 hover:bg-gray-600 text-white'
                            : 'bg-gray-100 hover:bg-gray-200 text-gray-900'
                        }`}
                      >
                        <ChevronLeft className="h-4 w-4" />
                        Back to all achievements
                      </button>
                      {categories[selectedCategory].items.map((achievement, index) => (
                      <div
                        key={index}
                        className={`p-4 rounded-lg ${
                          isDarkMode
                            ? achievement.completed ? 'bg-gray-700' : 'bg-gray-750'
                            : achievement.completed ? 'bg-gray-50' : 'bg-gray-100'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg ${
                            achievement.completed
                              ? isDarkMode ? 'bg-green-900/30' : 'bg-green-100'
                              : isDarkMode ? 'bg-gray-600' : 'bg-gray-200'
                          }`}>
                            {achievement.completed ? (
                              <Trophy className={`h-5 w-5 ${isDarkMode ? 'text-green-400' : 'text-green-600'}`} />
                            ) : (
                              <Lock className={`h-5 w-5 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`} />
                            )}
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center justify-between">
                              <h4 className={`font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                                {achievement.name}
                              </h4>
                              <span className={`text-sm ${
                                isDarkMode ? 'text-gray-400' : 'text-gray-500'
                              }`}>
                                {Math.round((achievement.progress / achievement.target) * 100)}%
                              </span>
                            </div>
                            <p className={`text-sm mt-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                              {achievement.description}
                            </p>
                            <div className="w-full bg-gray-200 dark:bg-gray-600 h-1.5 rounded-full mt-2">
                              <div
                                className="bg-indigo-500 h-1.5 rounded-full transition-all duration-300"
                                style={{ width: `${(achievement.progress / achievement.target) * 100}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                    </>
                  ) : (
                    Object.entries(categories).map(([key, category]) => (
                      <button
                        key={key}
                        onClick={() => setSelectedCategory(key)}
                        className={`w-full p-4 rounded-lg text-left transition-all duration-200 ${
                          isDarkMode
                            ? 'hover:bg-gray-700'
                            : 'hover:bg-gray-50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <category.icon className={`h-5 w-5 ${
                              isDarkMode ? 'text-gray-400' : 'text-gray-500'
                            }`} />
                            <div>
                              <h4 className={`font-medium ${
                                isDarkMode ? 'text-white' : 'text-gray-900'
                              }`}>
                                {category.title}
                              </h4>
                              <p className={`text-sm ${
                                isDarkMode ? 'text-gray-400' : 'text-gray-500'
                              }`}>
                                {category.items.filter(a => a.completed).length} / {category.items.length} completed
                              </p>
                            </div>
                          </div>
                          <ChevronRight className={`h-5 w-5 ${
                            isDarkMode ? 'text-gray-400' : 'text-gray-500'
                          }`} />
                        </div>
                      </button>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className={`p-6 rounded-xl ${
      isDarkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'
    } shadow-lg`}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className={`text-lg font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Achievements
          </h3>
          <p className={`text-sm mt-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            {completedAchievements} of {totalAchievements} completed
          </p>
        </div>
        <button
          onClick={() => {
            setSelectedCategory(null);
            setShowModal(true);
          }}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            isDarkMode
              ? 'bg-gray-700 hover:bg-gray-600 text-white'
              : 'bg-gray-100 hover:bg-gray-200 text-gray-900'
          }`}
        >
          View All
        </button>
      </div>

      {/* Progress Overview */}
      <div className="mb-4">
        <div className="w-full bg-gray-200 dark:bg-gray-700 h-2 rounded-full">
          <div
            className="bg-indigo-500 h-2 rounded-full transition-all duration-300"
            style={{ width: `${(completedAchievements / totalAchievements) * 100}%` }}
          />
        </div>
      </div>

      {/* Recent or Featured Achievements */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {Object.entries(categories).slice(0, 4).map(([key, category]) => {
          const completed = category.items.filter(a => a.completed).length;
          const total = category.items.length;
          return (
            <button
              key={key}
              onClick={() => {
                setSelectedCategory(key);
                setShowModal(true);
              }}
              className={`p-4 rounded-lg text-left transition-all duration-200 hover:scale-[1.02] ${
                isDarkMode ? 'bg-gray-700 hover:bg-gray-650' : 'bg-gray-50 hover:bg-gray-100'
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <div className={`p-2 rounded-lg ${
                  isDarkMode ? 'bg-gray-600' : 'bg-gray-200'
                }`}>
                  <category.icon className={`h-5 w-5 ${
                    isDarkMode ? 'text-gray-300' : 'text-gray-600'
                  }`} />
                </div>
                <div>
                  <h4 className={`font-medium ${
                    isDarkMode ? 'text-white' : 'text-gray-900'
                  }`}>
                    {category.title}
                  </h4>
                  <p className={`text-sm ${
                    isDarkMode ? 'text-gray-400' : 'text-gray-500'
                  }`}>
                    {completed} / {total}
                  </p>
                </div>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-600 h-1.5 rounded-full">
                <div
                  className="bg-indigo-500 h-1.5 rounded-full transition-all duration-300"
                  style={{ width: `${(completed / total) * 100}%` }}
                />
              </div>
            </button>
          );
        })}
      </div>

      {/* Achievement Modal */}
      <AchievementModal />
    </div>
  );
};

const PerformanceStats = ({ stats, isDarkMode }) => {
  return (
    <div className={`p-6 rounded-xl ${
      isDarkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'
    } shadow-lg`}>
      <h3 className={`text-lg font-medium mb-4 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
        Performance Statistics
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(stats).map(([timeControl, data]) => (
          <div key={timeControl} className={`p-4 rounded-lg ${
            isDarkMode ? 'bg-gray-700' : 'bg-gray-50'
          }`}>
            <h4 className={`text-sm font-medium mb-2 ${isDarkMode ? 'text-gray-200' : 'text-gray-700'}`}>
              {timeControl.charAt(0).toUpperCase() + timeControl.slice(1)}
            </h4>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className={isDarkMode ? 'text-gray-400' : 'text-gray-600'}>Games Played</span>
                <span className={isDarkMode ? 'text-gray-200' : 'text-gray-800'}>{data.games}</span>
              </div>
              <div className="flex justify-between">
                <span className={isDarkMode ? 'text-gray-400' : 'text-gray-600'}>Win Rate</span>
                <span className={isDarkMode ? 'text-gray-200' : 'text-gray-800'}>{data.winRate}%</span>
              </div>
              {/*
              <div className="flex justify-between">
                <span className={isDarkMode ? 'text-gray-400' : 'text-gray-600'}>Average Rating</span>
                <span className={isDarkMode ? 'text-gray-200' : 'text-gray-800'}>{data.avgRating}</span>
              </div>
              <div className="flex justify-between">
                <span className={isDarkMode ? 'text-gray-400' : 'text-gray-600'}>Peak Rating</span>
                <span className={isDarkMode ? 'text-gray-200' : 'text-gray-800'}>{data.peakRating}</span>
              </div>
              */}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const Profile = () => {
  const { isDarkMode } = useTheme();
  const [profileData, setProfileData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [performanceStats, setPerformanceStats] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(Date.now());

  useEffect(() => {
    loadProfileData();
  }, [lastUpdate]);

  const loadProfileData = async () => {
    try {
      setLoading(true);
      const data = await fetchProfileData();
      setProfileData(data);

      // Format rating history data
      // Format performance stats with defaults
      if (data.performance_stats) {
        setPerformanceStats(data.performance_stats);
      } else {
        // Set default performance stats
        setPerformanceStats({
          bullet: { games: 0, winRate: 0, drawRate: 0, lossRate: 0 },
          blitz: { games: 0, winRate: 0, drawRate: 0, lossRate: 0 },
          rapid: { games: 0, winRate: 0, drawRate: 0, lossRate: 0 },
          classical: { games: 0, winRate: 0, drawRate: 0, lossRate: 0 }
        });
      }
    } catch (error) {
      console.error('Error loading profile data:', error);
      setError('Failed to load profile data');
      toast.error('Failed to load profile data');
    } finally {
      setLoading(false);
    }
  };

  const refreshProfileData = () => {
    setLastUpdate(Date.now());
  };

  useEffect(() => {
    const handleGameImported = () => {
      refreshProfileData();
    };

    window.addEventListener('game-imported', handleGameImported);
    return () => {
      window.removeEventListener('game-imported', handleGameImported);
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
            onClick={loadProfileData}
            className="mt-4 w-full px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!profileData) {
    return null;
  }

  // Safe access to time control distribution with defaults
  const defaultDistribution = { bullet: 0, blitz: 0, rapid: 0, classical: 0 };
  const timeControlDistribution = profileData.time_control_distribution || defaultDistribution;

  const timeControlData = [
    { label: 'Bullet', value: timeControlDistribution.bullet || 0 },
    { label: 'Blitz', value: timeControlDistribution.blitz || 0 },
    { label: 'Rapid', value: timeControlDistribution.rapid || 0 },
    { label: 'Classical', value: timeControlDistribution.classical || 0 }
  ];

  return (
    <div className={`min-h-screen ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Profile Header */}
        <div className={`mb-8 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
          <h1 className="text-3xl font-bold">Profile Overview</h1>
          <p className={`mt-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            View your chess statistics and progress
          </p>
        </div>

        {/* Commenting out Ratings Section as it's not supported yet */}
        {/*
        <div className="mb-8">
          <RatingsSection ratings={profileData.current_ratings} />
        </div>
        */}

        {/* Rating History Chart */}
        {/*
        <div className="mb-8">
          <RatingChart ratingHistory={ratingHistory} isDarkMode={isDarkMode} />
        </div>
        */}

        {/* Performance Statistics */}
        <div className="mb-8">
          <PerformanceStats stats={performanceStats} isDarkMode={isDarkMode} />
        </div>

        {/* Statistics Section */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          <StatCard
            title="Total Games"
            value={profileData.total_games || 0}
            icon={Layout}
            color="purple"
          />
          <StatCard
            title="Win Rate"
            value={`${profileData.win_rate || 0}%`}
            icon={Trophy}
            color="green"
          />
          <StatCard
            title="Credits"
            value={profileData.credits || 0}
            icon={Coins}
            color="yellow"
          />
        </div>

        {/* Time Control Distribution */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <ProgressChart
            data={timeControlData}
            title="Time Control Distribution"
          />

          {/* Achievements Section */}
          <div className={`p-6 rounded-xl ${
            isDarkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'
          } shadow-lg`}>
            <h3 className={`text-lg font-semibold mb-4 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Achievements
            </h3>
              <div className="space-y-4">
                <AchievementsSection achievements={profileData.achievements || []} />
              </div>
            </div>
          </div>

        <ProfileCoachSettings isDarkMode={isDarkMode} />

        <ProfileLinkedAccounts
          chesscomUsername={profileData.chesscom_username}
          lichessUsername={profileData.lichess_username}
          isDarkMode={isDarkMode}
          onUpdated={loadProfileData}
        />
      </div>
    </div>
  );
};

export default Profile;
