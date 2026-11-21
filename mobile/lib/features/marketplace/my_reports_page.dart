import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../l10n/market_strings.dart';

class MyReportsPage extends StatefulWidget {
  const MyReportsPage({
    super.key,
    required this.apiBaseUrl,
    required this.client,
    required this.accessToken,
  });

  final String apiBaseUrl;
  final http.Client client;
  final String accessToken;

  @override
  State<MyReportsPage> createState() => _MyReportsPageState();
}

class _MyReportsPageState extends State<MyReportsPage> {
  List<Map<String, dynamic>> _reports = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final response = await widget.client.get(
        Uri.parse('${widget.apiBaseUrl}/reports/my'),
        headers: {'Authorization': 'Bearer ${widget.accessToken}'},
      );
      if (response.statusCode != 200) {
        throw Exception('Could not load reports (${response.statusCode}).');
      }
      final rows = jsonDecode(response.body) as List<dynamic>;
      if (!mounted) return;
      setState(() => _reports = rows.cast<Map<String, dynamic>>());
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('My reports'),
      actions: [IconButton(
        tooltip: 'Refresh reports',
        onPressed: _loading ? null : _load,
        icon: const Icon(Icons.refresh),
      )],
    ),
    body: _loading
      ? const Center(child: CircularProgressIndicator())
      : _error != null
        ? Center(child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Text(_error!, textAlign: TextAlign.center),
              const SizedBox(height: 12),
              FilledButton(onPressed: _load, child: const Text('Try again')),
            ]),
          ))
        : _reports.isEmpty
          ? const Center(child: Text('You have not submitted any reports.'))
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: _reports.length,
                separatorBuilder: (_, __) => const SizedBox(height: 10),
                itemBuilder: (context, index) {
                  final report = _reports[index];
                  final target = report['listing_id'] != null ? 'Listing report' : 'Seller report';
                  return Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Row(children: [
                          Expanded(child: Text(target, style: Theme.of(context).textTheme.titleMedium)),
                          Chip(label: Text(marketStatusLabel(context, report['status'] as String? ?? 'pending'))),
                        ]),
                        Text((report['reason'] as String? ?? 'other').replaceAll('_', ' ')),
                        const SizedBox(height: 6),
                        Text(report['description'] as String? ?? ''),
                        if (report['review_note'] is String && (report['review_note'] as String).isNotEmpty) ...[
                          const SizedBox(height: 8),
                          Text('Review update: ${report['review_note']}'),
                        ],
                        const SizedBox(height: 8),
                        Text(
                          'Submitted: ${report['created_at'] ?? ''}',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ]),
                    ),
                  );
                },
              ),
            ),
  );
}
