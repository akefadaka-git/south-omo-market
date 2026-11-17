import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:uuid/uuid.dart';

class MarketplaceDiscoveryPage extends StatefulWidget {
  const MarketplaceDiscoveryPage({
    super.key,
    required this.apiBaseUrl,
    required this.client,
  });

  final String apiBaseUrl;
  final http.Client client;

  @override
  State<MarketplaceDiscoveryPage> createState() => _MarketplaceDiscoveryPageState();
}

class _MarketplaceDiscoveryPageState extends State<MarketplaceDiscoveryPage> {
  List<Map<String, dynamic>> _categories = [];
  List<Map<String, dynamic>> _listings = [];
  String? _categoryId;
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final results = await Future.wait([
        widget.client.get(Uri.parse('${widget.apiBaseUrl}/categories')),
        widget.client.get(Uri.parse(
          '${widget.apiBaseUrl}/listings?limit=50${_categoryId == null ? '' : '&category_id=$_categoryId'}',
        )),
      ]);
      if (results.any((response) => response.statusCode != 200)) {
        throw Exception('Marketplace listings could not be loaded.');
      }
      final categories = (jsonDecode(results[0].body) as List<dynamic>)
          .cast<Map<String, dynamic>>();
      final listings = (jsonDecode(results[1].body) as List<dynamic>)
          .cast<Map<String, dynamic>>();
      if (!mounted) return;
      setState(() { _categories = categories; _listings = listings; });
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Discover listings'), actions: [
      IconButton(tooltip: 'Refresh listings', onPressed: _loading ? null : _load,
        icon: const Icon(Icons.refresh)),
    ]),
    body: Column(children: [
      Padding(
        padding: const EdgeInsets.all(12),
        child: DropdownButtonFormField<String>(
          value: _categoryId,
          decoration: const InputDecoration(labelText: 'Filter by category'),
          items: [
            const DropdownMenuItem<String>(value: null, child: Text('All categories')),
            ..._categories.map((category) => DropdownMenuItem<String>(
              value: category['id'] as String,
              child: Text(category['name'] as String),
            )),
          ],
          onChanged: (value) { setState(() => _categoryId = value); _load(); },
        ),
      ),
      Expanded(child: _loading
        ? const Center(child: CircularProgressIndicator())
        : _error != null
          ? Center(child: Text(_error!, textAlign: TextAlign.center))
          : _listings.isEmpty
            ? const Center(child: Text('No published listings found.'))
            : RefreshIndicator(
              onRefresh: _load,
              child: ListView.builder(
                itemCount: _listings.length,
                itemBuilder: (context, index) {
                  final item = _listings[index];
                  return Card(
                    margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    child: ListTile(
                      title: Text(item['title'] as String? ?? 'Listing'),
                      subtitle: Text(
                        '${item['location'] ?? ''} · ${((item['price_minor'] as num?) ?? 0) / 100} ETB',
                      ),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
                        builder: (_) => ListingDetailPage(
                          apiBaseUrl: widget.apiBaseUrl,
                          client: widget.client,
                          listingId: item['id'] as String,
                        ),
                      )),
                    ),
                  );
                },
              ),
            ),
      ),
    ]),
  );
}

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
  String? _error;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try {
      final response = await widget.client.get(
        Uri.parse('${widget.apiBaseUrl}/listings/${widget.listingId}'),
      );
      if (response.statusCode != 200) throw Exception('Listing is no longer available.');
      if (mounted) setState(() => _listing = jsonDecode(response.body) as Map<String, dynamic>);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    }
  }

  @override
  Widget build(BuildContext context) {
    final listing = _listing;
    return Scaffold(
      appBar: AppBar(title: const Text('Listing details')),
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
                    errorBuilder: (_, __, ___) => const SizedBox(
                      height: 80, child: Center(child: Text('Photo unavailable')),
                    ),
                  ),
                ),
              Text(listing['description'] as String? ?? ''),
            ]),
    );
  }
}

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
        throw Exception('Your listings could not be loaded.');
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
      setState(() => _error = 'Only your server-side draft listings can be edited.');
      return;
    }
    if (_title.text.trim().length < 3 || _location.text.trim().length < 2 ||
        amount == null || amount < 0 || _categoryId == null) {
      setState(() => _error = 'Enter a valid title, category, price and location.');
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
      if (response.statusCode != 200) throw Exception('Draft update failed (${response.statusCode}).');
      final updated = jsonDecode(response.body) as Map<String, dynamic>;
      setState(() { _selected = updated; _message = 'Draft changes saved.'; });
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
      if (response.statusCode != 200) throw Exception('Submission failed (${response.statusCode}).');
      setState(() => _message = 'Submitted for moderation. It is not public until approved.');
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
      setState(() => _error = 'A listing can contain up to five photos.');
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
      if (response.statusCode != 201) throw Exception('Photo upload failed (${response.statusCode}).');
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
    appBar: AppBar(title: const Text('My listings'), actions: [
      IconButton(onPressed: _loading ? null : _load, icon: const Icon(Icons.refresh)),
    ]),
    body: _loading ? const Center(child: CircularProgressIndicator())
      : ListView(padding: const EdgeInsets.all(16), children: [
        if (_error != null) Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
        if (_message != null) Text(_message!),
        Text('Your listings', style: Theme.of(context).textTheme.titleLarge),
        if (_listings.isEmpty) const Text('You have not created any server listings yet.'),
        ..._listings.map((listing) => ListTile(
          title: Text(listing['title'] as String? ?? 'Untitled'),
          subtitle: Text('${listing['location'] ?? ''} · ${listing['status']}'),
          selected: _selected?['id'] == listing['id'],
          onTap: () => _select(listing),
        )),
        if (_selected != null) ...[
          const Divider(),
          Text('Edit draft', style: Theme.of(context).textTheme.titleLarge),
          DropdownButtonFormField<String>(
            value: _categoryId,
            decoration: const InputDecoration(labelText: 'Category'),
            items: _categories.map((category) => DropdownMenuItem<String>(
              value: category['id'] as String, child: Text(category['name'] as String),
            )).toList(),
            onChanged: _selected!['status'] == 'draft' ? (value) => setState(() => _categoryId = value) : null,
          ),
          TextField(controller: _title, decoration: const InputDecoration(labelText: 'Title'),
            enabled: _selected!['status'] == 'draft'),
          TextField(controller: _description, decoration: const InputDecoration(labelText: 'Description'),
            maxLines: 3, enabled: _selected!['status'] == 'draft'),
          TextField(controller: _price, decoration: const InputDecoration(labelText: 'Price (ETB)'),
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            enabled: _selected!['status'] == 'draft'),
          TextField(controller: _location, decoration: const InputDecoration(labelText: 'Location'),
            enabled: _selected!['status'] == 'draft'),
          Text('${(_selected!['images'] as List<dynamic>? ?? []).length}/5 photos'),
          if (_selected!['status'] == 'draft') Wrap(spacing: 8, children: [
            FilledButton(onPressed: _busy ? null : _save, child: const Text('Save changes')),
            OutlinedButton(onPressed: _busy ? null : _addPhoto, child: const Text('Add photo')),
            FilledButton.tonal(onPressed: _busy ? null : _submit, child: const Text('Submit for review')),
          ]),
          if (_selected!['status'] != 'draft')
            Text('This listing is ${_selected!['status']}; editing and resubmission are disabled.'),
        ],
      ]),
  );
}
