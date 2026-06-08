/**
 * Client-side helpers for single-game credit waivers (mirrors backend rules).
 */

export const getUserPreferences = (user) => user?.preferences || user?.profile?.preferences || {};

export const hasUsedFirstSingleGameFree = (user) => {
  const preferences = getUserPreferences(user);
  return Boolean(preferences.single_game_free_used);
};

export const qualifiesForFirstSingleGameFree = (user, { isReanalyze = false } = {}) => {
  if (isReanalyze) {
    return false;
  }
  return !hasUsedFirstSingleGameFree(user);
};

export const getSingleGameCreditCostLabel = ({
  user,
  creditsRequired = 1,
  isReanalyze = false,
  fromBatch = false,
}) => {
  if (isReanalyze) {
    return creditsRequired;
  }
  if (fromBatch) {
    return 0;
  }
  if (qualifiesForFirstSingleGameFree(user)) {
    return 0;
  }
  return creditsRequired;
};
