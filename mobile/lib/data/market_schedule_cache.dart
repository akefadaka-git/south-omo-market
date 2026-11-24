abstract interface class MarketScheduleCache {
  Future<void> saveMarketSchedule(Map<String, dynamic> schedule);
  Future<Map<String, dynamic>?> cachedMarketSchedule();
}
