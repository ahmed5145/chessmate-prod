import React, { useState } from 'react';
import { CheckCircle, ExternalLink, Link2, Loader2, Unlink, XCircle } from 'lucide-react';
import { toast } from 'react-hot-toast';
import api from '../../services/api';

const PLATFORMS = [
  {
    key: 'chess.com',
    label: 'Chess.com',
    inputKey: 'chesscom',
    placeholder: 'Chess.com username',
    profileUrl: (username) => `https://www.chess.com/member/${encodeURIComponent(username)}`,
    accent: {
      connected: 'border-[#81b64c]/50 bg-[#81b64c]/10',
      idle: 'border-gray-200 dark:border-gray-700',
      badge: 'bg-[#81b64c] text-white',
      text: 'text-[#5a8f35] dark:text-[#9fd36f]',
    },
  },
  {
    key: 'lichess',
    label: 'Lichess',
    inputKey: 'lichess',
    placeholder: 'Lichess username',
    profileUrl: (username) => `https://lichess.org/@/${encodeURIComponent(username)}`,
    accent: {
      connected: 'border-gray-800/30 bg-gray-900/5 dark:border-gray-500/40 dark:bg-white/5',
      idle: 'border-gray-200 dark:border-gray-700',
      badge: 'bg-gray-900 text-white dark:bg-gray-100 dark:text-gray-900',
      text: 'text-gray-700 dark:text-gray-200',
    },
  },
];

const ProfileLinkedAccounts = ({
  chesscomUsername,
  lichessUsername,
  isDarkMode,
  onUpdated,
}) => {
  const [drafts, setDrafts] = useState({ chesscom: '', lichess: '' });
  const [busyPlatform, setBusyPlatform] = useState(null);

  const getUsername = (platformKey) => (
    platformKey === 'chess.com' ? chesscomUsername : lichessUsername
  );

  const handleLink = async (platform) => {
    const username = drafts[platform.inputKey]?.trim();
    if (!username) {
      toast.error('Enter a username first');
      return;
    }

    setBusyPlatform(platform.key);
    try {
      const payload = platform.key === 'chess.com'
        ? { chess_com_username: username }
        : { lichess_username: username };

      await api.patch('/api/v1/profile/update/', payload);
      setDrafts((prev) => ({ ...prev, [platform.inputKey]: '' }));
      await onUpdated?.();
      toast.success(`${platform.label} linked`);
    } catch (error) {
      toast.error(error.response?.data?.message || error.message || 'Failed to link account');
    } finally {
      setBusyPlatform(null);
    }
  };

  const handleUnlink = async (platform) => {
    setBusyPlatform(platform.key);
    try {
      const payload = platform.key === 'chess.com'
        ? { chess_com_username: '' }
        : { lichess_username: '' };

      await api.patch('/api/v1/profile/update/', payload);
      await onUpdated?.();
      toast.success(`${platform.label} unlinked`);
    } catch (error) {
      toast.error(error.response?.data?.message || error.message || 'Failed to unlink account');
    } finally {
      setBusyPlatform(null);
    }
  };

  return (
    <div className={`p-6 rounded-xl ${
      isDarkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'
    } shadow-lg mb-8`}>
      <div className="flex items-start gap-3 mb-5">
        <div className={`p-2 rounded-lg ${isDarkMode ? 'bg-indigo-900/40' : 'bg-indigo-50'}`}>
          <Link2 className={`h-5 w-5 ${isDarkMode ? 'text-indigo-300' : 'text-indigo-600'}`} />
        </div>
        <div>
          <h3 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Linked accounts
          </h3>
          <p className={`text-sm mt-0.5 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            Connect Chess.com and Lichess so game imports use the correct usernames.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {PLATFORMS.map((platform) => {
          const username = getUsername(platform.key);
          const connected = Boolean(username);
          const isBusy = busyPlatform === platform.key;

          return (
            <div
              key={platform.key}
              className={`rounded-xl border p-4 flex flex-col gap-3 transition-colors ${
                connected ? platform.accent.connected : platform.accent.idle
              } ${isDarkMode && !connected ? 'bg-gray-900/30' : !connected ? 'bg-gray-50/80' : ''}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <span className={`inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-xs font-bold ${platform.accent.badge}`}>
                    {platform.label.slice(0, 2).toUpperCase()}
                  </span>
                  <div className="min-w-0">
                    <p className={`font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                      {platform.label}
                    </p>
                    <p className={`text-xs mt-0.5 ${
                      connected
                        ? platform.accent.text
                        : isDarkMode ? 'text-gray-500' : 'text-gray-500'
                    }`}>
                      {connected ? 'Connected for imports' : 'Not connected'}
                    </p>
                  </div>
                </div>
                {connected ? (
                  <CheckCircle className="h-5 w-5 text-green-500 shrink-0" aria-hidden />
                ) : (
                  <XCircle className={`h-5 w-5 shrink-0 ${isDarkMode ? 'text-gray-600' : 'text-gray-300'}`} aria-hidden />
                )}
              </div>

              {connected ? (
                <>
                  <p className={`text-sm font-medium truncate ${isDarkMode ? 'text-gray-100' : 'text-gray-800'}`}>
                    @{username}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <a
                      href={platform.profileUrl(username)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={`inline-flex items-center gap-1.5 text-sm font-medium rounded-md px-3 py-1.5 border ${
                        isDarkMode
                          ? 'border-gray-600 text-gray-200 hover:bg-gray-700/60'
                          : 'border-gray-300 text-gray-700 hover:bg-white'
                      }`}
                    >
                      View profile
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                    <button
                      type="button"
                      onClick={() => handleUnlink(platform)}
                      disabled={isBusy}
                      className={`inline-flex items-center gap-1.5 text-sm font-medium rounded-md px-3 py-1.5 ${
                        isDarkMode
                          ? 'text-red-400 hover:bg-red-950/30'
                          : 'text-red-600 hover:bg-red-50'
                      } disabled:opacity-50`}
                    >
                      {isBusy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Unlink className="h-3.5 w-3.5" />}
                      Unlink
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <input
                    type="text"
                    placeholder={platform.placeholder}
                    value={drafts[platform.inputKey] || ''}
                    onChange={(e) => setDrafts((prev) => ({ ...prev, [platform.inputKey]: e.target.value }))}
                    autoComplete="off"
                    autoCapitalize="none"
                    spellCheck="false"
                    disabled={isBusy}
                    className={`block w-full px-3 py-2 text-sm rounded-md shadow-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-60 ${
                      isDarkMode
                        ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
                        : 'border border-gray-300 text-gray-900 placeholder-gray-500'
                    }`}
                  />
                  <button
                    type="button"
                    onClick={() => handleLink(platform)}
                    disabled={isBusy}
                    className="self-start inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Link2 className="h-4 w-4" />}
                    Link account
                  </button>
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ProfileLinkedAccounts;
