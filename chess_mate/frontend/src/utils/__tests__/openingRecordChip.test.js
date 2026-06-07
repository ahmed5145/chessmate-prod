import { getOpeningRecordChipProps } from '../openingRecordChip';

describe('getOpeningRecordChipProps', () => {
  it('colors wins green', () => {
    expect(getOpeningRecordChipProps('1W-0L-0D')).toEqual({ color: 'success', variant: 'filled' });
  });

  it('colors losses red', () => {
    expect(getOpeningRecordChipProps('0W-1L-0D')).toEqual({ color: 'error', variant: 'filled' });
  });

  it('colors draws yellow', () => {
    expect(getOpeningRecordChipProps('0W-0L-1D')).toEqual({ color: 'warning', variant: 'filled' });
  });
});
