export const WEEKDAYS = [
  'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
] as const;

export function marketNamesForDay(
  markets: Array<{ name: string; schedule_days: number[]; is_active: boolean }>,
  weekday: number,
): string[] {
  return markets
    .filter((market) => market.is_active && market.schedule_days.includes(weekday))
    .map((market) => market.name)
    .sort((a, b) => a.localeCompare(b));
}
