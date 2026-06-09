const MAX_ITEMS = 4;

export const buildDrillChecklistItems = ({
  coaching = {},
  worstMoment = null,
  drillLink = null,
} = {}) => {
  const items = [];

  if (coaching.do_today) {
    items.push({
      id: 'do_today',
      label: String(coaching.do_today),
    });
  }

  if (worstMoment?.move_number) {
    items.push({
      id: 'replay_moment',
      label: `Replay move ${worstMoment.move_number} on the board panel`,
    });
  }

  if (drillLink?.url) {
    items.push({
      id: 'lichess_drill',
      label: drillLink.label || 'Practice on Lichess',
      url: drillLink.url,
    });
  }

  if (coaching.takeaway && items.length < MAX_ITEMS) {
    items.push({
      id: 'takeaway',
      label: `Reflect on the takeaway: ${String(coaching.takeaway).slice(0, 140)}`,
    });
  }

  return items.slice(0, MAX_ITEMS);
};

export const drillChecklistStorageKey = (gameId, completedAt = null) => {
  const stamp = completedAt ? String(completedAt).replace(/[^\w.-]/g, '_') : 'latest';
  return `sg_drill_${gameId}_${stamp}`;
};

export const readDrillChecklistState = (storageKey) => {
  if (!storageKey || typeof localStorage === 'undefined') {
    return {};
  }
  try {
    const raw = localStorage.getItem(storageKey);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
};

export const writeDrillChecklistState = (storageKey, checkedMap) => {
  if (!storageKey || typeof localStorage === 'undefined') {
    return;
  }
  localStorage.setItem(storageKey, JSON.stringify(checkedMap));
};

export const countChecked = (items, checkedMap) => (
  items.filter((item) => checkedMap[item.id]).length
);
