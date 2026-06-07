/** Chip color for W/L/D opening records like "1W-0L-0D". */

export const parseOpeningRecord = (record = '') => {
  const wins = Number(record.match(/(\d+)W/i)?.[1] || 0);
  const losses = Number(record.match(/(\d+)L/i)?.[1] || 0);
  const draws = Number(record.match(/(\d+)D/i)?.[1] || 0);
  return { wins, losses, draws };
};

export const getOpeningRecordChipProps = (record) => {
  const { wins, losses, draws } = parseOpeningRecord(record);

  if (wins > losses && wins > draws) {
    return { color: 'success', variant: 'filled' };
  }
  if (losses > wins && losses >= draws) {
    return { color: 'error', variant: 'filled' };
  }
  if (draws > wins && draws > losses) {
    return { color: 'warning', variant: 'filled' };
  }
  if (draws > 0 && draws === wins && draws > losses) {
    return { color: 'warning', variant: 'filled' };
  }
  if (draws > 0 && wins === 0 && losses === 0) {
    return { color: 'default', variant: 'filled' };
  }
  return { color: 'default', variant: 'outlined' };
};
