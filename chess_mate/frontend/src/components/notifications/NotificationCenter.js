import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Bell } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import {
  fetchNotifications,
  patchNotifications,
} from '../../services/apiRequests';

const POLL_MS = 60000;

const formatRelativeTime = (iso) => {
  if (!iso) return '';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const deltaMinutes = Math.floor((Date.now() - then) / 60000);
  if (deltaMinutes < 1) return 'Just now';
  if (deltaMinutes < 60) return `${deltaMinutes}m ago`;
  const deltaHours = Math.floor(deltaMinutes / 60);
  if (deltaHours < 24) return `${deltaHours}h ago`;
  const deltaDays = Math.floor(deltaHours / 24);
  return `${deltaDays}d ago`;
};

const NotificationCenter = ({ className = '' }) => {
  const { isDarkMode } = useTheme();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [payload, setPayload] = useState({ unread_count: 0, notifications: [] });

  const load = useCallback(async () => {
    if (!localStorage.getItem('tokens')) {
      return;
    }
    setLoading(true);
    try {
      const data = await fetchNotifications();
      setPayload(data || { unread_count: 0, notifications: [] });
    } catch (error) {
      console.error('Failed to load notifications', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, POLL_MS);
    return () => window.clearInterval(timer);
  }, [load]);

  useEffect(() => {
    if (open) {
      load();
    }
  }, [open, load]);

  const handleOpenItem = async (notification) => {
    if (!notification?.href) {
      return;
    }
    if (!notification.is_read && notification.id != null) {
      try {
        const data = await patchNotifications({ ids: [notification.id] });
        setPayload(data);
      } catch (error) {
        console.error('Failed to mark notification read', error);
      }
    }
    setOpen(false);
    navigate(notification.href);
  };

  const handleMarkAllRead = async () => {
    try {
      const data = await patchNotifications({ markAll: true });
      setPayload(data);
    } catch (error) {
      console.error('Failed to mark all notifications read', error);
    }
  };

  const unreadCount = payload.unread_count || 0;
  const items = (payload.notifications || []).slice(0, 8);

  return (
    <div className={`relative ${className}`}>
      <button
        type="button"
        aria-label="Notifications"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className={`relative inline-flex items-center justify-center p-2 rounded-lg transition-colors duration-200 h-10 w-10
          ${isDarkMode
            ? 'bg-gray-800 text-white hover:bg-gray-700'
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
      >
        <Bell size={20} />
        {unreadCount > 0 ? (
          <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        ) : null}
      </button>

      {open ? (
        <>
          <button
            type="button"
            aria-label="Close notifications"
            className="fixed inset-0 z-40 cursor-default"
            onClick={() => setOpen(false)}
          />
          <div
            className={`absolute right-0 mt-2 w-80 max-w-[calc(100vw-2rem)] z-50 rounded-xl border shadow-xl overflow-hidden
              ${isDarkMode ? 'bg-gray-900 border-gray-700' : 'bg-white border-gray-200'}`}
          >
            <div className={`flex items-center justify-between px-4 py-3 border-b ${
              isDarkMode ? 'border-gray-700' : 'border-gray-100'
            }`}>
              <p className={`text-sm font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                Notifications
              </p>
              {unreadCount > 0 ? (
                <button
                  type="button"
                  onClick={handleMarkAllRead}
                  className={`text-xs font-semibold ${
                    isDarkMode ? 'text-indigo-300 hover:text-indigo-200' : 'text-indigo-600 hover:text-indigo-700'
                  }`}
                >
                  Mark all read
                </button>
              ) : null}
            </div>

            <div className="max-h-80 overflow-y-auto">
              {loading && items.length === 0 ? (
                <p className={`px-4 py-6 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                  Loading…
                </p>
              ) : null}
              {!loading && items.length === 0 ? (
                <p className={`px-4 py-6 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                  You&apos;re all caught up.
                </p>
              ) : null}
              {items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleOpenItem(item)}
                  className={`w-full text-left px-4 py-3 border-b transition-colors ${
                    isDarkMode
                      ? 'border-gray-800 hover:bg-gray-800'
                      : 'border-gray-50 hover:bg-gray-50'
                  } ${item.is_read ? 'opacity-70' : ''}`}
                >
                  <p className={`text-sm font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                    {item.title}
                  </p>
                  {item.body ? (
                    <p className={`mt-0.5 text-xs line-clamp-2 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      {item.body}
                    </p>
                  ) : null}
                  <p className={`mt-1 text-[11px] ${isDarkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                    {formatRelativeTime(item.created_at)}
                  </p>
                </button>
              ))}
            </div>

            <div className={`px-4 py-3 border-t ${isDarkMode ? 'border-gray-700 bg-gray-900' : 'border-gray-100 bg-gray-50'}`}>
              <Link
                to="/dashboard#notifications"
                onClick={() => setOpen(false)}
                className={`text-xs font-semibold ${
                  isDarkMode ? 'text-indigo-300 hover:text-indigo-200' : 'text-indigo-600 hover:text-indigo-700'
                }`}
              >
                View all on dashboard
              </Link>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
};

export default NotificationCenter;
