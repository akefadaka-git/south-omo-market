import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

import '../../data/local_draft_store.dart';
import '../../data/offline_sync_service.dart';
import '../../marketplace_pages.dart';
import '../../l10n/market_strings.dart';
import '../../design/market_design_system.dart';
class MarketplaceHomePage extends StatefulWidget {
  const MarketplaceHomePage({
    super.key,
    required this.apiBaseUrl,
    this.client,
  });

  final String apiBaseUrl;
  final http.Client? client;

  @override
  State<MarketplaceHomePage> createState() => _MarketplaceHomePageState();
}

class _MarketplaceHomePageState extends State<MarketplaceHomePage> {
  final _formKey = GlobalKey<FormState>();
  final _phoneController = TextEditingController();
  final _displayNameController = TextEditingController();
  final _passwordController = TextEditingController();
  late final http.Client _client;
  late final bool _ownsClient;
  String? _accessToken;
  String? _error;
  bool _needsSellerProfile = false;
  bool _register = false;
  bool _busy = false;
  bool _obscurePassword = true;

  String get _baseUrl => widget.apiBaseUrl.replaceFirst(RegExp(r'/+$'), '');

  @override
  void initState() {
    super.initState();
    _ownsClient = widget.client == null;
    _client = widget.client ?? http.Client();
  }

  @override
  void dispose() {
    _phoneController.dispose();
    _displayNameController.dispose();
    _passwordController.dispose();
    if (_ownsClient) _client.close();
    super.dispose();
  }

  Future<void> _signIn() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      if (_register) {
        final created = await _client.post(
          Uri.parse('$_baseUrl/auth/register'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'phone_number': _phoneController.text.trim(),
            'display_name': _displayNameController.text.trim(),
            'password': _passwordController.text,
          }),
        );
        if (created.statusCode != 201) {
          throw Exception(created.statusCode == 409
            ? 'That phone number is already registered.'
            : 'Seller account registration failed (${created.statusCode}).');
        }
      }
      final response = await _client.post(
        Uri.parse('$_baseUrl/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'phone_number': _phoneController.text.trim(),
          'password': _passwordController.text,
        }),
      );
      if (response.statusCode != 200) {
        throw Exception(marketString(context, en: 'Sign-in failed. Check the account details and try again.', am: 'መግባት አልተሳካም። የመለያ መረጃዎን ያረጋግጡና እንደገና ይሞክሩ።', mdy: ''));
      }
      final payload = jsonDecode(response.body) as Map<String, dynamic>;
      final token = payload['access_token'] as String?;
      if (token == null || token.isEmpty) {
        throw Exception(marketString(context, en: 'The API did not return an access token.', am: 'ከአገልጋዩ የመግቢያ ቁልፍ አልተመለሰም።', mdy: ''));
      }
      final profileResponse = await _client.get(
        Uri.parse('$_baseUrl/sellers/me'),
        headers: {'Authorization': 'Bearer $token'},
      );
      if (profileResponse.statusCode != 200 && profileResponse.statusCode != 404) {
        throw Exception(marketString(context, en: 'Could not verify seller profile.', am: 'የሻጭ መገለጫውን ማረጋገጥ አልተቻለም።', mdy: ''));
      }
      if (!mounted) return;
      setState(() {
        _accessToken = token;
        _needsSellerProfile = profileResponse.statusCode == 404;
        _passwordController.clear();
        _displayNameController.clear();
        _register = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final token = _accessToken;
    if (token != null && _needsSellerProfile) {
      return SellerProfileSetupPage(
        apiBaseUrl: _baseUrl,
        accessToken: token,
        client: _client,
        onComplete: () => setState(() => _needsSellerProfile = false),
      );
    }
    if (token != null) {
      return SellerInboxPage(
        apiBaseUrl: _baseUrl,
        accessToken: token,
        client: _client,
        onLogout: () => setState(() { _accessToken = null; _needsSellerProfile = false; }),
      );
    }

    return Scaffold(
      appBar: AppBar(title: Row(mainAxisSize: MainAxisSize.min, children: [
        MarketBrandMark(size: 34), SizedBox(width: 10), Text(marketString(context, en: 'South Omo Market', am: 'ደቡብ ኦሞ ገበያ', mdy: '')),
      ])),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 440),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  MarketBrandPanel(
                    title: marketString(context, en: 'Your shop. More local buyers.', am: 'የእርስዎ ሱቅ። ተጨማሪ የአካባቢ ገዢዎች።', mdy: ''),
                    subtitle: marketString(context, en: 'Manage your listings and buyer inquiries across South Omo.', am: 'በደቡብ ኦሞ ያሉ ዝርዝሮችዎንና የገዢ ጥያቄዎችን ያስተዳድሩ።', mdy: ''),
                  ),
                  const SizedBox(height: 22),
                  Text(
                    marketString(context, en: 'Seller sign in', am: 'የሻጭ መግቢያ', mdy: ''),
                    style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  Text(marketString(context, en: 'Sign in to view and manage inquiries about your listings.', am: 'ስለ ዝርዝሮችዎ የተላኩ ጥያቄዎችን ለማየትና ለማስተዳደር ይግቡ።', mdy: '')),
                  const SizedBox(height: 24),
                  if (_register) ...[
                    TextFormField(
                      key: const Key('seller-display-name'),
                      controller: _displayNameController,
                      decoration: InputDecoration(
                        labelText: marketString(context, en: 'Public seller name', am: 'የሻጭ ስም', mdy: ''),
                        prefixIcon: const Icon(Icons.storefront_outlined),
                      ),
                      validator: (value) => value == null || value.trim().length < 2
                        ? marketString(context, en: 'Enter at least 2 characters.', am: 'ቢያንስ 2 ፊደላት ያስገቡ።', mdy: '')
                        : null,
                    ),
                    const SizedBox(height: 12),
                  ],
                  TextFormField(
                    key: const Key('seller-phone'),
                    controller: _phoneController,
                    keyboardType: TextInputType.phone,
                    decoration: InputDecoration(
                      labelText: marketString(context, en: 'Phone number', am: 'ስልክ ቁጥር', mdy: ''),
                      prefixIcon: Icon(Icons.phone_outlined),
                    ),
                    validator: (value) =>
                        value == null || value.trim().length < 7 ? marketString(context, en: 'Enter a valid phone number', am: 'ትክክለኛ የስልክ ቁጥር ያስገቡ', mdy: '') : null,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    key: const Key('seller-password'),
                    controller: _passwordController,
                    obscureText: _obscurePassword,
                    decoration: InputDecoration(
                      labelText: marketString(context, en: 'Password', am: 'የይለፍ ቃል', mdy: ''),
                      prefixIcon: const Icon(Icons.lock_outline_rounded),
                      suffixIcon: IconButton(
                        tooltip: _obscurePassword ? 'Show password' : 'Hide password',
                        onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                        icon: Icon(_obscurePassword ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                      ),
                    ),
                    validator: (value) =>
                        value == null || value.length < 12 ? marketString(context, en: 'Password must be at least 12 characters', am: 'የይለፍ ቃሉ ቢያንስ 12 ፊደላት መሆን አለበት', mdy: '') : null,
                  ),
                  const SizedBox(height: 12),
                  TextButton(
                    onPressed: _busy ? null : () => setState(() {
                      _register = !_register;
                      _error = null;
                    }),
                    child: Text(_register
                      ? marketString(context, en: 'I already have a seller account', am: 'የሻጭ መለያ አለኝ', mdy: '')
                      : marketString(context, en: 'Create seller account', am: 'የሻጭ መለያ ፍጠር', mdy: '')),
                  ),
                  const SizedBox(height: 8),
                  FilledButton(
                    onPressed: _busy ? null : _signIn,
                    child: Text(_busy
                      ? marketString(context, en: 'Please wait…', am: 'እባክዎ ይጠብቁ…', mdy: '')
                      : (_register
                        ? marketString(context, en: 'Register and continue', am: 'ተመዝግበው ይቀጥሉ', mdy: '')
                        : marketString(context, en: 'Sign in', am: 'ግባ', mdy: ''))),
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: 12),
                    Text(_error!, key: const Key('sign-in-error'),
                        style: TextStyle(color: Theme.of(context).colorScheme.error)),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

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


class SellerDraftsPage extends StatefulWidget {
  const SellerDraftsPage({
    super.key,
    required this.apiBaseUrl,
    required this.accessToken,
    required this.client,
  });

  final String apiBaseUrl;
  final String accessToken;
  final http.Client client;

  @override
  State<SellerDraftsPage> createState() => _SellerDraftsPageState();
}

class _SellerDraftsPageState extends State<SellerDraftsPage> {
  static const _categories = <Map<String, String>>[
    {'id': '00000000-0000-4000-8000-000000000001', 'name': 'Livestock'},
    {'id': '00000000-0000-4000-8000-000000000002', 'name': 'Agriculture'},
    {'id': '00000000-0000-4000-8000-000000000003', 'name': 'Food and groceries'},
    {'id': '00000000-0000-4000-8000-000000000004', 'name': 'Shops and products'},
    {'id': '00000000-0000-4000-8000-000000000005', 'name': 'Services'},
    {'id': '00000000-0000-4000-8000-000000000006', 'name': 'Property and rentals'},
  ];

  final _store = LocalDraftStore();
  final _picker = ImagePicker();
  final _uuid = const Uuid();
  final _title = TextEditingController();
  final _description = TextEditingController();
  final _price = TextEditingController();
  final _location = TextEditingController(text: 'Koybe');
  String? _categoryId;
  String? _draftId;
  String? _clientSyncId;
  bool _selectedDraftSynced = false;
  List<Map<String, Object?>> _drafts = [];
  List<Map<String, Object?>> _images = [];
  bool _busy = false;
  String? _message;
  String? _error;
  StreamSubscription<List<ConnectivityResult>>? _connectivitySubscription;

  @override
  void initState() {
    super.initState();
    _connectivitySubscription = Connectivity().onConnectivityChanged.listen((results) {
      if (results.any((result) => result != ConnectivityResult.none)) _syncNow();
    });
    _categoryId = _categories.first['id'];
    _initialize();
  }

  Future<void> _initialize() async {
    await _reload();
    await _syncIfOnline();
  }

  Future<void> _syncIfOnline() async {
    final results = await Connectivity().checkConnectivity();
    if (!mounted) return;
    if (results.any((result) => result != ConnectivityResult.none)) {
      await _syncNow();
    }
  }

  @override
  void dispose() {
    _connectivitySubscription?.cancel();
    unawaited(_store.close());
    _title.dispose();
    _description.dispose();
    _price.dispose();
    _location.dispose();
    super.dispose();
  }

  Future<void> _reload() async {
    try {
      final drafts = await _store.allDrafts();
      if (!mounted) return;
      setState(() => _drafts = drafts);
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = marketString(context, en: 'Could not open local drafts: $error', am: 'የአካባቢ ረቂቆችን መክፈት አልተቻለም፦ $error', mdy: ''));
    }
  }

  Future<void> _saveDraft() async {
    final title = _title.text.trim();
    final location = _location.text.trim();
    final amount = double.tryParse(_price.text.trim());
    if (title.length < 3 || location.length < 2 || amount == null || amount < 0 || _categoryId == null) {
      setState(() => _error = marketString(context, en: 'Enter a title, category, valid ETB price and location.', am: 'ርዕስ፣ ምድብ፣ ትክክለኛ የብር ዋጋ እና አካባቢ ያስገቡ።', mdy: ''));
      return;
    }
    if (_selectedDraftSynced) {
      setState(() => _error = marketString(context, en: 'A synchronized server draft cannot be edited offline. Start a new draft.', am: 'ከአገልጋዩ ጋር የተመሳሰለ ረቂቅ ከመስመር ውጭ ማስተካከል አይቻልም። አዲስ ረቂቅ ይጀምሩ።', mdy: ''));
      return;
    }
    final id = _draftId ?? _uuid.v4();
    final syncId = _clientSyncId ?? id;
    await _store.saveDraft({
      'id': id,
      'client_sync_id': syncId,
      'category_id': _categoryId,
      'title': title,
      'description': _description.text.trim(),
      'price_minor': (amount * 100).round(),
      'location_label': location,
      'sync_state': 'pending',
      'last_error': null,
      'updated_at': DateTime.now().toUtc().toIso8601String(),
    });
    if (!mounted) return;
    setState(() {
      _draftId = id;
      _clientSyncId = syncId;
      _error = null;
      _message = 'Draft saved on this device. It has not been published.';
    });
    await _reload();
    await _loadImages();
  }

  Future<void> _loadImages() async {
    final id = _draftId;
    if (id == null) return;
    final images = await _store.allImages(id);
    if (mounted) setState(() => _images = images);
  }

  Future<void> _pickImage() async {
    final id = _draftId;
    if (id == null) {
      setState(() => _error = marketString(context, en: 'Save the draft before adding photos.', am: 'ፎቶ ከመጨመርዎ በፊት ረቂቁን ያስቀምጡ።', mdy: ''));
      return;
    }
    if (_selectedDraftSynced) {
      setState(() => _error = marketString(context, en: 'This server draft is synchronized and cannot be changed here.', am: 'ይህ የአገልጋይ ረቂቅ ተመሳስሏል፤ እዚህ ማስተካከል አይቻልም።', mdy: ''));
      return;
    }
    if (_images.length >= 5) {
      setState(() => _error = marketString(context, en: 'A listing can contain up to five photos.', am: 'አንድ ዝርዝር እስከ 5 ፎቶዎችን ሊይዝ ይችላል።', mdy: ''));
      return;
    }
    final picked = await _picker.pickImage(
      source: ImageSource.gallery,
      maxWidth: 2400,
      maxHeight: 2400,
      imageQuality: 88,
    );
    if (picked == null) return;
    final imageId = _uuid.v4();
    final documents = await getApplicationDocumentsDirectory();
    final imageDirectory = Directory('${documents.path}/listing_draft_images');
    await imageDirectory.create(recursive: true);
    final extension = picked.path.contains('.')
        ? picked.path.split('.').last.toLowerCase()
        : 'jpg';
    final durablePath = '${imageDirectory.path}/$imageId.$extension';
    await File(picked.path).copy(durablePath);
    await _store.addImage(id: imageId, draftId: id, localPath: durablePath);
    await _loadImages();
    if (mounted) setState(() => _message = 'Photo queued locally for upload.');
  }

  Future<void> _syncNow() async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
      _message = null;
    });
    try {
      final result = await OfflineSyncService(
        apiBaseUrl: widget.apiBaseUrl,
        accessToken: widget.accessToken,
        store: _store,
        client: widget.client,
      ).syncPending();
      await _reload();
      await _loadImages();
      if (!mounted) return;
      final selected = _drafts.where((draft) => draft['id'] == _draftId);
      setState(() {
        if (selected.isNotEmpty) _selectedDraftSynced = selected.first['sync_state'] == 'synced';
        _message = '${result.synced} draft(s) synced; ${result.failed} need retry.';
      });
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = marketString(context, en: 'Sync could not complete: $error', am: 'ማመሳሰል ሊጠናቀቅ አልቻለም፦ $error', mdy: ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _startNewDraft() {
    setState(() {
      _draftId = null;
      _clientSyncId = null;
      _selectedDraftSynced = false;
      _title.clear();
      _description.clear();
      _price.clear();
      _location.text = 'Koybe';
      _images = [];
      _error = null;
      _message = null;
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(marketString(context, en: 'Offline listing drafts', am: 'ከመስመር ውጭ የዝርዝር ረቂቆች', mdy: '')),
      actions: [
        IconButton(
          tooltip: marketString(context, en: 'Sync pending drafts', am: 'ያልተላኩ ረቂቆችን አመሳስል', mdy: ''),
          onPressed: _busy ? null : _syncNow,
          icon: const Icon(Icons.sync),
        ),
      ],
    ),
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(marketString(context, en: 'Create a listing draft', am: 'አዲስ ዝርዝር ረቂቅ ይፍጠሩ', mdy: ''), style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 8),
        DropdownButtonFormField<String>(
          value: _categoryId,
          decoration: InputDecoration(labelText: marketString(context, en: 'Category', am: 'ምድብ', mdy: '')),
          items: _categories.map((item) => DropdownMenuItem(
            value: item['id'], child: Text(item['name']!),
          )).toList(),
          onChanged: (value) => setState(() => _categoryId = value),
        ),
        const SizedBox(height: 8),
        TextField(controller: _title, decoration: InputDecoration(labelText: marketString(context, en: 'Listing title', am: 'የዝርዝር ርዕስ', mdy: ''))),
        TextField(
          controller: _description,
          decoration: InputDecoration(labelText: marketString(context, en: 'Description', am: 'መግለጫ', mdy: '')),
          maxLines: 3,
        ),
        TextField(
          controller: _price,
          decoration: InputDecoration(labelText: marketString(context, en: 'Price (ETB)', am: 'ዋጋ (ብር)', mdy: '')),
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
        ),
        TextField(controller: _location, decoration: InputDecoration(labelText: marketString(context, en: 'Location', am: 'አካባቢ', mdy: ''))),
        const SizedBox(height: 12),
        Wrap(spacing: 8, children: [
          FilledButton.icon(
            onPressed: _busy ? null : _saveDraft,
            icon: const Icon(Icons.save_outlined),
            label: Text(marketString(context, en: 'Save draft offline', am: 'ረቂቁን ከመስመር ውጭ አስቀምጥ', mdy: '')),
          ),
          OutlinedButton.icon(
            onPressed: _busy ? null : _pickImage,
            icon: const Icon(Icons.add_photo_alternate_outlined),
            label: Text('Add photo (${_images.length}/5)'),
          ),
          TextButton(onPressed: _startNewDraft, child: Text(marketString(context, en: 'New draft', am: 'አዲስ ረቂቅ', mdy: ''))),
        ]),
        if (_message != null) Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(_message!, style: TextStyle(color: Theme.of(context).colorScheme.primary)),
        ),
        if (_error != null) Padding(
          padding: const EdgeInsets.only(top: 8),
          child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
        ),
        const Divider(height: 28),
        Row(children: [
          Expanded(child: Text(marketString(context, en: 'Saved on this device', am: 'በዚህ መሣሪያ ላይ የተቀመጡ', mdy: ''), style: Theme.of(context).textTheme.titleMedium)),
          TextButton(onPressed: _reload, child: Text(marketString(context, en: 'Refresh', am: 'አድስ', mdy: ''))),
        ]),
        if (_drafts.isEmpty)
          Text(marketString(context, en: 'No local drafts yet.', am: 'እስካሁን የአካባቢ ረቂቅ የለም።', mdy: ''))
        else
          ..._drafts.map((draft) => Card(
            child: ListTile(
              title: Text(draft['title'] as String),
              subtitle: Text('${draft['location_label']} · ${draft['sync_state']}'
                '${draft['last_error'] == null ? '' : '\n${draft['last_error']}'}'),
              trailing: Icon(draft['sync_state'] == 'synced' ? Icons.cloud_done : Icons.cloud_upload_outlined),
              onTap: () async {
                setState(() {
                  _draftId = draft['id'] as String;
                  _clientSyncId = draft['client_sync_id'] as String?;
                  _selectedDraftSynced = draft['sync_state'] == 'synced';
                  _categoryId = draft['category_id'] as String?;
                  _title.text = draft['title'] as String;
                  _description.text = draft['description'] as String? ?? '';
                  _price.text = ((draft['price_minor'] as int) / 100).toStringAsFixed(2);
                  _location.text = draft['location_label'] as String;
                });
                await _loadImages();
              },
            ),
          )),
        const SizedBox(height: 12),
        FilledButton.tonal(
          onPressed: _busy ? null : _syncNow,
          child: Text(_busy ? marketString(context, en: 'Synchronizing…', am: 'በማመሳሰል ላይ…', mdy: '') : marketString(context, en: 'Sync pending drafts and photos', am: 'ቀጣይ ረቂቆችንና ፎቶዎችን አመሳስል', mdy: '')),
        ),
        const SizedBox(height: 8),
        Text(marketString(context, en: 'Drafts remain local until synchronization succeeds. Synchronization creates server-side drafts only; publishing still requires seller submission and administrator moderation.', am: 'ረቂቆች ማመሳሰል እስኪሳካ ድረስ በመሣሪያው ላይ ይቆያሉ። ማመሳሰል በአገልጋዩ ላይ ረቂቅ ብቻ ይፈጥራል፤ ለሕዝብ ከመታየቱ በፊት የሻጭ ማቅረብና የአስተዳዳሪ ግምገማ ያስፈልጋል።', mdy: '')),
      ],
    ),
  );
}
