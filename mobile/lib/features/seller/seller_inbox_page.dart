import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../l10n/market_strings.dart';
import '../../design/market_design_system.dart';

class SellerInboxPage extends StatefulWidget {
  const SellerInboxPage({
    super.key,
    required this.apiBaseUrl,
    required this.accessToken,
    required this.client,
    required this.onLogout,
  });

  final String apiBaseUrl;
  final String accessToken;
  final http.Client client;
  final VoidCallback onLogout;

  @override
  State<SellerInboxPage> createState() => _SellerInboxPageState();
}

class _SellerInboxPageState extends State<SellerInboxPage> {
  List<Map<String, dynamic>> _inquiries = [];
  String? _error;
  bool _loading = true;
  final Set<String> _updating = {};

  Map<String, String> get _headers => {
        'Authorization': 'Bearer ${widget.accessToken}',
        'Content-Type': 'application/json',
      };

  @override
  void initState() {
    super.initState();
    _loadInbox();
  }

  Future<void> _loadInbox() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final response = await widget.client.get(
        Uri.parse('${widget.apiBaseUrl}/inquiries/inbox?limit=50'),
        headers: _headers,
      );
      if (response.statusCode == 403) {
        throw Exception(marketString(context, en: 'A seller profile is required to use the inquiry inbox.', am: 'የጥያቄ ሳጥኑን ለመጠቀም የሻጭ መገለጫ ያስፈልጋል።', mdy: ''));
      }
      if (response.statusCode != 200) throw Exception(marketString(context, en: 'Could not load seller inquiries.', am: 'የሻጭ ጥያቄዎችን መጫን አልተቻለም።', mdy: ''));
      final rows = jsonDecode(response.body) as List<dynamic>;
      if (!mounted) return;
      setState(() {
        _inquiries = rows.cast<Map<String, dynamic>>();
      });
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _updateStatus(String inquiryId, String status) async {
    setState(() => _updating.add(inquiryId));
    try {
      final response = await widget.client.patch(
        Uri.parse('${widget.apiBaseUrl}/inquiries/$inquiryId/status'),
        headers: _headers,
        body: jsonEncode({'status': status}),
      );
      if (response.statusCode != 200) throw Exception(marketString(context, en: 'Could not update inquiry status.', am: 'የጥያቄውን ሁኔታ ማዘመን አልተቻለም።', mdy: ''));
      await _loadInbox();
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _updating.remove(inquiryId));
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: Row(mainAxisSize: MainAxisSize.min, children: [
            MarketBrandMark(size: 32), SizedBox(width: 9), Text(marketString(context, en: 'Seller inquiry inbox', am: 'የሻጭ ጥያቄዎች', mdy: '')),
          ]),
          actions: [
            IconButton(
              tooltip: marketString(context, en: 'Discover published listings', am: 'የታተሙ ዝርዝሮችን ያግኙ', mdy: ''),
              onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
                builder: (_) => MarketplaceDiscoveryPage(
                  apiBaseUrl: widget.apiBaseUrl,
                  client: widget.client,
                ),
              )),
              icon: const Icon(Icons.search),
            ),
            IconButton(
              tooltip: marketString(context, en: 'My listings', am: 'የእኔ ዝርዝሮች', mdy: ''),
              onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
                builder: (_) => SellerListingsPage(
                  apiBaseUrl: widget.apiBaseUrl,
                  accessToken: widget.accessToken,
                  client: widget.client,
                ),
              )),
              icon: const Icon(Icons.storefront_outlined),
            ),
            IconButton(
              tooltip: marketString(context, en: 'Offline listing drafts', am: 'ከመስመር ውጭ ረቂቆች', mdy: ''),
              onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
                builder: (_) => SellerDraftsPage(
                  apiBaseUrl: widget.apiBaseUrl,
                  accessToken: widget.accessToken,
                  client: widget.client,
                ),
              )),
              icon: const Icon(Icons.inventory_2_outlined),
            ),
            IconButton(
              tooltip: marketString(context, en: 'Refresh', am: 'አድስ', mdy: ''),
              onPressed: _loading ? null : _loadInbox,
              icon: const Icon(Icons.refresh),
            ),
            IconButton(
              tooltip: marketString(context, en: 'Sign out', am: 'ውጣ', mdy: ''),
              onPressed: widget.onLogout,
              icon: const Icon(Icons.logout),
            ),
          ],
        ),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(_error!, textAlign: TextAlign.center),
                          const SizedBox(height: 12),
                          FilledButton(onPressed: _loadInbox, child: Text(marketString(context, en: 'Retry', am: 'እንደገና ሞክር', mdy: ''))),
                        ],
                      ),
                    ),
                  )
                : _inquiries.isEmpty
                    ? Center(child: Text(marketString(context, en: 'No inquiries yet.', am: 'እስካሁን ምንም ጥያቄ የለም።', mdy: '')))
                    : RefreshIndicator(
                        onRefresh: _loadInbox,
                        child: ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: _inquiries.length,
                          itemBuilder: (context, index) {
                            final inquiry = _inquiries[index];
                            final id = inquiry['id'] as String;
                            final status = inquiry['status'] as String;
                            final updating = _updating.contains(id);
                            return Card(
                              margin: const EdgeInsets.only(bottom: 12),
                              child: Padding(
                                padding: const EdgeInsets.all(16),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      inquiry['listing_title'] as String? ?? 'Listing inquiry',
                                      style: Theme.of(context).textTheme.titleMedium,
                                    ),
                                    const SizedBox(height: 6),
                                    Text('${inquiry['buyer_name'] ?? 'Buyer'} · ${inquiry['buyer_contact'] ?? ''}'),
                                    const SizedBox(height: 8),
                                    Text(inquiry['message'] as String? ?? ''),
                                    const SizedBox(height: 8),
                                    Text('${marketString(context, en: 'Status', am: 'ሁኔታ', mdy: '')}: ${status == 'open' ? 'ክፍት' : status == 'read' ? 'ተነብቧል' : status == 'closed' ? 'ተዘግቷል' : status}'),
                                    const SizedBox(height: 8),
                                    Wrap(
                                      spacing: 8,
                                      children: [
                                        if (status == 'open')
                                          OutlinedButton(
                                            onPressed: updating ? null : () => _updateStatus(id, 'read'),
                                            child: Text(marketString(context, en: 'Mark read', am: 'እንደተነበበ ምልክት አድርግ', mdy: '')),
                                          ),
                                        if (status != 'closed')
                                          FilledButton.tonal(
                                            onPressed: updating ? null : () => _updateStatus(id, 'closed'),
                                            child: Text(marketString(context, en: 'Close inquiry', am: 'ጥያቄውን ዝጋ', mdy: '')),
                                          ),
                                        if (status == 'closed')
                                          OutlinedButton(
                                            onPressed: updating ? null : () => _updateStatus(id, 'open'),
                                            child: Text(marketString(context, en: 'Reopen', am: 'እንደገና ክፈት', mdy: '')),
                                          ),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                      ),
      );
}


