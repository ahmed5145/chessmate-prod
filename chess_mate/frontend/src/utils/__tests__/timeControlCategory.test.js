import { getTimeControlCategory } from '../timeControlCategory';

describe('getTimeControlCategory', () => {
  it('uses named category fields from API', () => {
    expect(getTimeControlCategory({ time_control_category: 'blitz' })).toBe('blitz');
    expect(getTimeControlCategory({ time_control: 'rapid' })).toBe('rapid');
  });

  it('parses numeric seconds format', () => {
    expect(getTimeControlCategory({ time_control: '180+2' })).toBe('blitz');
    expect(getTimeControlCategory({ time_control: '600+0' })).toBe('rapid');
  });

  it('does not treat blitz string as classical', () => {
    expect(getTimeControlCategory({ time_control: 'blitz' })).toBe('blitz');
    expect(getTimeControlCategory({ time_control: 'blitz' })).not.toBe('classical');
  });
});
