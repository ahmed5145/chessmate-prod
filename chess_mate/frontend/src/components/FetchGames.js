import React, { useState, useContext } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { UserContext } from '../contexts/UserContext';
import { toast } from 'react-hot-toast';


// API Configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://3.133.97.72/api';


const FetchGames = () => {
  const [platform, setPlatform] = useState('chess.com');
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [gameMode, setGameMode] = useState('all');
  const [numGames, setNumGames] = useState(10);
  const { credits } = useContext(UserContext);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const accessToken = localStorage.getItem('tokens') ? JSON.parse(localStorage.getItem('tokens')).access : null;
      if (!accessToken) {
        toast.error('Please log in to fetch games');
        return;
      }

      // Check if user has enough credits
      if (credits < numGames) {
        toast.error(`Not enough credits. Required: ${numGames}, Available: ${credits}`);
        return;
      }

      const response = await fetch(`${API_BASE_URL}/fetch-games/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({
          platform,
          username,
          game_mode: gameMode,
          num_games: numGames
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to fetch games');
      }

      toast.success(data.message);
      navigate('/games');
    } catch (error) {
      console.error('Error fetching games:', error);
      toast.error(error.message || 'Failed to fetch games');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="max-w-3xl mx-auto">
        <div className="bg-white shadow sm:rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg font-medium leading-6 text-gray-900">Import Chess Games</h3>
            <div className="mt-2 max-w-xl text-sm text-gray-500">
              <p>Enter your chess platform username to import your games for analysis.</p>
              <div className={`mt-4 p-4 rounded-lg ${credits < 5 ? 'bg-yellow-50 border border-yellow-200' : ''}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className={`font-medium ${credits < 5 ? 'text-yellow-800' : 'text-gray-900'}`}>
                      Available Credits: {credits}
                    </p>
                    <p className="mt-1 text-sm text-gray-500">Cost: 1 credit per game</p>
                  </div>
                  {credits < 5 && (
                    <Link
                      to="/credits"
                      className="ml-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-yellow-600 hover:bg-yellow-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500"
                    >
                      Buy Credits
                    </Link>
                  )}
                </div>
                {credits < 5 && (
                  <p className="mt-2 text-sm text-yellow-700">
                    Your credits are running low. Consider purchasing more credits to continue analyzing games.
                  </p>
                )}
              </div>
            </div>
            <form onSubmit={handleSubmit} className="mt-5">
              <div className="space-y-4">
                <div>
                  <label htmlFor="platform" className="block text-sm font-medium text-gray-700">
                    Platform
                  </label>
                  <select
                    id="platform"
                    value={platform}
                    onChange={(e) => setPlatform(e.target.value)}
                    className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
                  >
                    <option value="chess.com">Chess.com</option>
                    <option value="lichess">Lichess</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="username" className="block text-sm font-medium text-gray-700">
                    Username
                  </label>
                  <input
                    type="text"
                    id="username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                    placeholder="Enter your username"
                    required
                  />
                </div>

                <div>
                  <label htmlFor="gameMode" className="block text-sm font-medium text-gray-700">
                    Game Mode
                  </label>
                  <select
                    id="gameMode"
                    value={gameMode}
                    onChange={(e) => setGameMode(e.target.value)}
                    className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
                  >
                    <option value="all">All Game Types</option>
                    <option value="bullet">Bullet</option>
                    <option value="blitz">Blitz</option>
                    <option value="rapid">Rapid</option>
                    <option value="classical">Classical</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="numGames" className="block text-sm font-medium text-gray-700">
                    Number of Games
                  </label>
                  <div className="mt-1 relative rounded-md shadow-sm">
                    <input
                      type="number"
                      id="numGames"
                      value={numGames}
                      onChange={(e) => setNumGames(Math.max(1, Math.min(100, parseInt(e.target.value) || 1)))}
                      className="block w-full pr-12 border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                      placeholder="10"
                      min="1"
                      max="100"
                      required
                    />
                    <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                      <span className="text-gray-500 sm:text-sm">games</span>
                    </div>
                  </div>
                  <p className="mt-1 text-sm text-gray-500">Total cost: {numGames} credits</p>
                </div>
              </div>

              <div className="mt-5">
                <button
                  type="submit"
                  disabled={loading || !username}
                  className={`inline-flex items-center justify-center w-full px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 ${
                    (loading || !username) && 'opacity-50 cursor-not-allowed'
                  }`}
                >
                  {loading ? (
                    <>
                      <div className="spinner-small mr-2" />
                      Fetching Games...
                    </>
                  ) : (
                    'Import Games'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FetchGames;
