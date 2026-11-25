import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../data/local_draft_store.dart';
import '../../data/market_schedule_cache.dart';
import '../../l10n/market_strings.dart';

class MarketCalendarPage extends StatefulWidget {
  const MarketCalendarPage({
    super.key,
    required this.apiBaseUrl,
    required this.client,
    this.cache,
  });

  final String apiBaseUrl;
  final http.Client client;
  final MarketScheduleCache? cache;

  @override
  State<MarketCalendarPage> createState() => _MarketCalendarPageState();
}

class _MarketCalendarPageState extends State<MarketCalendarPage> {
  LocalDraftStore? _ownedStore;
  MarketScheduleCache get _cache => widget.cache ?? (_ownedStore ??= LocalDraftStore());

  Map<String, dynamic>? _schedule;
  bool _loading = true;
  bool _offline = false;
  String? _updatedAt;
  String? _error;
  String _search = '';
  int? _weekdayFilter;

  @override
  void initState() {
    super.initState();
    unawaited(_load());
  }

  @override
  void dispose() {
    if (widget.cache == null) {
      unawaited(_ownedStore?.close() ?? Future<void>.value());
    }
    super.dispose();
  }

  Future<void> _load() async {
    if (mounted) setState(() { _loading = true; _error = null; _offline = false; });
    try {
      if (widget.apiBaseUrl.trim().isEmpty) {
        throw Exception('The market schedule service is not configured.');
      }
      final response = await widget.client.get(
        Uri.parse('${widget.apiBaseUrl}/markets/schedule?lang=${Localizations.localeOf(context).languageCode}'),
      );
      if (response.statusCode != 200) {
        throw Exception('The market schedule could not be loaded.');
      }
      final payload = jsonDecode(response.body) as Map<String, dynamic>;
      await _cache.saveMarketSchedule(payload);
      if (mounted) setState(() {
        _schedule = payload;
        _updatedAt = DateTime.now().toUtc().toIso8601String();
      });
    } catch (error) {
      final cached = await _cache.cachedMarketSchedule();
      if (mounted) {
        if (cached != null) {
          setState(() {
            _schedule = cached;
            _offline = true;
            _updatedAt = cached['cached_at'] as String?;
          });
        } else {
          setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
        }
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final days = (_schedule?['days'] as List<dynamic>? ?? const [])
        .cast<Map<String, dynamic>>();
    return Scaffold(
      appBar: AppBar(
        title: Text(marketString(context,
          en: 'Weekly market calendar', am: 'ሳምንታዊ የገበያ ቀን መቁጠሪያ', mdy: '')),
        actions: [
          IconButton(
            tooltip: marketString(context, en: 'Refresh schedule', am: 'የገበያ ቀናትን አድስ', mdy: ''),
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(mainAxisSize: MainAxisSize.min, children: [
                    Text(_error!, textAlign: TextAlign.center),
                    const SizedBox(height: 12),
                    OutlinedButton(onPressed: _load, child: Text(
                      marketString(context, en: 'Try again', am: 'እንደገና ይሞክሩ', mdy: ''),
                    )),
                  ]),
                ))
              : Column(children: [
                  if (_updatedAt != null)
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
                      child: Align(
                        alignment: Alignment.centerLeft,
                        child: Text(
                          "${marketString(context, en: 'Last updated', am: 'መጨረሻ የተዘመነበት', mdy: '')}: ${DateTime.tryParse(_updatedAt!)?.toLocal().toString() ?? _updatedAt}",
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ),
                    ),
                  if (_offline)
                    MaterialBanner(
                      content: Text(marketString(context,
                        en: 'Offline — showing the last saved market schedule.',
                        am: 'ከመስመር ውጭ — የመጨረሻው የተቀመጠ የገበያ መርሐ ግብር እየታየ ነው።',
                        mdy: '')),
                      actions: const [SizedBox.shrink()],
                    ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
                    child: Column(children: [
                      TextField(
                        decoration: InputDecoration(
                          labelText: marketString(context, en: 'Search markets', am: 'ገበያ ይፈልጉ', mdy: ''),
                          prefixIcon: const Icon(Icons.search),
                        ),
                        onChanged: (value) => setState(() => _search = value.trim().toLowerCase()),
                      ),
                      DropdownButtonFormField<int?>(
                        value: _weekdayFilter,
                        decoration: InputDecoration(
                          labelText: marketString(context, en: 'Filter by weekday', am: 'በሳምንቱ ቀን ያጣሩ', mdy: ''),
                        ),
                        items: [
                          DropdownMenuItem<int?>(value: null, child: Text(marketString(context, en: 'All days', am: 'ሁሉም ቀናት', mdy: ''))),
                          ...List.generate(7, (index) => DropdownMenuItem<int?>(value: index, child: Text(marketWeekdayLabel(context, index)))),
                        ],
                        onChanged: (value) => setState(() => _weekdayFilter = value),
                      ),
                    ]),
                  ),
                  Expanded(child: ListView.builder(
                    padding: const EdgeInsets.all(12),
                    itemCount: days.where((day) => _weekdayFilter == null || day['weekday'] == _weekdayFilter).length,
                    itemBuilder: (context, index) {
                      final filteredDays = days.where((day) => _weekdayFilter == null || day['weekday'] == _weekdayFilter).toList();
                      final day = filteredDays[index];
                      final weekday = day['weekday'] as int;
                      final markets = (day['markets'] as List<dynamic>? ?? const [])
                          .cast<Map<String, dynamic>>()
                          .where((market) => (market['name'] as String? ?? '').toLowerCase().contains(_search))
                          .toList();
                      return Card(
                        child: Padding(
                          padding: const EdgeInsets.all(14),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(children: [
                                Expanded(child: Text(
                                  marketWeekdayLabel(context, weekday),
                                  style: Theme.of(context).textTheme.titleMedium,
                                )),
                                Text('${markets.length}'),
                              ]),
                              const SizedBox(height: 8),
                              if (markets.isEmpty)
                                Text(marketString(context,
                                  en: 'No market recorded for this day.',
                                  am: 'ለዚህ ቀን ገበያ አልተመዘገበም።', mdy: ''))
                              else
                                Wrap(
                                  spacing: 8,
                                  runSpacing: 6,
                                  children: markets.map((market) => ActionChip(
                                    label: Text(market['name'] as String? ?? ''),
                                    avatar: const Icon(Icons.storefront_outlined, size: 18),
                                    onPressed: () {
                                      final marketId = market['id'] as String?;
                                      if (marketId == null || marketId.isEmpty) return;
                                      Navigator.of(context).push(MaterialPageRoute<void>(
                                        builder: (_) => MarketDetailPage(
                                          apiBaseUrl: widget.apiBaseUrl,
                                          client: widget.client,
                                          marketId: marketId,
                                          initialMarket: market,
                                        ),
                                      ));
                                    },
                                  )).toList(),
                                ),
                            ],
                          ),
                        ),
                      );
                    },
                  )),
                ]),
    );
  }
}



class MarketDetailPage extends StatefulWidget {
  const MarketDetailPage({
    super.key,
    required this.apiBaseUrl,
    required this.client,
    required this.marketId,
    required this.initialMarket,
  });

  final String apiBaseUrl;
  final http.Client client;
  final String marketId;
  final Map<String, dynamic> initialMarket;

  @override
  State<MarketDetailPage> createState() => _MarketDetailPageState();
}

class _MarketDetailPageState extends State<MarketDetailPage> {
  late Map<String, dynamic> _market = Map<String, dynamic>.from(widget.initialMarket);
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    unawaited(_load());
  }

  Future<void> _load() async {
    try {
      final language = Localizations.localeOf(context).languageCode;
      final response = await widget.client.get(Uri.parse(
        '${widget.apiBaseUrl}/markets/${widget.marketId}?lang=$language',
      ));
      if (response.statusCode != 200) {
        throw Exception(marketString(context,
          en: 'Market details could not be loaded.',
          am: 'የገበያውን ዝርዝር መረጃ ማምጣት አልተቻለም።', mdy: ''));
      }
      if (mounted) setState(() => _market = jsonDecode(response.body) as Map<String, dynamic>);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final language = Localizations.localeOf(context).languageCode;
    final name = (_market['name'] ?? (language == 'am' ? _market['name_am'] : _market['name_en']) ?? '').toString();
    final location = _market['location'] is Map<String, dynamic>
        ? _market['location'] as Map<String, dynamic>
        : <String, dynamic>{};
    final address = (_market['address'] ?? (language == 'am' ? _market['address_am'] : _market['address_en']))?.toString();
    final description = (_market['description'] ?? '').toString();
    final days = (_market['schedule_days'] as List<dynamic>? ?? const []).cast<int>();
    final latitude = (_market['latitude'] as num?)?.toDouble();
    final longitude = (_market['longitude'] as num?)?.toDouble();
    return Scaffold(
      appBar: AppBar(title: Text(name.isEmpty
          ? marketString(context, en: 'Market details', am: 'የገበያ ዝርዝር', mdy: '')
          : name)),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (_error != null)
                  MaterialBanner(
                    content: Text(_error!),
                    actions: [
                      TextButton(onPressed: _load, child: Text(
                        marketString(context, en: 'Retry', am: 'እንደገና ይሞክሩ', mdy: ''),
                      )),
                    ],
                  ),
                Text(name, style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 8),
                if (_market['name_en'] != null || _market['name_am'] != null)
                  Text(
                    '${_market['name_en'] ?? 'English name pending'} • ${_market['name_am'] ?? 'የአማርኛ ስም ይጠበቃል'}',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                const SizedBox(height: 16),
                _detailRow(context, Icons.location_on_outlined,
                  marketString(context, en: 'Town / locality', am: 'ከተማ / አካባቢ', mdy: ''),
                  (language == 'am' ? (location['name_am'] ?? 'የአማርኛ ስም ይጠበቃል') : (location['name_en'] ?? '')).toString()),
                _detailRow(context, Icons.place_outlined,
                  marketString(context, en: 'Address', am: 'አድራሻ', mdy: ''),
                  address ?? marketString(context, en: 'Address not yet verified', am: 'አድራሻው ገና አልተረጋገጠም', mdy: '')),
                _detailRow(context, Icons.calendar_month_outlined,
                  marketString(context, en: 'Market day', am: 'የገበያ ቀን', mdy: ''),
                  days.isEmpty ? marketString(context, en: 'Not scheduled', am: 'አልተመደበም', mdy: '') : days.map((day) => marketWeekdayLabel(context, day)).join(', ')),
                if (description.isNotEmpty)
                  _detailRow(context, Icons.info_outline,
                    marketString(context, en: 'About this market', am: 'ስለዚህ ገበያ', mdy: ''),
                    description),
                const SizedBox(height: 16),
                Text(marketString(context, en: 'Location map', am: 'የአካባቢ ካርታ', mdy: ''),
                  style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 8),
                if (latitude != null && longitude != null)
                  ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.network(
                      'https://staticmap.openstreetmap.de/staticmap.php?center=$latitude,$longitude&zoom=14&size=640x360&markers=$latitude,$longitude,red-pushpin',
                      height: 220,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => _mapFallback(context, latitude, longitude),
                    ),
                  )
                else
                  _mapFallback(context, null, null),
              ],
            ),
    );
  }

  Widget _detailRow(BuildContext context, IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 9),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(icon, size: 20),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(label, style: Theme.of(context).textTheme.labelMedium),
          const SizedBox(height: 3),
          Text(value, style: Theme.of(context).textTheme.bodyLarge),
        ])),
      ]),
    );
  }

  Widget _mapFallback(BuildContext context, double? latitude, double? longitude) {
    final hasCoordinates = latitude != null && longitude != null;
    return Container(
      height: 150,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
        const Icon(Icons.map_outlined, size: 34),
        const SizedBox(height: 8),
        Text(hasCoordinates
            ? '$latitude, $longitude'
            : marketString(context, en: 'Map coordinates are awaiting local verification.',
                am: 'የካርታ መጋጠሚያዎች የአካባቢ ማረጋገጫ ይጠብቃሉ።', mdy: ''),
          textAlign: TextAlign.center),
      ]),
    );
  }
}
