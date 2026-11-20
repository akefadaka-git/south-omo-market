import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:uuid/uuid.dart';

import 'l10n/market_strings.dart';
import 'design/market_design_system.dart';

class MarketplaceDiscoveryPage extends StatefulWidget {
  const MarketplaceDiscoveryPage({
    super.key,
    required this.apiBaseUrl,
    required this.client,
    this.onSellerSignIn,
  });

  final String apiBaseUrl;
  final http.Client client;
  final void Function(BuildContext context)? onSellerSignIn;

  @override
  State<MarketplaceDiscoveryPage> createState() => _MarketplaceDiscoveryPageState();
}

class _MarketplaceDiscoveryPageState extends State<MarketplaceDiscoveryPage> {
  List<Map<String, dynamic>> _categories = [];
  List<Map<String, dynamic>> _locations = [];
  List<Map<String, dynamic>> _listings = [];
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  String? _categoryId;
  String? _locationId;
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final deviceLanguage = WidgetsBinding.instance.platformDispatcher.locale.languageCode;
      final categoryLanguage = deviceLanguage == 'am' || deviceLanguage == 'mdy'
          ? deviceLanguage
          : 'en';
      final listingUri = Uri.parse('${widget.apiBaseUrl}/listings').replace(
        queryParameters: {
          'limit': '50',
          if (_categoryId != null) 'category_id': _categoryId!,
          if (_locationId != null) 'location_id': _locationId!,
        },
      );
      final results = await Future.wait([
        widget.client.get(Uri.parse('${widget.apiBaseUrl}/categories?lang=$categoryLanguage')),
        widget.client.get(listingUri),
        widget.client.get(Uri.parse('${widget.apiBaseUrl}/locations?lang=$categoryLanguage')),
      ]);
      if (results.any((response) => response.statusCode != 200)) {
        throw Exception('Marketplace listings could not be loaded.');
      }
      final categories = (jsonDecode(results[0].body) as List<dynamic>)
          .cast<Map<String, dynamic>>();
      final listings = (jsonDecode(results[1].body) as List<dynamic>)
          .cast<Map<String, dynamic>>();
      final locations = (jsonDecode(results[2].body) as List<dynamic>)
          .cast<Map<String, dynamic>>()
          .where((location) => location['level'] == 'town' || location['level'] == 'locality')
          .toList();
      if (!mounted) return;
      setState(() {
        _categories = categories;
        _locations = locations;
        _listings = listings;
      });
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final query = _searchQuery.trim().toLowerCase();
    final visibleListings = _listings.where((item) {
      if (query.isEmpty) return true;
      final searchable = '${item['title'] ?? ''} ${item['location'] ?? ''}'.toLowerCase();
      return searchable.contains(query);
    }).toList();

    return Scaffold(
    appBar: AppBar(title: Row(mainAxisSize: MainAxisSize.min, children: [
      const MarketBrandMark(size: 34),
      const SizedBox(width: 10),
      Flexible(child: Text(marketString(context, en: 'South Omo Market', am: 'ደቡብ ኦሞ ገበያ', mdy: ''))),
    ]), actions: [
      if (widget.onSellerSignIn != null)
        IconButton(
          tooltip: marketString(context, en: 'Seller sign in', am: 'የሻጭ መግቢያ', mdy: ''),
          onPressed: () => widget.onSellerSignIn!(context),
          icon: const Icon(Icons.storefront_outlined),
        ),
      IconButton(tooltip: marketString(context, en: 'Refresh listings', am: 'ዝርዝሮችን አድስ', mdy: ''), onPressed: _loading ? null : _load,
        icon: const Icon(Icons.refresh)),
    ]),
    body: Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(14, 10, 14, 4),
        child: MarketBrandPanel(
          title: marketString(context, en: 'Trade closer. Grow together.', am: 'በቅርብ ይገበያዩ፤ አብረው ያድጉ።', mdy: ''),
          subtitle: marketString(context, en: 'Discover goods, local skills and trusted businesses across South Omo.', am: 'በደቡብ ኦሞ ያሉ ምርቶችን፣ ክህሎቶችን እና ንግዶችን ያግኙ።', mdy: ''),
        ),
      ),
      Padding(
        padding: const EdgeInsets.fromLTRB(12, 12, 12, 8),
        child: TextField(
          key: const Key('marketplace-search'),
          controller: _searchController,
          onChanged: (value) => setState(() => _searchQuery = value),
          textInputAction: TextInputAction.search,
          decoration: InputDecoration(
            labelText: marketString(context, en: 'Search products and services', am: 'ምርቶችን እና አገልግሎቶችን ፈልግ', mdy: ''),
            prefixIcon: const Icon(Icons.search),
            suffixIcon: _searchQuery.isEmpty ? null : IconButton(
              tooltip: 'Clear search',
              onPressed: () {
                _searchController.clear();
                setState(() => _searchQuery = '');
              },
              icon: const Icon(Icons.close),
            ),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(16)),
          ),
        ),
      ),
      Padding(
        padding: const EdgeInsets.all(12),
        child: DropdownButtonFormField<String>(
          value: _categoryId,
          decoration: InputDecoration(labelText: marketString(context, en: 'Filter by category', am: 'በምድብ አጣራ', mdy: '')),
          items: [
            DropdownMenuItem<String>(value: null, child: Text(marketString(context, en: 'All categories', am: 'ሁሉም ምድቦች', mdy: ''))),
            ..._categories.map((category) => DropdownMenuItem<String>(
              value: category['id'] as String,
              child: Text(category['name'] as String),
            )),
          ],
          onChanged: (value) { setState(() => _categoryId = value); _load(); },
        ),
      ),
      Padding(
        padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
        child: DropdownButtonFormField<String>(
          value: _locationId,
          decoration: InputDecoration(labelText: marketString(context, en: 'Filter by location', am: 'በአካባቢ አጣራ', mdy: '')),
          items: [
            DropdownMenuItem<String>(value: null, child: Text(marketString(context, en: 'All locations', am: 'ሁሉም አካባቢዎች', mdy: ''))),
            ..._locations.map((location) => DropdownMenuItem<String>(
              value: location['id'] as String,
              child: Text(location['name'] as String),
            )),
          ],
          onChanged: (value) { setState(() => _locationId = value); _load(); },
        ),
      ),
      Expanded(child: _loading
        ? const Center(child: CircularProgressIndicator())
        : _error != null
          ? Center(child: Text(_error!, textAlign: TextAlign.center))
          : visibleListings.isEmpty
            ? Center(child: Text(
                query.isEmpty
                  ? marketString(context, en: 'No published listings found.', am: 'የታተሙ ማስታወቂያዎች አልተገኙም።', mdy: '')
                  : marketString(context, en: 'No matches. Try another search or clear the filters.', am: 'ውጤት አልተገኘም። ሌላ ፍለጋ ወይም ማጣሪያ ይሞክሩ።', mdy: ''),
                textAlign: TextAlign.center,
              ))
            : RefreshIndicator(
              onRefresh: _load,
              child: ListView.builder(
                itemCount: visibleListings.length,
                itemBuilder: (context, index) {
                  final item = visibleListings[index];
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
      setState(() => _error = 'Enter a message of up to 2,000 characters.');
      return;
    }
    setState(() { _sending = true; _error = null; _notice = null; });
    try {
      final token = await showDialog<String>(
        context: context,
        builder: (_) => BuyerAuthDialog(apiBaseUrl: widget.apiBaseUrl, client: widget.client),
      );
      if (token == null) {
        if (mounted) setState(() => _error = 'Buyer sign-in was not completed. Please try again.');
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
        throw Exception('You cannot inquire about your own listing.');
      }
      if (response.statusCode != 201) {
        throw Exception(response.statusCode == 404
          ? 'This listing is no longer available.'
          : 'Your inquiry could not be sent (${response.statusCode}).');
      }
      if (mounted) {
        _messageController.clear();
        setState(() => _notice = 'Your inquiry was sent to the seller.');
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
              const SizedBox(height: 24),
              Text('Contact seller', style: Theme.of(context).textTheme.titleLarge),
              const Text('Sign in or create a buyer account to send your inquiry. Your registered phone number is shared with the seller.'),
              TextField(
                key: const Key('buyer-inquiry-message'),
                controller: _messageController,
                maxLines: 4,
                maxLength: 2000,
                decoration: const InputDecoration(
                  labelText: 'Your message',
                  hintText: 'Ask about availability, condition or collection',
                  border: OutlineInputBorder(),
                ),
              ),
              FilledButton.icon(
                onPressed: _sending ? null : _sendInquiry,
                icon: const Icon(Icons.send),
                label: Text(_sending ? 'Sending…' : 'Send inquiry'),
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
      setState(() => _error = 'Enter a public seller name and location.');
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
          ? 'A seller profile already exists. Sign out and sign in again.'
          : 'Seller profile setup failed (${response.statusCode}).');
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
    appBar: AppBar(title: const Text('Set up seller profile')),
    body: ListView(padding: const EdgeInsets.all(24), children: [
      const Text('Create your seller profile before managing listings and inquiries.'),
      TextField(controller: _name, decoration: const InputDecoration(labelText: 'Public seller name')),
      TextField(controller: _location, decoration: const InputDecoration(labelText: 'Location')),
      const SizedBox(height: 16),
      FilledButton(
        onPressed: _busy ? null : _createProfile,
        child: Text(_busy ? 'Saving…' : 'Create seller profile'),
      ),
      if (_error != null) Padding(
        padding: const EdgeInsets.only(top: 12),
        child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
      ),
    ]),
  );
}


class BuyerAuthDialog extends StatefulWidget {
  const BuyerAuthDialog({super.key, required this.apiBaseUrl, required this.client});
  final String apiBaseUrl;
  final http.Client client;

  @override
  State<BuyerAuthDialog> createState() => _BuyerAuthDialogState();
}

class _BuyerAuthDialogState extends State<BuyerAuthDialog> {
  final _phone = TextEditingController();
  final _name = TextEditingController();
  final _password = TextEditingController();
  bool _register = false;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _phone.dispose(); _name.dispose(); _password.dispose(); super.dispose();
  }

  Future<void> _authenticate() async {
    if (_phone.text.trim().length < 7 || _password.text.length < 12 ||
        (_register && _name.text.trim().isEmpty)) {
      setState(() => _error = 'Enter a valid phone number, password (at least 12 characters), and display name when registering.');
      return;
    }
    setState(() { _busy = true; _error = null; });
    try {
      final base = widget.apiBaseUrl;
      if (_register) {
        final created = await widget.client.post(
          Uri.parse('$base/auth/register'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'phone_number': _phone.text.trim(),
            'display_name': _name.text.trim(),
            'password': _password.text,
          }),
        );
        if (created.statusCode != 201) {
          throw Exception(created.statusCode == 409
            ? 'That phone number is already registered. Choose sign in.'
            : 'Account registration failed (${created.statusCode}).');
        }
      }
      final response = await widget.client.post(
        Uri.parse('$base/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'phone_number': _phone.text.trim(),
          'password': _password.text,
        }),
      );
      if (response.statusCode != 200) throw Exception('Sign in failed (${response.statusCode}).');
      final token = (jsonDecode(response.body) as Map<String, dynamic>)['access_token'] as String?;
      if (token == null || token.isEmpty) throw Exception('The API did not return an access token.');
      if (mounted) Navigator.of(context, rootNavigator: true).pop<String>(token);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(_register ? 'Create buyer account' : 'Buyer sign in'),
    content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
      if (_register) TextField(key: const Key('buyer-display-name'), controller: _name, decoration: const InputDecoration(labelText: 'Display name')),
      TextField(key: const Key('buyer-phone'), controller: _phone, keyboardType: TextInputType.phone,
        decoration: const InputDecoration(labelText: 'Phone number')),
      TextField(key: const Key('buyer-password'), controller: _password, obscureText: true,
        decoration: const InputDecoration(labelText: 'Password (minimum 12 characters)')),
      if (_error != null) Padding(
        padding: const EdgeInsets.only(top: 8),
        child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
      ),
    ])),
    actions: [
      TextButton(
        onPressed: _busy ? null : () => setState(() { _register = !_register; _error = null; }),
        child: Text(_register ? 'I already have an account' : 'Create account'),
      ),
      FilledButton(onPressed: _busy ? null : _authenticate,
        child: Text(_busy ? 'Please wait…' : (_register ? 'Register and continue' : 'Sign in'))),
    ],
  );
}
