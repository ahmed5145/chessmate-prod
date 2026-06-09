/** Dashboard stage + section visibility — coach-home information architecture. */

import { resolveOneThingToday } from './oneThingToday';
import { resolveNextAction, shouldShowFocusCard } from './dashboardFocus';

export const DASHBOARD_STAGES = {
  NEW: 'new',
  ONBOARDING: 'onboarding',
  COACH_READY: 'coach_ready',
  COACH_ACTIVE: 'coach_active',
};

const getUserPreferences = (user) => user?.preferences || user?.profile?.preferences || {};

export const resolveDashboardStage = (dashboardData = {}) => {
  const totalGames = Number(dashboardData.total_games) || 0;
  const hasBatch = Boolean(dashboardData.latest_batch_coach?.batch_id);
  const batchesCompleted = Number(dashboardData.batches_completed) || 0;

  if (totalGames === 0) {
    return DASHBOARD_STAGES.NEW;
  }
  if (!hasBatch && batchesCompleted === 0) {
    return totalGames < 5 ? DASHBOARD_STAGES.ONBOARDING : DASHBOARD_STAGES.COACH_READY;
  }
  return DASHBOARD_STAGES.COACH_ACTIVE;
};

export const resolveDashboardPageCopy = (stage, username = 'there') => {
  const copy = {
    [DASHBOARD_STAGES.NEW]: {
      eyebrow: 'Coach home',
      subtitle: 'Import games from Chess.com or Lichess to unlock your first coach report.',
    },
    [DASHBOARD_STAGES.ONBOARDING]: {
      eyebrow: 'Coach home',
      subtitle: 'Import a few more games — Batch Coach needs at least 5 to find cross-game patterns.',
    },
    [DASHBOARD_STAGES.COACH_READY]: {
      eyebrow: 'Coach home',
      subtitle: 'You are ready. Run Batch Coach on 5–30 games for a personalized coaching session.',
    },
    [DASHBOARD_STAGES.COACH_ACTIVE]: {
      eyebrow: 'Coach home',
      subtitle: `Welcome back, ${username}. Here is what to focus on today.`,
    },
  };
  return copy[stage] || copy[DASHBOARD_STAGES.NEW];
};

export const resolveCoachSectionCopy = (stage) => {
  if (stage === DASHBOARD_STAGES.COACH_ACTIVE) {
    return {
      title: "Today's coaching",
      description: 'Priorities and drills from your latest coach report — your daily habit loop.',
    };
  }
  if (stage === DASHBOARD_STAGES.COACH_READY) {
    return {
      title: 'Next step',
      description: 'Run Batch Coach once to unlock your inbox, fix-rate tracking, and daily drills.',
    };
  }
  return null;
};

export const isOneThingRedundantWithHero = (dashboardData = {}) => {
  const oneThing = resolveOneThingToday(dashboardData);
  if (!oneThing?.ctaTo) {
    return false;
  }
  const hero = resolveNextAction(dashboardData);
  return oneThing.ctaTo === hero.ctaTo;
};

export const resolveDashboardSections = (dashboardData = {}, user = null) => {
  const stage = resolveDashboardStage(dashboardData);
  const welcomePending = user && getUserPreferences(user).welcome_guide_seen !== true;
  const oneThing = resolveOneThingToday(dashboardData);
  const hasProgress = Boolean(dashboardData.fix_rate?.show || dashboardData.phase_heatmap?.show);
  const showFocus = shouldShowFocusCard(dashboardData, user);
  const coachSection = resolveCoachSectionCopy(stage);
  const oneThingRedundant = isOneThingRedundantWithHero(dashboardData);

  return {
    stage,
    showSinceLastVisit: stage === DASHBOARD_STAGES.COACH_ACTIVE
      && Boolean(dashboardData.sinceLastVisit?.showBanner),
    showOneThingToday: Boolean(oneThing)
      && stage === DASHBOARD_STAGES.COACH_ACTIVE
      && !oneThingRedundant,
    showCoachSection: !welcomePending && Boolean(coachSection),
    coachSection,
    showProgressSection: stage === DASHBOARD_STAGES.COACH_ACTIVE && hasProgress,
    showFocusSection: showFocus,
    showRecentGames: true,
    showMoreStats: stage !== DASHBOARD_STAGES.NEW,
  };
};
