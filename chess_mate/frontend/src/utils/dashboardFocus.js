/** Dashboard hero, focus insight, and metric helpers. */

const getUserPreferences = (user) => user?.preferences || user?.profile?.preferences || {};

const GENERIC_INSIGHT_PATTERNS = [
  /import and analyze games/i,
  /run batch coach or analyze/i,
  /unlock personalized/i,
  /unlock more personalized/i,
];

export const isGameRowAnalyzed = (game = {}) => {
  const status = String(game.analysis_status || game.status || '').toLowerCase();
  return status === 'analyzed' || status === 'completed' || !!game.analysis;
};

export const isGenericInsight = (text = '') => (
  GENERIC_INSIGHT_PATTERNS.some((pattern) => pattern.test(String(text)))
);

const mapServerNextAction = (action = {}) => ({
  title: action.title,
  description: action.description,
  ctaLabel: action.ctaLabel || action.cta_label,
  ctaTo: action.ctaTo || action.cta_to,
  secondaryLinks: action.secondaryLinks || action.secondary_links || [],
});

const mapServerFocusInsight = (focus = {}) => ({
  type: focus.type || 'success',
  text: focus.text,
  href: focus.href || null,
  actionLabel: focus.actionLabel || focus.action_label || null,
  meta: focus.meta || null,
});

export const resolveNextAction = (dashboardData = {}) => {
  if (dashboardData.nextAction?.ctaTo) {
    return mapServerNextAction(dashboardData.nextAction);
  }
  if (dashboardData.next_action?.cta_to) {
    return mapServerNextAction(dashboardData.next_action);
  }

  const totalGames = Number(dashboardData.total_games) || 0;
  const batchCoach = dashboardData.latest_batch_coach;
  const recentGames = Array.isArray(dashboardData.recent_games) ? dashboardData.recent_games : [];
  const firstUnanalyzed = recentGames.find((game) => !isGameRowAnalyzed(game));

  if (totalGames === 0) {
    return {
      title: 'Import games to get started',
      description: 'Pull games from Chess.com or Lichess to unlock analysis and coaching.',
      ctaLabel: 'Import games',
      ctaTo: '/fetch-games',
      secondaryLinks: [{ label: 'Credits & pricing', to: '/credits' }],
    };
  }

  if (batchCoach?.summary && batchCoach?.batch_id) {
    const summaryPreview = String(batchCoach.summary).trim();
    return {
      title: 'Pick up your latest coach report',
      description: summaryPreview.length > 180 ? `${summaryPreview.slice(0, 180)}…` : summaryPreview,
      ctaLabel: 'Open report',
      ctaTo: `/batch-report/${batchCoach.batch_id}`,
      secondaryLinks: [
        { label: 'Run new batch', to: '/batch-analysis' },
        { label: 'View games', to: '/games' },
      ],
    };
  }

  if (totalGames >= 5) {
    return {
      title: 'Run Batch Coach on your games',
      description: 'Batch Coach analyzes 5–30 imported games and finds cross-game patterns — no need to run single-game review first.',
      ctaLabel: 'Start Batch Coach',
      ctaTo: '/batch-analysis',
      secondaryLinks: [
        { label: 'View games', to: '/games' },
        ...(firstUnanalyzed?.id
          ? [{ label: 'Optional: deep review one game', to: `/game/${firstUnanalyzed.id}/analysis` }]
          : []),
      ],
    };
  }

  const remaining = 5 - totalGames;
  const tryGameLink = firstUnanalyzed?.id
    ? [{ label: 'Optional: try deep review', to: `/game/${firstUnanalyzed.id}/analysis` }]
    : [];

  if (totalGames > 0) {
    return {
      title: `Import ${remaining} more game${remaining === 1 ? '' : 's'} for Batch Coach`,
      description: 'Batch Coach needs at least 5 games. Optional: run a depth-20 review on one game (+1 credit).',
      ctaLabel: 'Import games',
      ctaTo: '/fetch-games',
      secondaryLinks: [
        { label: 'View games', to: '/games' },
        ...tryGameLink,
      ],
    };
  }

  return {
    title: 'Import games to get started',
    description: 'Pull games from Chess.com or Lichess to unlock Batch Coach.',
    ctaLabel: 'Import games',
    ctaTo: '/fetch-games',
    secondaryLinks: [{ label: 'Credits & pricing', to: '/credits' }],
  };
};

export const resolveFocusInsight = (dashboardData = {}) => {
  if (dashboardData.focusInsight?.text) {
    return mapServerFocusInsight(dashboardData.focusInsight);
  }
  if (dashboardData.focus_insight?.text) {
    return mapServerFocusInsight(dashboardData.focus_insight);
  }

  const batchCoach = dashboardData.latest_batch_coach;
  const insights = Array.isArray(dashboardData.insights) ? dashboardData.insights : [];
  const rawInsights = Array.isArray(dashboardData.analysis_insights) ? dashboardData.analysis_insights : [];
  const meaningful = insights.filter((item) => item?.text && !isGenericInsight(item.text));

  const priorityInsight = meaningful.find((item) => (
    /top focus|opening to review|weakest|priority/i.test(item.text)
  ));
  if (priorityInsight && batchCoach?.batch_id) {
    return {
      type: priorityInsight.type || 'warning',
      text: priorityInsight.text,
      href: `/batch-report/${batchCoach.batch_id}`,
      actionLabel: 'Open report',
    };
  }

  if (batchCoach?.summary) {
    return {
      type: 'success',
      text: String(batchCoach.summary).trim(),
      href: `/batch-report/${batchCoach.batch_id}`,
      actionLabel: 'Open full report',
      meta: [
        batchCoach.games_count ? `${batchCoach.games_count} games` : null,
        batchCoach.overall_accuracy_pct != null
          ? `${Number(batchCoach.overall_accuracy_pct).toFixed(1)}% accuracy`
          : null,
      ].filter(Boolean).join(' · '),
    };
  }

  const firstMeaningful = meaningful[0];
  if (firstMeaningful) {
    const linkedRaw = rawInsights.find((item) => item?.game_id);
    const href = linkedRaw?.game_id ? `/game/${linkedRaw.game_id}/analysis` : null;
    return {
      type: firstMeaningful.type || 'success',
      text: firstMeaningful.text,
      href,
      actionLabel: href ? 'View game' : null,
    };
  }

  const totalGames = Number(dashboardData.total_games) || 0;
  return {
    type: 'success',
    text: totalGames > 0
      ? 'Run Batch Coach to surface patterns across your games — or try an optional deep review on one game.'
      : 'Import games to unlock Batch Coach and personalized coaching.',
    href: totalGames > 0 ? '/games' : '/fetch-games',
    actionLabel: totalGames > 0 ? 'View games' : 'Import games',
  };
};

export const buildHeroMetrics = (dashboardData = {}) => {
  if (Array.isArray(dashboardData.heroMetrics) && dashboardData.heroMetrics.length > 0) {
    return dashboardData.heroMetrics;
  }
  if (Array.isArray(dashboardData.hero_metrics) && dashboardData.hero_metrics.length > 0) {
    return dashboardData.hero_metrics.map((metric) => ({
      label: metric.label,
      value: String(metric.value),
    }));
  }

  const totalGames = Number(dashboardData.total_games) || 0;
  const analyzedGames = Number(
    dashboardData.analyzed_games
    ?? dashboardData.game_stats?.analyzed_games
    ?? dashboardData.game_stats?.analyzed
  ) || 0;
  const metrics = [];

  if (totalGames > 0) {
    metrics.push({ label: 'Analyzed', value: `${analyzedGames} / ${totalGames}` });
  }

  const accuracy = Number(dashboardData.average_accuracy);
  if (analyzedGames >= 3 && accuracy > 0) {
    metrics.push({ label: 'Avg accuracy', value: `${accuracy}%` });
  }

  const winRate = Number(dashboardData.win_rate);
  if (totalGames >= 10 && winRate >= 0) {
    metrics.push({ label: 'Win rate', value: `${winRate}%` });
  }

  return metrics;
};

export const formatTimeControlLabel = (key = '') => (
  String(key).charAt(0).toUpperCase() + String(key).slice(1)
);

/** Hide focus card when it repeats the hero or welcome onboarding already covers it. */
export const shouldShowFocusCard = (dashboardData = {}, user = null) => {
  if (user && getUserPreferences(user).welcome_guide_seen !== true) {
    return false;
  }

  const actionType = dashboardData.nextAction?.type || dashboardData.next_action?.type;
  const focus = resolveFocusInsight(dashboardData);
  if (!focus?.text) {
    return false;
  }

  if (actionType === 'import_games') {
    return false;
  }

  if (isGenericInsight(focus.text)) {
    return false;
  }

  const action = resolveNextAction(dashboardData);
  if (actionType === 'open_batch_report') {
    const heroText = String(action.description || '').trim().toLowerCase();
    const focusText = String(focus.text || '').trim().toLowerCase();
    if (heroText && (focusText === heroText || heroText.startsWith(focusText.slice(0, 40)))) {
      return /top focus|opening to review|weakest|priority| vs /i.test(focus.text);
    }
  }

  return true;
};
