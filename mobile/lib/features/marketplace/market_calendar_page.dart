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
        Uri.parse('${widget.apiBaseUrl}/markets/schedule'),
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
                                  children: markets.map((market) => Chip(
                                    label: Text(market['name'] as String? ?? ''),
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
