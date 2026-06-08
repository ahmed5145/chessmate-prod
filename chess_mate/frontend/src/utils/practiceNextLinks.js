import { buildPriorityDrillDisplay } from './priorityDrillDisplay';
import {
  collectStudyLinksFromBatchSummary,
  resolvePriorityLichessLink,
} from './lichessStudyLinks';

const MAX_BATCH_LINKS = 2;

/**
 * Priority #1 Lichess drill plus up to two unique batch study URLs (deduped).
 */
export const collectPracticeNextLinks = ({
  coaching_report,
  batch_summary,
  per_game_results = [],
}) => {
  const links = [];
  const seen = new Set();

  const addLink = (entry) => {
    if (!entry?.url || seen.has(entry.url)) {
      return;
    }
    seen.add(entry.url);
    links.push(entry);
  };

  const priorities = coaching_report?.top_3_priorities || [];
  const priorityOne = priorities.find((item) => Number(item?.rank) === 1) || priorities[0];

  if (priorityOne) {
    const lichessLink = resolvePriorityLichessLink(priorityOne, {
      batch_summary,
      per_game_results,
    });
    if (lichessLink) {
      addLink({
        ...lichessLink,
        source: 'priority',
        headline: 'Priority #1 drill',
        description:
          buildPriorityDrillDisplay(priorityOne, per_game_results)
          || priorityOne.specific_drill
          || priorityOne.title,
      });
    }
  }

  let batchCount = 0;
  collectStudyLinksFromBatchSummary(batch_summary).forEach((link) => {
    if (batchCount >= MAX_BATCH_LINKS) {
      return;
    }
    if (seen.has(link.url)) {
      return;
    }
    addLink({
      ...link,
      source: 'batch',
      headline: link.label,
      description: null,
    });
    batchCount += 1;
  });

  return links;
};

export const getRemainingStudyDrillLinks = (batchReport) => {
  const practiceUrls = new Set(
    collectPracticeNextLinks({
      coaching_report: batchReport?.coaching_report,
      batch_summary: batchReport?.batch_summary,
      per_game_results: batchReport?.per_game_results,
    }).map((link) => link.url)
  );

  return collectStudyLinksFromBatchSummary(batchReport?.batch_summary).filter(
    (link) => !practiceUrls.has(link.url)
  );
};
