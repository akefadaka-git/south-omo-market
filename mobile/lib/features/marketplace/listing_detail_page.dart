import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../../l10n/market_strings.dart';
import 'buyer_auth_dialog.dart';
import 'my_reports_page.dart';

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


  Future<void> _report({required String? listingId, required String? sellerId}) async {
    setState(() { _sending = true; _error = null; _notice = null; });
    try {
      final token = await showDialog<String>(
        context: context,
        builder: (_) => BuyerAuthDialog(apiBaseUrl: widget.apiBaseUrl, client: widget.client),
      );
      if (token == null || !mounted) return;
      final report = await showDialog<Map<String, String>>(
        context: context,
        builder: (_) => _ReportComposeDialog(),
      );
      if (report == null || !mounted) return;
      final response = await widget.client.post(
        Uri.parse('${widget.apiBaseUrl}/reports'),
        headers: {'Authorization': 'Bearer $token', 'Content-Type': 'application/json'},
        body: jsonEncode({
          if (listingId != null) 'listing_id': listingId,
          if (sellerId != null) 'seller_id': sellerId,
          'reason': report['reason'],
          'description': report['description'],
          'evidence': (report['evidence_summary'] ?? '').isNotEmpty
              ? [{
                  'summary': report['evidence_summary'],
                  if ((report['evidence_reference'] ?? '').isNotEmpty)
                    'reference': report['evidence_reference'],
                }]
              : [],
        }),
      );
      if (response.statusCode != 201) {
        final detail = (jsonDecode(response.body) as Map<String, dynamic>)['detail'];
        throw Exception(detail is String ? detail : 'Report could not be submitted (${response.statusCode}).');
      }
      if (mounted) setState(() => _notice = 'Report submitted. You can follow its status in My reports.');
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  Future<void> _openMyReports() async {
    final token = await showDialog<String>(
      context: context,
      builder: (_) => BuyerAuthDialog(apiBaseUrl: widget.apiBaseUrl, client: widget.client),
    );
    if (token == null || !mounted) return;
    await Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => MyReportsPage(
        apiBaseUrl: widget.apiBaseUrl,
        client: widget.client,
        accessToken: token,
      ),
    ));
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
              const SizedBox(height: 12),
              Wrap(spacing: 8, runSpacing: 8, children: [
                OutlinedButton.icon(
                  onPressed: _sending ? null : () => _report(listingId: widget.listingId, sellerId: null),
                  icon: const Icon(Icons.flag_outlined),
                  label: Text(marketString(context, en: 'Report listing', am: 'ዝርዝሩን ሪፖርት አድርግ', mdy: '')),
                ),
                if (listing['seller_id'] is String)
                  OutlinedButton.icon(
                    onPressed: _sending ? null : () => _report(listingId: null, sellerId: listing['seller_id'] as String),
                    icon: const Icon(Icons.person_off_outlined),
                    label: Text(marketString(context, en: 'Report seller', am: 'ሻጩን ሪፖርት አድርግ', mdy: '')),
                  ),
                TextButton(
                  onPressed: _sending ? null : _openMyReports,
                  child: Text(marketString(context, en: 'My reports', am: 'ሪፖርቶቼ', mdy: '')),
                ),
              ]),
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

class _ReportComposeDialog extends StatefulWidget {
  @override
  State<_ReportComposeDialog> createState() => _ReportComposeDialogState();
}

class _ReportComposeDialogState extends State<_ReportComposeDialog> {
  final _formKey = GlobalKey<FormState>();
  final _description = TextEditingController();
  final _evidenceSummary = TextEditingController();
  final _evidenceReference = TextEditingController();
  String _reason = 'misleading_information';

  @override
  void dispose() {
    _description.dispose();
    _evidenceSummary.dispose();
    _evidenceReference.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(marketString(context, en: 'Report concern', am: 'ችግር ሪፖርት አድርግ', mdy: '')),
    content: Form(
      key: _formKey,
      child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
        DropdownButtonFormField<String>(
          value: _reason,
          decoration: InputDecoration(labelText: marketString(context, en: 'Reason', am: 'ምክንያት', mdy: '')),
          items: [
            DropdownMenuItem(value: 'fraud', child: Text(marketString(context, en: 'Fraud or scam', am: 'ማጭበርበር', mdy: ''))),
            DropdownMenuItem(value: 'misleading_information', child: Text(marketString(context, en: 'Misleading information', am: 'አሳሳች መረጃ', mdy: ''))),
            DropdownMenuItem(value: 'prohibited_item', child: Text(marketString(context, en: 'Prohibited item', am: 'የተከለከለ ዕቃ', mdy: ''))),
            DropdownMenuItem(value: 'harassment', child: Text(marketString(context, en: 'Harassment', am: 'ማዋከብ', mdy: ''))),
            DropdownMenuItem(value: 'unsafe_activity', child: Text(marketString(context, en: 'Unsafe activity', am: 'አደገኛ ተግባር', mdy: ''))),
            DropdownMenuItem(value: 'impersonation', child: Text(marketString(context, en: 'Impersonation', am: 'ሌላን መምሰል', mdy: ''))),
            DropdownMenuItem(value: 'spam', child: Text(marketString(context, en: 'Spam', am: 'አላስፈላጊ መልዕክት', mdy: ''))),
            DropdownMenuItem(value: 'other', child: Text(marketString(context, en: 'Other', am: 'ሌላ', mdy: ''))),
          ],
          onChanged: (value) { if (value != null) setState(() => _reason = value); },
        ),
        const SizedBox(height: 12),
        TextFormField(
          controller: _description,
          minLines: 3,
          maxLines: 5,
          maxLength: 4000,
          decoration: InputDecoration(
            labelText: marketString(context, en: 'Describe the concern', am: 'ችግሩን ይግለጹ', mdy: ''),
            helperText: marketString(context, en: 'Include relevant facts. Do not include passwords or sensitive personal data.', am: 'ተዛማጅ እውነታዎችን ያካትቱ። የይለፍ ቃል ወይም ሚስጥራዊ የግል መረጃ አያስገቡ።', mdy: ''),
            border: OutlineInputBorder(),
          ),
          validator: (value) => (value == null || value.trim().length < 10)
            ? 'Please provide at least 10 characters.' : null,
        ),
        const SizedBox(height: 10),
        TextFormField(
          controller: _evidenceSummary,
          minLines: 2,
          maxLines: 3,
          maxLength: 3000,
          decoration: const InputDecoration(
            labelText: marketString(context, en: 'Evidence summary (optional)', am: 'የማስረጃ ማጠቃለያ (አማራጭ)', mdy: ''),
            border: OutlineInputBorder(),
          ),
        ),
        TextFormField(
          controller: _evidenceReference,
          maxLength: 500,
          decoration: const InputDecoration(
            labelText: marketString(context, en: 'Evidence reference (optional)', am: 'የማስረጃ መለያ (አማራጭ)', mdy: ''),
            helperText: marketString(context, en: 'Do not enter a private URL or sensitive personal information.', am: 'የግል ዩአርኤል ወይም ሚስጥራዊ የግል መረጃ አያስገቡ።', mdy: ''),
          ),
        ),
      ])),
    ),
    actions: [
      TextButton(onPressed: () => Navigator.pop(context), child: Text(marketString(context, en: 'Cancel', am: 'ይቅር', mdy: ''))),
      FilledButton(
        onPressed: () {
          if (!_formKey.currentState!.validate()) return;
          Navigator.pop(context, {'reason': _reason, 'description': _description.text.trim(), 'evidence_summary': _evidenceSummary.text.trim(), 'evidence_reference': _evidenceReference.text.trim()});
        },
        child: Text(marketString(context, en: 'Submit report', am: 'ሪፖርት ላክ', mdy: '')),
      ),
    ],
  );
}

