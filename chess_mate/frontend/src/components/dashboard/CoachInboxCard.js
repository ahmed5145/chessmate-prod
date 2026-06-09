import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Inbox } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { trackMarketingEvent } from '../../utils/marketingAnalytics';

const CoachInboxCard = ({ priorityInbox }) => {
  const { isDarkMode } = useTheme();
  const pendingItems = priorityInbox?.pending_items || [];
  const pendingCount = priorityInbox?.pending_count ?? pendingItems.length;

  if (pendingCount === 0) {
    return (
      <section
        className={`mb-8 rounded-xl border px-5 py-4 ${
          isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
        }`}
      >
        <div className="flex items-center gap-2">
          <Inbox className={`h-5 w-5 ${isDarkMode ? 'text-indigo-300' : 'text-indigo-600'}`} />
          <h2 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Coach inbox
          </h2>
        </div>
        <p className={`mt-2 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          No priorities waiting. Run a batch to get your top 3 coaching actions.
        </p>
        <Link
          to={priorityInbox?.empty_state_cta || '/batch-analysis'}
          className={`mt-3 inline-flex items-center gap-1 text-sm font-semibold ${
            isDarkMode ? 'text-indigo-300 hover:text-indigo-200' : 'text-indigo-600 hover:text-indigo-700'
          }`}
        >
          {priorityInbox?.empty_state_label || 'Start Batch Coach'}
          <ArrowRight className="h-4 w-4" />
        </Link>
      </section>
    );
  }

  return (
    <section
      className={`mb-8 rounded-xl border overflow-hidden ${
        isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
      } shadow-lg`}
    >
      <div className={`flex items-center justify-between px-5 py-4 border-b ${
        isDarkMode ? 'border-gray-700' : 'border-gray-100'
      }`}>
        <div className="flex items-center gap-2">
          <Inbox className={`h-5 w-5 ${isDarkMode ? 'text-indigo-300' : 'text-indigo-600'}`} />
          <h2 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
            Coach inbox
          </h2>
        </div>
        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
          isDarkMode ? 'bg-indigo-900/50 text-indigo-200' : 'bg-indigo-100 text-indigo-800'
        }`}>
          {pendingCount} pending
        </span>
      </div>

      <ul className={`divide-y ${isDarkMode ? 'divide-gray-700' : 'divide-gray-100'}`}>
        {pendingItems.map((item) => (
          <li key={item.id || `${item.batch_id}-${item.priority_index}`}>
            <Link
              to={item.href || `/batch-report/${item.batch_id}`}
              onClick={() => trackMarketingEvent('priority_inbox_open', {
                batch_id: item.batch_id,
                priority_index: item.priority_index,
                surface: 'dashboard',
              })}
              className={`flex items-start justify-between gap-3 px-5 py-4 transition-colors ${
                isDarkMode ? 'hover:bg-gray-700/80' : 'hover:bg-gray-50'
              }`}
            >
              <div className="min-w-0">
                <p className={`text-xs font-semibold uppercase tracking-wide ${
                  isDarkMode ? 'text-indigo-300' : 'text-indigo-600'
                }`}>
                  Priority #{item.priority_index}
                </p>
                <p className={`mt-0.5 text-sm font-medium ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                  {item.title}
                </p>
                {item.drill ? (
                  <p className={`mt-1 text-xs line-clamp-2 ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    {item.drill}
                  </p>
                ) : null}
              </div>
              <ArrowRight className={`h-4 w-4 shrink-0 mt-1 ${
                isDarkMode ? 'text-gray-400' : 'text-gray-500'
              }`} />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
};

export default CoachInboxCard;
