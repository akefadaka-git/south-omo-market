import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:uuid/uuid.dart';

import '../../l10n/market_strings.dart';
import '../../design/market_design_system.dart';
import '../../design/market_brand_pages.dart';

class SellerListingsPage extends StatefulWidget {
  const SellerListingsPage({
    super.key,
    required this.apiBaseUrl,
    required this.accessToken,
    required this.client,
  });

  final String apiBaseUrl;
  final String accessToken;
  final http.Client client;

  @override
  State<SellerListingsPage> createState() => _SellerListingsPageState();
}

class _SellerListingsPageState extends State<SellerListingsPage> {
  final _picker = ImagePicker();
  final _uuid = const Uuid();
  final _title = TextEditingController();
  final _description = TextEditingController();
  final _price = TextEditingController();
  final _location = TextEditingController();
  List<Map<String, dynamic>> _listings = [];
  List<Map<String, dynamic>> _categories = [];
  Map<String, dynamic>? _selected;
  String? _categoryId;
  String? _error;
  String? _message;
  bool _loading = true;
  bool _busy = false;

  Map<String, String> get _headers => {
    'Authorization': 'Bearer ${widget.accessToken}',
    'Content-Type': 'application/json',
  };

  @override
  void initState() { super.initState(); _load(); }

  @override
  void dispose() {
    _title.dispose(); _description.dispose(); _price.dispose(); _location.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final responses = await Future.wait([
        widget.client.get(Uri.parse('${widget.apiBaseUrl}/listings/my'), headers: _headers),
        widget.client.get(Uri.parse('${widget.apiBaseUrl}/categories')),
      ]);
      if (responses.any((response) => response.statusCode != 200)) {
        throw Exception(marketString(context, en: 'Your listings could not be loaded.', am: 'የእርስዎን ዝርዝሮች መጫን አልተቻለም።', mdy: ''));
      }
      if (!mounted) return;
      setState(() {
        _listings = (jsonDecode(responses[0].body) as List<dynamic>).cast<Map<String, dynamic>>();
        _categories = (jsonDecode(responses[1].body) as List<dynamic>).cast<Map<String, dynamic>>();
      });
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _select(Map<String, dynamic> listing) {
    setState(() {
      _selected = listing;
      _categoryId = listing['category_id'] as String?;
      _title.text = listing['title'] as String? ?? '';
      _description.text = listing['description'] as String? ?? '';
      _price.text = (((listing['price_minor'] as num?) ?? 0) / 100).toStringAsFixed(2);
      _location.text = listing['location'] as String? ?? '';
      _message = null; _error = null;
    });
  }

  Future<void> _save() async {
    final listing = _selected;
    final amount = double.tryParse(_price.text.trim());
    if (listing == null || listing['status'] != 'draft') {
      setState(() => _error = marketString(context, en: 'Only your server-side draft listings can be edited.', am: 'በአገልጋዩ ላይ ያሉ የራስዎን ረቂቅ ዝርዝሮች ብቻ ማስተካከል ይችላሉ።', mdy: ''));
      return;
    }
    if (_title.text.trim().length < 3 || _location.text.trim().length < 2 ||
        amount == null || amount < 0 || _categoryId == null) {
      setState(() => _error = marketString(context, en: 'Enter a valid title, category, price and location.', am: 'ትክክለኛ ርዕስ፣ ምድብ፣ ዋጋ እና አካባቢ ያስገቡ።', mdy: ''));
      return;
    }
    setState(() { _busy = true; _error = null; _message = null; });
    try {
      final response = await widget.client.patch(
        Uri.parse('${widget.apiBaseUrl}/listings/${listing['id']}'),
        headers: _headers,
        body: jsonEncode({
          'category_id': _categoryId,
          'title': _title.text.trim(),
          'description': _description.text.trim(),
          'price_minor': (amount * 100).round(),
          'location_label': _location.text.trim(),
        }),
      );
      if (response.statusCode != 200) throw Exception(marketString(context, en: 'Draft update failed (${response.statusCode}).', am: 'ረቂቁን ማዘመን አልተሳካም (${response.statusCode})።', mdy: ''));
      final updated = jsonDecode(response.body) as Map<String, dynamic>;
      setState(() { _selected = updated; _message = marketString(context, en: 'Draft changes saved.', am: 'የረቂቁ ለውጦች ተቀምጠዋል።', mdy: ''); });
      await _load();
      if (mounted) _select(updated);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _submit() async {
    final listing = _selected;
    if (listing == null || listing['status'] != 'draft') return;
    setState(() { _busy = true; _error = null; _message = null; });
    try {
      final response = await widget.client.post(
        Uri.parse('${widget.apiBaseUrl}/listings/${listing['id']}/submit'),
        headers: _headers,
      );
      if (response.statusCode != 200) throw Exception(marketString(context, en: 'Submission failed (${response.statusCode}).', am: 'ለግምገማ መላክ አልተሳካም (${response.statusCode})።', mdy: ''));
      setState(() => _message = marketString(context, en: 'Submitted for moderation. It is not public until approved.', am: 'ለግምገማ ተልኳል። እስኪፈቀድ ድረስ ለሕዝብ አይታይም።', mdy: ''));
      await _load();
      if (mounted) setState(() => _selected = null);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _addPhoto() async {
    final listing = _selected;
    if (listing == null || listing['status'] != 'draft') return;
    final currentImages = (listing['images'] as List<dynamic>? ?? []);
    if (currentImages.length >= 5) {
      setState(() => _error = marketString(context, en: 'A listing can contain up to five photos.', am: 'አንድ ዝርዝር እስከ 5 ፎቶዎችን ሊይዝ ይችላል።', mdy: ''));
      return;
    }
    final picked = await _picker.pickImage(source: ImageSource.gallery, maxWidth: 2400,
      maxHeight: 2400, imageQuality: 88);
    if (picked == null) return;
    setState(() { _busy = true; _error = null; });
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('${widget.apiBaseUrl}/listings/${listing['id']}/images'),
      )
        ..headers['Authorization'] = 'Bearer ${widget.accessToken}'
        ..fields['client_image_id'] = _uuid.v4()
        ..files.add(await http.MultipartFile.fromPath('file', picked.path));
      final streamed = await widget.client.send(request);
      final response = await http.Response.fromStream(streamed);
      if (response.statusCode != 201) throw Exception(marketString(context, en: 'Photo upload failed (${response.statusCode}).', am: 'ፎቶውን መጫን አልተሳካም (${response.statusCode})።', mdy: ''));
      await _load();
      final updated = _listings.firstWhere((item) => item['id'] == listing['id']);
      if (mounted) _select(updated);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(marketString(context, en: 'My listings', am: 'የእኔ ዝርዝሮች', mdy: '')), actions: [
      IconButton(onPressed: _loading ? null : _load, icon: const Icon(Icons.refresh)),
    ]),
    body: _loading ? const Center(child: CircularProgressIndicator())
      : ListView(padding: const EdgeInsets.all(16), children: [
        if (_error != null) Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
        if (_message != null) Text(_message!),
        Text(marketString(context, en: 'Your listings', am: 'የእርስዎ ዝርዝሮች', mdy: ''), style: Theme.of(context).textTheme.titleLarge),
        if (_listings.isEmpty) Text(marketString(context, en: 'You have not created any server listings yet.', am: 'እስካሁን በሰርቨሩ ላይ ምንም ዝርዝር አልፈጠሩም።', mdy: '')),
        ..._listings.map((listing) => ListTile(
          title: Text(listing['title'] as String? ?? 'Untitled'),
          subtitle: Text('${listing['location'] ?? ''} · ${listing['status']}'),
          selected: _selected?['id'] == listing['id'],
          onTap: () => _select(listing),
        )),
        if (_selected != null) ...[
          const Divider(),
          Text(marketString(context, en: 'Edit draft', am: 'ረቂቁን አስተካክል', mdy: ''), style: Theme.of(context).textTheme.titleLarge),
          DropdownButtonFormField<String>(
            value: _categoryId,
            decoration: InputDecoration(labelText: marketString(context, en: 'Category', am: 'ምድብ', mdy: '')),
            items: _categories.map((category) => DropdownMenuItem<String>(
              value: category['id'] as String, child: Text(category['name'] as String),
            )).toList(),
            onChanged: _selected!['status'] == 'draft' ? (value) => setState(() => _categoryId = value) : null,
          ),
          TextField(controller: _title, decoration: InputDecoration(labelText: marketString(context, en: 'Title', am: 'ርዕስ', mdy: '')),
            enabled: _selected!['status'] == 'draft'),
          TextField(controller: _description, decoration: InputDecoration(labelText: marketString(context, en: 'Description', am: 'መግለጫ', mdy: '')),
            maxLines: 3, enabled: _selected!['status'] == 'draft'),
          TextField(controller: _price, decoration: InputDecoration(labelText: marketString(context, en: 'Price (ETB)', am: 'ዋጋ (ብር)', mdy: '')),
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            enabled: _selected!['status'] == 'draft'),
          TextField(controller: _location, decoration: InputDecoration(labelText: marketString(context, en: 'Location', am: 'አካባቢ', mdy: '')),
            enabled: _selected!['status'] == 'draft'),
          Text(marketString(context, en: '${(_selected!['images'] as List<dynamic>? ?? []).length}/5 photos', am: '${(_selected!['images'] as List<dynamic>? ?? []).length}/5 ፎቶዎች', mdy: '')),
          if (_selected!['status'] == 'draft') Wrap(spacing: 8, children: [
            FilledButton(onPressed: _busy ? null : _save, child: Text(marketString(context, en: 'Save changes', am: 'ለውጦችን አስቀምጥ', mdy: ''))),
            OutlinedButton(onPressed: _busy ? null : _addPhoto, child: Text(marketString(context, en: 'Add photo', am: 'ፎቶ ጨምር', mdy: ''))),
            FilledButton.tonal(onPressed: _busy ? null : _submit, child: Text(marketString(context, en: 'Submit for review', am: 'ለግምገማ ላክ', mdy: ''))),
          ]),
          if (_selected!['status'] != 'draft')
            Text(marketString(context, en: 'This listing is ${_selected!['status']}; editing and resubmission are disabled.', am: 'የዚህ ዝርዝር ሁኔታ ${_selected!['status']} ነው፤ ማስተካከልና እንደገና መላክ ተዘግቷል።', mdy: '')),
        ],
      ]),
  );
}


class SellerProfileSetupPage extends StatefulWidget {
  const SellerProfileSetupPage({
    super.key,
    required this.apiBaseUrl,
    required this.accessToken,
    required this.client,
    required this.onComplete,
  });

  final String apiBaseUrl;
  final String accessToken;
  final http.Client client;
  final VoidCallback onComplete;

  @override
  State<SellerProfileSetupPage> createState() => _SellerProfileSetupPageState();
}

class _SellerProfileSetupPageState extends State<SellerProfileSetupPage> {
  final _name = TextEditingController();
  final _location = TextEditingController(text: 'Koybe');
  bool _busy = false;
  String? _error;

  @override
  void dispose() { _name.dispose(); _location.dispose(); super.dispose(); }

  Future<void> _createProfile() async {
    if (_name.text.trim().length < 2 || _location.text.trim().length < 2) {
      setState(() => _error = marketString(context, en: 'Enter a public seller name and location.', am: 'የሻጭ ስምና አካባቢ ያስገቡ።', mdy: ''));
      return;
    }
    setState(() { _busy = true; _error = null; });
    try {
      final response = await widget.client.post(
        Uri.parse('${widget.apiBaseUrl}/sellers/me'),
        headers: {
          'Authorization': 'Bearer ${widget.accessToken}',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'public_name': _name.text.trim(),
          'location_label': _location.text.trim(),
        }),
      );
      if (response.statusCode != 201) {
        throw Exception(response.statusCode == 409
          ? marketString(context, en: 'A seller profile already exists. Sign out and sign in again.', am: 'የሻጭ መገለጫ አስቀድሞ አለ። ይውጡና እንደገና ይግቡ።', mdy: '')
          : marketString(context, en: 'Seller profile setup failed (${response.statusCode}).', am: 'የሻጭ መገለጫ ማዘጋጀት አልተሳካም (${response.statusCode})።', mdy: ''));
      }
      widget.onComplete();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(marketString(context, en: 'Set up seller profile', am: 'የሻጭ መገለጫ ያዘጋጁ', mdy: ''))),
    body: ListView(padding: const EdgeInsets.all(24), children: [
      MarketBrandPanel(
        title: marketString(context, en: 'Meet your local customers.', am: 'ከአካባቢዎ ደንበኞች ጋር ይገናኙ።', mdy: ''),
        subtitle: marketString(context, en: 'Set up a clear public seller identity so buyers know who they are contacting.', am: 'ገዢዎች ማንን እንደሚያነጋግሩ እንዲያውቁ የሻጭ መገለጫዎን ያዘጋጁ።', mdy: ''),
      ),
      const SizedBox(height: 20),
      TextField(controller: _name, decoration: InputDecoration(
        labelText: marketString(context, en: 'Public seller name', am: 'የሻጭ ስም', mdy: ''), prefixIcon: Icon(Icons.storefront_outlined))),
      const SizedBox(height: 10),
      TextField(controller: _location, decoration: InputDecoration(
        labelText: marketString(context, en: 'Location', am: 'አካባቢ', mdy: ''), prefixIcon: Icon(Icons.location_on_outlined))),
      const SizedBox(height: 16),
      FilledButton(
        onPressed: _busy ? null : _createProfile,
        child: Text(_busy ? marketString(context, en: 'Saving…', am: 'በማስቀመጥ ላይ…', mdy: '') : marketString(context, en: 'Create seller profile', am: 'የሻጭ መገለጫ ፍጠር', mdy: '')),
      ),
      if (_error != null) Padding(
        padding: const EdgeInsets.only(top: 12),
        child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
      ),
    ]),
  );
}


