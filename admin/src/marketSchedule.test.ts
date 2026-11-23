import { describe, expect, it } from 'vitest';
import { marketNamesForDay, WEEKDAYS } from './marketSchedule';

describe('market weekly schedule', () => {
  const markets = [
    { name: 'Beneta', schedule_days: [3], is_active: true },
    { name: 'Asheker', schedule_days: [1], is_active: true },
    { name: 'Boshkoro', schedule_days: [5], is_active: true },
    { name: 'Bala', schedule_days: [1], is_active: true },
    { name: 'Koybe', schedule_days: [0], is_active: true },
    { name: 'Bobo', schedule_days: [2], is_active: true },
    { name: 'Ajo', schedule_days: [5], is_active: true },
    { name: 'Gento', schedule_days: [5], is_active: true },
    { name: 'Inactive', schedule_days: [5], is_active: false },
  ];

  it('defines a seven-day Monday-first week', () => {
    expect(WEEKDAYS).toHaveLength(7);
    expect(WEEKDAYS[0]).toBe('Monday');
    expect(WEEKDAYS[6]).toBe('Sunday');
  });

  it('returns the configured active markets for each weekday', () => {
    expect(marketNamesForDay(markets, 0)).toEqual(['Koybe']);
    expect(marketNamesForDay(markets, 1)).toEqual(['Asheker', 'Bala']);
    expect(marketNamesForDay(markets, 2)).toEqual(['Bobo']);
    expect(marketNamesForDay(markets, 3)).toEqual(['Beneta']);
    expect(marketNamesForDay(markets, 4)).toEqual([]);
    expect(marketNamesForDay(markets, 5)).toEqual(['Ajo', 'Boshkoro', 'Gento']);
    expect(marketNamesForDay(markets, 6)).toEqual([]);
  });
});
