import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

import 'data/local_draft_store.dart';
import 'data/offline_sync_service.dart';

const defaultApiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000/api/v1',
);

void main() => runApp(const SouthOmoMarketApp());

class SouthOmoMarketApp extends StatelessWidget {
  const SouthOmoMarketApp({
    super.key,
    this.apiBaseUrl = defaultApiBaseUrl,
    this.client,
  });

  final String apiBaseUrl;
  final http.Client? client;

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'South Omo Market',
        debugShowCheckedModeBanner: false,
        supportedLocales: const [Locale('am'), Locale('en'), Locale('mdy')],
        localizationsDelegates: GlobalMaterialLocalizations.delegates,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF356859)),
          useMaterial3: true,
        ),
        home: MarketplaceHomePage(apiBaseUrl: apiBaseUrl, client: client),
      );
}

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
  final _passwordController = TextEditingController();
  late final http.Client _client;
  late final bool _ownsClient;
  String? _accessToken;
  String? _error;
  bool _busy = false;

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
      final response = await _client.post(
        Uri.parse('$_baseUrl/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'phone_number': _phoneController.text.trim(),
          'password': _passwordController.text,
        }),
      );
      if (response.statusCode != 200) {
        throw Exception('Sign-in failed. Check the account details and try again.');
      }
      final payload = jsonDecode(response.body) as Map<String, dynamic>;
      final token = payload['access_token'] as String?;
      if (token == null || token.isEmpty) {
        throw Exception('The API did not return an access token.');
      }
      if (!mounted) return;
      setState(() {
        _accessToken = token;
        _passwordController.clear();
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
    if (token != null) {
      return SellerInboxPage(
        apiBaseUrl: _baseUrl,
        accessToken: token,
        client: _client,
        onLogout: () => setState(() => _accessToken = null),
      );
    }

    return Scaffold(
      appBar: AppBar(title: const Text('South Omo Market')),
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
                  const Text(
                    'Seller sign in',
                    style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  const Text('Sign in to view and manage inquiries about your listings.'),
                  const SizedBox(height: 24),
                  TextFormField(
                    key: const Key('seller-phone'),
                    controller: _phoneController,
                    keyboardType: TextInputType.phone,
                    decoration: const InputDecoration(labelText: 'Phone number'),
                    validator: (value) =>
                        value == null || value.trim().length < 7 ? 'Enter a valid phone number' : null,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    key: const Key('seller-password'),
                    controller: _passwordController,
                    obscureText: true,
                    decoration: const InputDecoration(labelText: 'Password'),
                    validator: (value) =>
                        value == null || value.length < 12 ? 'Password must be at least 12 characters' : null,
                  ),
                  const SizedBox(height: 20),
                  FilledButton(
                    onPressed: _busy ? null : _signIn,
                    child: Text(_busy ? 'Signing in…' : 'Sign in'),
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
        throw Exception('A seller profile is required to use the inquiry inbox.');
      }
      if (response.statusCode != 200) throw Exception('Could not load seller inquiries.');
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
      if (response.statusCode != 200) throw Exception('Could not update inquiry status.');
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
          title: const Text('Seller inquiry inbox'),
          actions: [
            IconButton(
              tooltip: 'Offline listing drafts',
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
              tooltip: 'Refresh',
              onPressed: _loading ? null : _loadInbox,
              icon: const Icon(Icons.refresh),
            ),
            IconButton(
              tooltip: 'Sign out',
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
                          FilledButton(onPressed: _loadInbox, child: const Text('Retry')),
                        ],
                      ),
                    ),
                  )
                : _inquiries.isEmpty
                    ? const Center(child: Text('No inquiries yet.'))
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
                                    Text('Status: $status'),
                                    const SizedBox(height: 8),
                                    Wrap(
                                      spacing: 8,
                                      children: [
                                        if (status == 'open')
                                          OutlinedButton(
                                            onPressed: updating ? null : () => _updateStatus(id, 'read'),
                                            child: const Text('Mark read'),
                                          ),
                                        if (status != 'closed')
                                          FilledButton.tonal(
                                            onPressed: updating ? null : () => _updateStatus(id, 'closed'),
                                            child: const Text('Close inquiry'),
                                          ),
                                        if (status == 'closed')
                                          OutlinedButton(
                                            onPressed: updating ? null : () => _updateStatus(id, 'open'),
                                            child: const Text('Reopen'),
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
      setState(() => _error = 'Could not open local drafts: $error');
    }
  }

  Future<void> _saveDraft() async {
    final title = _title.text.trim();
    final location = _location.text.trim();
    final amount = double.tryParse(_price.text.trim());
    if (title.length < 3 || location.length < 2 || amount == null || amount < 0 || _categoryId == null) {
      setState(() => _error = 'Enter a title, category, valid ETB price and location.');
      return;
    }
    if (_selectedDraftSynced) {
      setState(() => _error = 'A synchronized server draft cannot be edited offline. Start a new draft.');
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
      setState(() => _error = 'Save the draft before adding photos.');
      return;
    }
    if (_selectedDraftSynced) {
      setState(() => _error = 'This server draft is synchronized and cannot be changed here.');
      return;
    }
    if (_images.length >= 5) {
      setState(() => _error = 'A listing can contain up to five photos.');
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
      setState(() => _error = 'Sync could not complete: $error');
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
      title: const Text('Offline listing drafts'),
      actions: [
        IconButton(
          tooltip: 'Sync pending drafts',
          onPressed: _busy ? null : _syncNow,
          icon: const Icon(Icons.sync),
        ),
      ],
    ),
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('Create a listing draft', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 8),
        DropdownButtonFormField<String>(
          value: _categoryId,
          decoration: const InputDecoration(labelText: 'Category'),
          items: _categories.map((item) => DropdownMenuItem(
            value: item['id'], child: Text(item['name']!),
          )).toList(),
          onChanged: (value) => setState(() => _categoryId = value),
        ),
        const SizedBox(height: 8),
        TextField(controller: _title, decoration: const InputDecoration(labelText: 'Listing title')),
        TextField(
          controller: _description,
          decoration: const InputDecoration(labelText: 'Description'),
          maxLines: 3,
        ),
        TextField(
          controller: _price,
          decoration: const InputDecoration(labelText: 'Price (ETB)'),
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
        ),
        TextField(controller: _location, decoration: const InputDecoration(labelText: 'Location')),
        const SizedBox(height: 12),
        Wrap(spacing: 8, children: [
          FilledButton.icon(
            onPressed: _busy ? null : _saveDraft,
            icon: const Icon(Icons.save_outlined),
            label: const Text('Save draft offline'),
          ),
          OutlinedButton.icon(
            onPressed: _busy ? null : _pickImage,
            icon: const Icon(Icons.add_photo_alternate_outlined),
            label: Text('Add photo (${_images.length}/5)'),
          ),
          TextButton(onPressed: _startNewDraft, child: const Text('New draft')),
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
          Expanded(child: Text('Saved on this device', style: Theme.of(context).textTheme.titleMedium)),
          TextButton(onPressed: _reload, child: const Text('Refresh')),
        ]),
        if (_drafts.isEmpty)
          const Text('No local drafts yet.')
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
          child: Text(_busy ? 'Synchronizing…' : 'Sync pending drafts and photos'),
        ),
        const SizedBox(height: 8),
        const Text(
          'Drafts remain local until synchronization succeeds. Synchronization creates server-side drafts only; publishing still requires seller submission and administrator moderation.',
        ),
      ],
    ),
  );
}
