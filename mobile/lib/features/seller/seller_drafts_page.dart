import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

import '../../data/local_draft_store.dart';
import '../../data/offline_sync_service.dart';
import '../../l10n/market_strings.dart';

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
      _message = marketString(context, en: 'Draft saved on this device. It has not been published.', am: 'ረቂቁ በዚህ መሣሪያ ላይ ተቀምጧል። ገና አልታተመም።', mdy: '');
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
    if (mounted) setState(() => _message = marketString(context, en: 'Photo queued locally for upload.', am: 'ፎቶው በአካባቢው ለመጫን ተዘጋጅቷል።', mdy: ''));
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
        _message = marketString(context, en: '${result.synced} draft(s) synced; ${result.failed} need retry.', am: '${result.synced} ረቂቅ(ቆች) ተመሳስለዋል፤ ${result.failed} እንደገና መሞከር ያስፈልጋቸዋል።', mdy: '');
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
            value: item['id'], child: Text(marketString(context, en: item['name']!, am: const {'Livestock':'እንስሳት','Agriculture':'ግብርና','Food and groceries':'ምግብና ሸቀጣ ሸቀጦች','Shops and products':'ሱቆችና ምርቶች','Services':'አገልግሎቶች','Property and rentals':'ንብረትና ኪራይ'}[item['name']] ?? item['name']!, mdy: '')),
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
            label: Text(marketString(context, en: 'Add photo (${_images.length}/5)', am: 'ፎቶ ጨምር (${_images.length}/5)', mdy: '')),
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
              subtitle: Text('${draft['location_label']} · ${marketStatusLabel(context, draft['sync_state'] as String)}'
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
