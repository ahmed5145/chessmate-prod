/** Canonical user-facing copy for the Batch Coach feature. */

export const BATCH_COACH = 'Batch Coach';
export const BATCH_COACH_REPORT = 'Batch Coach report';
export const BATCH_COACH_REPORTS = 'Batch Coach reports';
export const SAVED_BATCH_COACH_REPORTS = 'Saved Batch Coach reports';

export const BATCH_COACH_BUILDING_TITLE = 'Building your Batch Coach report';
export const BATCH_COACH_REPORT_READY = 'Your Batch Coach report is ready';
export const BATCH_COACH_PREPARING =
  'Preparing your Batch Coach report. This usually takes several minutes.';

export const BATCH_COACH_FAILED = 'Batch Coach failed';
export const BATCH_COACH_START_FAILED = 'Failed to start Batch Coach';
export const BATCH_COACH_STATUS_FAILED = 'Failed to check Batch Coach status';

export const batchCoachRequiresMinGames = (min = 5) =>
  `Batch Coach requires at least ${min} games to detect patterns.`;

export const batchCoachMaxGames = (max = 30) =>
  `Batch Coach supports a maximum of ${max} games.`;

export const batchCoachMaxGamesToast = (max = 30) =>
  `Maximum number of games for Batch Coach is ${max}`;

export const BATCH_COACH_STARTED = 'Batch Coach started';
export const BATCH_COACH_PENDING = 'Batch Coach pending';
export const BATCH_COACH_IN_PROGRESS = 'Batch Coach in progress';

export const BATCH_COACH_START_BUTTON = 'Start Batch Coach';
export const BATCH_COACH_NAV_LABEL = BATCH_COACH;

export const BATCH_COACH_SAVED_BREADCRUMB = `${BATCH_COACH} → ${SAVED_BATCH_COACH_REPORTS}`;

export const BATCH_COACH_TAGLINE =
  'Batch Coach finds patterns across your recent games (default 10, min 5, max 30).';

export const BATCH_COACH_INCLUDED =
  'Batch Coach is included for games already on your account (credits are used when you import games).';

export const BATCH_COACH_LEGACY_LINK_MSG =
  'This report link is outdated. Open your report from Batch Coach history.';

export const BATCH_COACH_RESULTS_TITLE = 'Batch Coach report';

export const batchCoachHeaderGames = (count) => `${BATCH_COACH} · ${count} games`;

export const BATCH_COACH_NO_SAVED =
  'No saved reports yet. Run Batch Coach to create your first report.';

export const BATCH_COACH_RERUN_OPENING =
  're-run Batch Coach to refresh opening insights.';

export const BATCH_COACH_RERUN_REPERTOIRE =
  'Run a new Batch Coach report to see repertoire feedback.';
