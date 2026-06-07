/**
 * Consistent numeric display in batch reports (max 2 decimal places).
 */

export const formatNumber = (value, decimals = 2) => {
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return '0';
  }
  return numeric.toFixed(decimals);
};
