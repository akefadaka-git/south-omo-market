import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../../l10n/market_strings.dart';
import 'buyer_auth_dialog.dart';

class ListingDetailPage extends StatefulWidget {
  const ListingDetailPage({
    super.key,
    required this.apiBaseUrl,
    required this.client,
    required this.listingId,
  });

  final String apiBaseUrl;
  final http.Client client;
  final String listingId;

  @override
  State<ListingDetailPage> createState() => _ListingDetailPageState();
}

class _ListingDetailPageState extends State<ListingDetailPage> {
  Map<String, dynamic>? _listing;
  final _messageController = TextEditingController();
  String? _error;
  String? _notice;
  bool _sending = false;

  @override
  void initState() { super.initState(); _load(); }

  @override
  void dispose() { _messageController.dispose(); super.dispose(); }

  Future<void> _sendInquiry() async {
    final message = _messageController.text.trim();
    if (message.isEmpty || message.length > 2000) {
      setState(() => _error = marketString(context, en: 'Enter a message of up to 2,000 characters.', am: 'እስከ 2,000 ፊደላት ያለው መልዕክት ያስገቡ።', mdy: ''));
      return;
    }
    setState(() { _sending = true; _error = null; _notice = null; });
    try {
      final token = await showDialog<String>(
        context: context,
        builder: (_) => BuyerAuthDialog(apiBaseUrl: widget.apiBaseUrl, client: widget.client),
      );
      if (token == null) {
        if (mounted) setState(() => _error = marketString(context, en: 'Buyer sign-in was not completed. Please try again.', am: 'የገዢ መግቢያ አልተጠናቀቀም። እንደገና ይሞክሩ።', mdy: ''));
        return;
      }
      final response = await widget.client.post(
        Uri.parse('${widget.apiBaseUrl}/inquiries'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({'listing_id': widget.listingId, 'message': message}),
      );
      if (response.statusCode == 409) {
        throw Exception(marketString(context, en: 'You cannot inquire about your own listing.', am: 'ስለ ራስዎ ዝርዝር ጥያቄ መላክ አይችሉም።', mdy: ''));
      }
      if (response.statusCode != 201) {
        throw Exception(response.statusCode == 404
          ? marketString(context, en: 'This listing is no longer available.', am: 'ይህ ዝርዝር ከእንግዲህ አይገኝም።', mdy: '')
          : marketString(context, en: 'Your inquiry could not be sent (${response.statusCode}).', am: 'ጥያቄዎን መላክ አልተቻለም (${response.statusCode})።', mdy: ''));
      }
      if (mounted) {
        _messageController.clear();
        setState(() => _notice = marketString(context, en: 'Your inquiry was sent to the seller.', am: 'ጥያቄዎ ለሻጩ ተልኳል።', mdy: ''));
      }
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  Future<void> _load() async {
    try {
      final response = await widget.client.get(
        Uri.parse('${widget.apiBaseUrl}/listings/${widget.listingId}'),
      );
      if (response.statusCode != 200) throw Exception(marketString(context, en: 'Listing is no longer available.', am: 'ይህ ዝርዝር ከእንግዲህ አይገኝም።', mdy: ''));
      if (mounted) setState(() => _listing = jsonDecode(response.body) as Map<String, dynamic>);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    }
  }

  @override
  Widget build(BuildContext context) {
    final listing = _listing;
    return Scaffold(
      appBar: AppBar(title: Text(marketString(context, en: 'Listing details', am: 'የዝርዝር መረጃ', mdy: ''))),
      body: _error != null
        ? Center(child: Text(_error!))
        : listing == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(16), children: [
              Text(listing['title'] as String, style: Theme.of(context).textTheme.headlineSmall),
              Text('${((listing['price_minor'] as num) / 100).toStringAsFixed(2)} ETB'),
              Text(listing['location'] as String? ?? ''),
              const SizedBox(height: 12),
              for (final image in (listing['images'] as List<dynamic>? ?? []))
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Image.network(
                    Uri.parse('${widget.apiBaseUrl}/').resolve(image['url'] as String).toString(),
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => SizedBox(
                      height: 80, child: Center(child: Text(marketString(context, en: 'Photo unavailable', am: 'ፎቶው አልተገኘም', mdy: ''))),
                    ),
                  ),
                ),
              Text(listing['description'] as String? ?? ''),
              const SizedBox(height: 24),
              Text(marketString(context, en: 'Contact seller', am: 'ሻጩን ያነጋግሩ', mdy: ''), style: Theme.of(context).textTheme.titleLarge),
              Text(marketString(context, en: 'Sign in or create a buyer account to send your inquiry. Your registered phone number is shared with the seller.', am: 'ጥያቄዎን ለመላክ ይግቡ ወይም የገዢ መለያ ይፍጠሩ። የተመዘገበው ስልክ ቁጥርዎ ለሻጩ ይታያል።', mdy: '')),
              TextField(
                key: const Key('buyer-inquiry-message'),
                controller: _messageController,
                maxLines: 4,
                maxLength: 2000,
                decoration: InputDecoration(
                  labelText: marketString(context, en: 'Your message', am: 'መልዕክትዎ', mdy: ''),
                  hintText: marketString(context, en: 'Ask about availability, condition or collection', am: 'ስለ መኖሩ፣ ሁኔታው ወይም መውሰጃው ይጠይቁ', mdy: ''),
                  border: OutlineInputBorder(),
                ),
              ),
              FilledButton.icon(
                onPressed: _sending ? null : _sendInquiry,
                icon: const Icon(Icons.send),
                label: Text(_sending ? marketString(context, en: 'Sending…', am: 'በመላክ ላይ…', mdy: '') : marketString(context, en: 'Send inquiry', am: 'ጥያቄ ላክ', mdy: '')),
              ),
              if (_notice != null) Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(_notice!, style: TextStyle(color: Theme.of(context).colorScheme.primary)),
              ),
              if (_error != null) Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ),
            ]),
    );
  }
}

