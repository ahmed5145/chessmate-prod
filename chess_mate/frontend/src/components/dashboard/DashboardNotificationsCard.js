import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import {
  fetchNotifications,
  patchNotifications,
} from '../../services/apiRequests';

const DashboardNotificationsCard = () => {
  const { isDarkMode } = useTheme();
  const navigate = useNavigate();
  const [payload, setPayload] = useState({ unread_count: 0, notifications: [] });

  const load = useCallback(async () => {
    try {
      const data = await fetchNotifications();
      setPayload(data || { unread_count: 0, notifications: [] });
    } catch (error) {
      console.error('Failed to load dashboard notifications', error);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const notifications = payload.notifications || [];
  if (notifications.length === 0) {
    return null;
  }

  const openNotification = async (item) => {
    if (!item?.href) return;
    if (!item.is_read && item.id != null) {
      try {
        await patchNotifications({ ids: [item.id] });
      } catch (error) {
        console.error('Failed to mark notification read', error);
      }
    }
    navigate(item.href);
  };

  return (
    <section
      id="notifications"
      className={`mb-8 rounded-xl border overflow-hidden scroll-mt-24 ${
        isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
      } shadow-lg`}
    >
      <div className={`flex items-center justify-between px-5 py-4 border-b ${
        isDarkMode ? 'border-gray-700' : 'border-gray-100'
      }`}>
        <div className="flex items-center gap-2">
          <Bell className={`h-5 w-5 ${isDarkMode ? 'text-indigo-300' : 'text-indigo-600'}`} />
          <h2 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Notifications
          </h2>
        </div>
        {payload.unread_count > 0 ? (
          <button
            type="button"
            onClick={async () => {
              const data = await patchNotifications({ markAll: true });
              setPayload(data);
            }}
            className={`text-xs font-semibold ${
              isDarkMode ? 'text-indigo-300 hover:text-indigo-200' : 'text-indigo-600 hover:text-indigo-700'
            }`}
          >
            Mark all read
          </button>
        ) : null}
      </div>
      <ul>
        {notifications.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              onClick={() => openNotification(item)}
              className={`w-full text-left px-5 py-4 border-b transition-colors ${
                isDarkMode
                  ? 'border-gray-700 hover:bg-gray-750'
                  : 'border-gray-100 hover:bg-gray-50'
              } ${item.is_read ? 'opacity-75' : ''}`}
            >
              <p className={`text-sm font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                {item.title}
              </p>
              {item.body ? (
                <p className={`mt-1 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  {item.body}
                </p>
              ) : null}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
};

export default DashboardNotificationsCard;
