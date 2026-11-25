import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:uuid/uuid.dart';

import '../../l10n/market_strings.dart';
import '../../design/market_design_system.dart';

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
  Map<String, dynamic> _attributeValues = {};
  Map<String, String> _attributeErrors = {};
  String? _error;
  String? _message;
  bool _loading = true;
  bool _busy = false;
  String? _loadedLocale;

  Map<String, String> get _headers => {
    'Authorization': 'Bearer ${widget.accessToken}',
    'Content-Type': 'application/json',
  };

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final language = Localizations.localeOf(context).languageCode;
    if (_loadedLocale == language) return;
    _loadedLocale = language;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _load();
    });
  }

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
        widget.client.get(Uri.parse('${widget.apiBaseUrl}/categories?lang=${_loadedLocale ?? 'am'}')),
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
      final savedCategoryId = listing['category_id'] as String?;
      _categoryId = _categories.any((category) =>
        category['id'] == savedCategoryId && category['is_leaf'] == true)
          ? savedCategoryId : null;
      _attributeValues = Map<String, dynamic>.from(
        (listing['attributes'] as Map<String, dynamic>?) ?? const {},
      );
      _attributeErrors = {};
      _title.text = listing['title'] as String? ?? '';
      _description.text = listing['description'] as String? ?? '';
      _price.text = (((listing['price_minor'] as num?) ?? 0) / 100).toStringAsFixed(2);
      _location.text = listing['location'] as String? ?? '';
      _message = null; _error = null;
    });
  }

  List<Map<String, dynamic>> get _selectedAttributeSchema {
    final categoryId = _categoryId;
    if (categoryId == null) return const [];
    Map<String, dynamic>? category;
    for (final item in _categories) {
      if (item['id'] == categoryId) { category = item; break; }
    }
    if (category == null) return const [];
    return (category['attributes_schema'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .toList();
  }

  String _attributeLabel(Map<String, dynamic> definition) {
    final raw = (definition['label'] ?? definition['name'] ?? definition['key'] ?? '').toString();
    if (raw.isEmpty) return '';
    return raw.replaceAll('_', ' ').split(' ').map((part) =>
      part.isEmpty ? part : '${part[0].toUpperCase()}${part.substring(1)}').join(' ');
  }

  bool _validateAttributes() {
    final errors = <String, String>{};
    for (final definition in _selectedAttributeSchema) {
      final key = definition['key']?.toString();
      if (key == null || key.isEmpty) continue;
      var value = _attributeValues[key];
      final required = definition['required'] == true;
      final type = definition['type']?.toString();
      if (type == 'boolean' && value == null) {
        value = false;
        _attributeValues[key] = false;
      }
      if (value == null || (value is String && value.trim().isEmpty)) {
        if (required) errors[key] = marketString(context,
          en: '${_attributeLabel(definition)} is required.',
          am: 'ይህ መስክ መሞላት አለበት።', mdy: '');
        continue;
      }
      if (type == 'text') {
        final max = (definition['max_length'] as num?)?.toInt() ?? 500;
        if (value is! String || value.trim().isEmpty || value.length > max) {
          errors[key] = marketString(context, en: 'Enter text up to $max characters.', am: 'እስከ $max ቁምፊዎች ያስገቡ።', mdy: '');
        }
      } else if (type == 'number') {
        if (value is! num || (definition['min'] is num && value < definition['min']) ||
            (definition['max'] is num && value > definition['max'])) {
          final min = definition['min']?.toString();
          final max = definition['max']?.toString();
          errors[key] = marketString(context,
            en: 'Enter a number${min == null ? '' : ' from $min'}${max == null ? '' : ' to $max'}.',
            am: 'በተፈቀደው ክልል ውስጥ ቁጥር ያስገቡ።', mdy: '');
        }
      } else if (type == 'choice') {
        final options = (definition['options'] as List<dynamic>? ?? const []).map((e) => e.toString()).toSet();
        if (value is! String || !options.contains(value)) {
          errors[key] = marketString(context, en: 'Choose one of the available options.', am: 'ከተዘረዘሩት አማራጮች አንዱን ይምረጡ።', mdy: '');
        }
      } else if (type == 'boolean' && value is! bool) {
        errors[key] = marketString(context, en: 'Choose yes or no.', am: 'አዎ ወይም አይ ይምረጡ።', mdy: '');
      }
    }
    setState(() => _attributeErrors = errors);
    return errors.isEmpty;
  }

  Widget _buildAttributeFields() {
    final schema = _selectedAttributeSchema;
    if (schema.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 12),
        Text(marketString(context, en: 'Category details', am: 'የምድቡ ዝርዝር መረጃ', mdy: ''),
          style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 6),
        Text(marketString(context,
          en: 'These fields are specific to the selected subcategory.',
          am: 'እነዚህ መስኮች ለተመረጠው ንዑስ ምድብ ብቻ ናቸው።', mdy: ''),
          style: Theme.of(context).textTheme.bodySmall),
        ...schema.map((definition) {
          final key = definition['key']?.toString() ?? '';
          if (key.isEmpty) return const SizedBox.shrink();
          final label = _attributeLabel(definition);
          final required = definition['required'] == true;
          final type = definition['type']?.toString();
          final error = _attributeErrors[key];
          final decoration = InputDecoration(
            labelText: required ? '$label *' : label,
            errorText: error,
            helperText: definition['help']?.toString(),
          );
          if (type == 'boolean') {
            return SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(required ? '$label *' : label),
              subtitle: error == null ? null : Text(error,
                style: TextStyle(color: Theme.of(context).colorScheme.error)),
              value: (_attributeValues[key] as bool?) ?? false,
              onChanged: _selected?['status'] == 'draft'
                ? (value) => setState(() {
                    _attributeValues[key] = value;
                    _attributeErrors.remove(key);
                  }) : null,
            );
          }
          if (type == 'choice') {
            final options = (definition['options'] as List<dynamic>? ?? const [])
                .map((value) => value.toString()).toList();
            return Padding(
              padding: const EdgeInsets.only(top: 8),
              child: DropdownButtonFormField<String>(
                value: options.contains(_attributeValues[key]) ? _attributeValues[key] as String : null,
                decoration: decoration,
                items: options.map((option) => DropdownMenuItem(
                  value: option, child: Text(option.replaceAll('_', ' ')))).toList(),
                onChanged: _selected?['status'] == 'draft'
                  ? (value) => setState(() {
                      if (value == null) { _attributeValues.remove(key); }
                      else { _attributeValues[key] = value; }
                      _attributeErrors.remove(key);
                    }) : null,
              ),
            );
          }
          final isNumber = type == 'number';
          return Padding(
            padding: const EdgeInsets.only(top: 8),
            child: TextFormField(
              key: ValueKey('${_selected?['id']}:$_categoryId:$key'),
              initialValue: _attributeValues[key]?.toString() ?? '',
              enabled: _selected?['status'] == 'draft',
              keyboardType: isNumber
                ? const TextInputType.numberWithOptions(decimal: true)
                : TextInputType.text,
              maxLength: isNumber ? null : ((definition['max_length'] as num?)?.toInt() ?? 500),
              decoration: decoration,
              onChanged: (raw) => setState(() {
                if (raw.trim().isEmpty) {
                  _attributeValues.remove(key);
                } else if (isNumber) {
                  _attributeValues[key] = num.tryParse(raw.trim()) ?? raw;
                } else {
                  _attributeValues[key] = raw;
                }
                _attributeErrors.remove(key);
              }),
            ),
          );
        }),
      ],
    );
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
    if (!_validateAttributes()) {
      setState(() => _error = marketString(context,
        en: 'Please correct the highlighted category fields.',
        am: 'እባክዎ ምልክት የተደረገባቸውን የምድብ መስኮች ያስተካክሉ።', mdy: ''));
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
          'attributes': _attributeValues,
        }),
      );
      if (response.statusCode != 200) {
        String detail = '';
        try {
          final body = jsonDecode(response.body) as Map<String, dynamic>;
          detail = body['detail']?.toString() ?? '';
        } catch (_) {}
        throw Exception(detail.isNotEmpty ? detail :
          marketString(context, en: 'Draft update failed (${response.statusCode}).',
            am: 'ረቂቁን ማዘመን አልተሳካም (${response.statusCode})።', mdy: ''));
      }
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
          title: Text(listing['title'] as String? ?? marketString(context, en: 'Untitled', am: 'ርዕስ የሌለው', mdy: '')),
          subtitle: Text('${listing['location'] ?? ''} · ${marketStatusLabel(context, listing['status'] as String)}'),
          selected: _selected?['id'] == listing['id'],
          onTap: () => _select(listing),
        )),
        if (_selected != null) ...[
          const Divider(),
          Text(marketString(context, en: 'Edit draft', am: 'ረቂቁን አስተካክል', mdy: ''), style: Theme.of(context).textTheme.titleLarge),
          DropdownButtonFormField<String>(
            value: _categoryId,
            decoration: InputDecoration(labelText: marketString(context, en: 'Category', am: 'ምድብ', mdy: '')),
            items: _categories.where((category) => category['is_leaf'] == true).map((category) => DropdownMenuItem<String>(
              value: category['id'] as String, child: Text(category['name'] as String),
            )).toList(),
            onChanged: _selected!['status'] == 'draft' ? (value) => setState(() {
              if (_categoryId != value) {
                _categoryId = value;
                _attributeValues = {};
                _attributeErrors = {};
              }
            }) : null,
          ),
          _buildAttributeFields(),
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
  final _legalName = TextEditingController();
  final _description = TextEditingController();
  final _locationLabel = TextEditingController();
  final _phone = TextEditingController();
  final _email = TextEditingController();
  final _serviceAreas = TextEditingController();
  final _hours = TextEditingController();
  final _registrationNumber = TextEditingController();
  final _latitude = TextEditingController();
  final _longitude = TextEditingController();

  List<Map<String, dynamic>> _categories = [];
  List<Map<String, dynamic>> _locations = [];
  String _businessType = 'individual';
  String? _categoryId;
  String? _locationId;
  String? _contactMethod;
  String _locationVisibility = 'hidden';
  List<String> _languages = ['am', 'en'];
  bool _publishPhone = false;
  bool _publishEmail = false;
  bool _confirmExactLocation = false;
  bool _loading = true;
  bool _busy = false;
  bool _editing = false;
  String? _verificationStatus;
  String? _membershipStatus;
  String? _error;

  Map<String, String> get _headers => {
    'Authorization': 'Bearer ${widget.accessToken}',
    'Content-Type': 'application/json',
  };

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) { if (mounted) _load(); });
  }

  @override
  void dispose() {
    _name.dispose();
    _legalName.dispose();
    _description.dispose();
    _locationLabel.dispose();
    _phone.dispose();
    _email.dispose();
    _serviceAreas.dispose();
    _hours.dispose();
    _registrationNumber.dispose();
    _latitude.dispose();
    _longitude.dispose();
    super.dispose();
  }

  String _text(Map<String, dynamic> data, String key) =>
      data[key]?.toString() ?? '';

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final responses = await Future.wait([
        widget.client.get(Uri.parse('${widget.apiBaseUrl}/categories?lang=${Localizations.localeOf(context).languageCode}')),
        widget.client.get(Uri.parse('${widget.apiBaseUrl}/locations?lang=${Localizations.localeOf(context).languageCode}')),
        widget.client.get(Uri.parse('${widget.apiBaseUrl}/sellers/me'), headers: _headers),
      ]);
      if (responses[0].statusCode != 200 || responses[1].statusCode != 200 ||
          (responses[2].statusCode != 200 && responses[2].statusCode != 404)) {
        throw Exception(marketString(context,
          en: 'Seller onboarding data could not be loaded. Please retry.',
          am: 'የሻጭ ምዝገባ መረጃን መጫን አልተቻለም። እንደገና ይሞክሩ።', mdy: ''));
      }
      final categories = (jsonDecode(responses[0].body) as List<dynamic>)
          .cast<Map<String, dynamic>>();
      final locations = (jsonDecode(responses[1].body) as List<dynamic>)
          .cast<Map<String, dynamic>>()
          .where((item) => item['level'] == 'town' || item['level'] == 'locality')
          .toList();
      Map<String, dynamic>? profile;
      if (responses[2].statusCode == 200) {
        profile = jsonDecode(responses[2].body) as Map<String, dynamic>;
      }
      if (!mounted) return;
      final profileData = profile;
      setState(() {
        _categories = categories.where((item) => item['is_leaf'] == true).toList();
        _locations = locations;
        if (profileData != null) {
          _editing = profileData['business_id'] != null;
          _name.text = _text(profileData, 'public_name');
          _legalName.text = _text(profileData, 'legal_name');
          _description.text = _text(profileData, 'description');
          _locationLabel.text = _text(profileData, 'location');
          _phone.text = _text(profileData, 'contact_phone');
          _email.text = _text(profileData, 'contact_email');
          _registrationNumber.text = _text(profileData, 'registration_number');
          _categoryId = profileData['primary_category_id'] as String?;
          _locationId = profileData['operating_location_id'] as String?;
          _businessType = _text(profileData, 'business_type').isEmpty ? 'individual' : _text(profileData, 'business_type');
          _serviceAreas.text = ((profileData['service_area'] as List<dynamic>?) ?? const []).join(', ');
          final hours = (profileData['operating_hours'] as Map<String, dynamic>?) ?? const {};
          _hours.text = hours['public_note']?.toString() ?? '';
          _languages = ((profileData['supported_languages'] as List<dynamic>?) ?? const ['am', 'en'])
              .map((item) => item.toString()).toList();
          _publishPhone = profileData['public_contact_phone'] != null;
          _publishEmail = profileData['public_contact_email'] != null;
          _contactMethod = profileData['public_contact_method'] as String?;
          _locationVisibility = _text(profileData, 'public_location_visibility').isEmpty
              ? 'hidden' : _text(profileData, 'public_location_visibility');
          _confirmExactLocation = _locationVisibility == 'exact';
          _latitude.text = _text(profileData, 'latitude');
          _longitude.text = _text(profileData, 'longitude');
          _verificationStatus = profileData['verification_status'] as String?;
          _membershipStatus = profileData['membership_status'] as String?;
        }
      });
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _save() async {
    if (_name.text.trim().length < 2 || _locationLabel.text.trim().length < 2 ||
        _locationId == null || _categoryId == null) {
      setState(() => _error = marketString(context,
        en: 'Enter a business name, category and operating town/locality.',
        am: 'የንግድ ስም፣ ምድብ እና የሚሰሩበትን ከተማ/አካባቢ ይምረጡ።', mdy: ''));
      return;
    }
    if (_languages.isEmpty) {
      setState(() => _error = marketString(context,
        en: 'Choose at least one supported language.',
        am: 'ቢያንስ አንድ የሚደገፍ ቋንቋ ይምረጡ።', mdy: ''));
      return;
    }
    final lat = _locationVisibility == 'exact' ? double.tryParse(_latitude.text.trim()) : null;
    final lon = _locationVisibility == 'exact' ? double.tryParse(_longitude.text.trim()) : null;
    if (_locationVisibility == 'exact' &&
        (lat == null || lon == null || !_confirmExactLocation)) {
      setState(() => _error = marketString(context,
        en: 'Exact map location requires valid coordinates and your explicit consent.',
        am: 'ትክክለኛ የካርታ አካባቢ ትክክለኛ መጋጠሚያዎችንና ግልጽ ፈቃድዎን ይፈልጋል።', mdy: ''));
      return;
    }
    if (_contactMethod == 'phone' || _contactMethod == 'sms') {
      if (!_publishPhone) {
        setState(() => _error = marketString(context,
          en: 'Choose to publish your phone number before selecting phone contact.',
          am: 'የስልክ አድራሻን ከመምረጥዎ በፊት ስልክ ቁጥርዎን ለሕዝብ ማሳየት ይፍቀዱ።', mdy: ''));
        return;
      }
    }
    if (_contactMethod == 'email' && (!_publishEmail || _email.text.trim().isEmpty)) {
      setState(() => _error = marketString(context,
        en: 'Choose to publish a valid email before selecting email contact.',
        am: 'የኢሜይል አድራሻን ከመምረጥዎ በፊት ኢሜይልዎን ለሕዝብ ማሳየት ይፍቀዱ።', mdy: ''));
      return;
    }

    setState(() { _busy = true; _error = null; });
    try {
      final payload = <String, dynamic>{
        'public_name': _name.text.trim(),
        'legal_name': _legalName.text.trim().isEmpty ? null : _legalName.text.trim(),
        'business_type': _businessType,
        'description': _description.text.trim().isEmpty ? null : _description.text.trim(),
        'primary_category_id': _categoryId,
        'location_label': _locationLabel.text.trim(),
        'operating_location_id': _locationId,
        'service_area': _serviceAreas.text.split(',').map((item) => item.trim())
            .where((item) => item.isNotEmpty).toList(),
        'operating_hours': _hours.text.trim().isEmpty ? <String, String>{}
            : <String, String>{'public_note': _hours.text.trim()},
        'supported_languages': _languages,
        'contact_phone': _phone.text.trim().isEmpty ? null : _phone.text.trim(),
        'contact_email': _email.text.trim().isEmpty ? null : _email.text.trim(),
        'publish_contact_phone': _publishPhone,
        'publish_contact_email': _publishEmail,
        'public_contact_method': _contactMethod,
        'public_location_visibility': _locationVisibility,
        'latitude': lat,
        'longitude': lon,
        'confirm_exact_location': _confirmExactLocation,
        'registration_number': _registrationNumber.text.trim().isEmpty
            ? null : _registrationNumber.text.trim(),
      };
      final uri = Uri.parse('${widget.apiBaseUrl}/sellers/me');
      final response = _editing
          ? await widget.client.patch(uri, headers: _headers, body: jsonEncode(payload))
          : await widget.client.post(uri, headers: _headers, body: jsonEncode(payload));
      final expected = _editing ? 200 : 201;
      if (response.statusCode != expected) {
        String detail = '';
        try {
          final body = jsonDecode(response.body) as Map<String, dynamic>;
          detail = body['detail']?.toString() ?? '';
        } catch (_) {}
        throw Exception(detail.isNotEmpty ? detail : marketString(context,
          en: 'Business profile could not be saved (${response.statusCode}).',
          am: 'የንግድ መገለጫውን ማስቀመጥ አልተቻለም (${response.statusCode})።', mdy: ''));
      }
      if (!mounted) return;
      widget.onComplete();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _sectionTitle(String title) => Padding(
    padding: const EdgeInsets.only(top: 18, bottom: 8),
    child: Text(title, style: Theme.of(context).textTheme.titleMedium),
  );

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(marketString(context,
      en: _editing ? 'Business profile' : 'Set up business profile',
      am: _editing ? 'የንግድ መገለጫ' : 'የንግድ መገለጫ ያዘጋጁ', mdy: '')),
      actions: [IconButton(onPressed: _loading || _busy ? null : _load,
        tooltip: marketString(context, en: 'Refresh', am: 'አድስ', mdy: ''),
        icon: const Icon(Icons.refresh))]),
    body: _loading ? const Center(child: CircularProgressIndicator())
      : ListView(padding: const EdgeInsets.all(20), children: [
        MarketBrandPanel(
          title: marketString(context, en: 'Build your business presence.',
            am: 'የንግድዎን መገኘት ያጠናክሩ።', mdy: ''),
          subtitle: marketString(context,
            en: 'Tell local buyers what you offer and how they can reach you. Your business starts pending review; it is not marked verified automatically.',
            am: 'ለአካባቢ ገዢዎች ምን እንደሚያቀርቡና እንዴት ሊያገኙዎት እንደሚችሉ ያሳውቁ። የንግድዎ ሁኔታ ግምገማ በመጠባበቅ ላይ ይሆናል፤ በራስ-ሰር የተረጋገጠ አይሆንም።', mdy: ''),
        ),
        if (_verificationStatus != null) Padding(
          padding: const EdgeInsets.only(top: 12),
          child: Card(child: ListTile(
            leading: const Icon(Icons.verified_user_outlined),
            title: Text(marketString(context, en: 'Business review status', am: 'የንግድ ግምገማ ሁኔታ', mdy: '')),
            subtitle: Text('${marketStatusLabel(context, _verificationStatus!)} · ${_membershipStatus ?? ''}'),
          )),
        ),
        _sectionTitle(marketString(context, en: 'Business identity', am: 'የንግድ መለያ', mdy: '')),
        TextField(key: const Key('seller-business-name'), controller: _name, decoration: InputDecoration(
          labelText: marketString(context, en: 'Public business name *', am: 'የንግድ ሕዝባዊ ስም *', mdy: ''),
          prefixIcon: const Icon(Icons.storefront_outlined))),
        const SizedBox(height: 10),
        DropdownButtonFormField<String>(
          key: const Key('seller-business-type'),
          value: _businessType,
          decoration: InputDecoration(labelText: marketString(context, en: 'Business type *', am: 'የንግድ ዓይነት *', mdy: '')),
          items: [
            ('individual', 'Individual seller', 'ግለሰብ ሻጭ'),
            ('shop', 'Shop', 'ሱቅ'),
            ('producer', 'Producer / farmer', 'አምራች / አርሶ አደር'),
            ('service_provider', 'Service provider', 'አገልግሎት ሰጪ'),
            ('cooperative', 'Cooperative', 'ህብረት ሥራ ማህበር'),
            ('company', 'Company', 'ኩባንያ'),
            ('trader', 'Trader', 'ነጋዴ'),
            ('other', 'Other', 'ሌላ'),
          ].map((item) => DropdownMenuItem(value: item.$1,
            child: Text(Localizations.localeOf(context).languageCode == 'am' ? item.$3 : item.$2))).toList(),
          onChanged: _busy ? null : (value) { if (value != null) setState(() => _businessType = value); },
        ),
        const SizedBox(height: 10),
        TextField(controller: _legalName, decoration: InputDecoration(
          labelText: marketString(context, en: 'Legal name (optional)', am: 'ሕጋዊ ስም (አማራጭ)', mdy: ''))),
        const SizedBox(height: 10),
        TextField(controller: _registrationNumber, decoration: InputDecoration(
          labelText: marketString(context, en: 'Business registration number (optional)', am: 'የንግድ ምዝገባ ቁጥር (አማራጭ)', mdy: ''))),
        const SizedBox(height: 10),
        TextField(controller: _description, maxLines: 4, maxLength: 2000,
          decoration: InputDecoration(labelText: marketString(context,
            en: 'About your business', am: 'ስለ ንግድዎ', mdy: ''))),
        _sectionTitle(marketString(context, en: 'Category and operating area', am: 'ምድብ እና የሚሰሩበት አካባቢ', mdy: '')),
        DropdownButtonFormField<String>(
          key: const Key('seller-business-category'),
          value: _categoryId,
          decoration: InputDecoration(labelText: marketString(context, en: 'Main business category *', am: 'ዋና የንግድ ምድብ *', mdy: '')),
          items: _categories.map((item) => DropdownMenuItem<String>(
            value: item['id'] as String, child: Text(item['name']?.toString() ?? ''))).toList(),
          onChanged: _busy ? null : (value) => setState(() => _categoryId = value),
        ),
        const SizedBox(height: 10),
        DropdownButtonFormField<String>(
          key: const Key('seller-business-location'),
          value: _locationId,
          decoration: InputDecoration(labelText: marketString(context, en: 'Operating town / locality *', am: 'የሚሰሩበት ከተማ / አካባቢ *', mdy: '')),
          items: _locations.map((item) => DropdownMenuItem<String>(
            value: item['id'] as String, child: Text(item['name']?.toString() ?? ''))).toList(),
          onChanged: _busy ? null : (value) {
            Map<String, dynamic>? selected;
            for (final item in _locations) { if (item['id'] == value) { selected = item; break; } }
            setState(() {
              _locationId = value;
              if (selected != null) _locationLabel.text = selected['name']?.toString() ?? '';
            });
          },
        ),
        const SizedBox(height: 10),
        TextField(key: const Key('seller-business-location-label'), controller: _locationLabel, decoration: InputDecoration(
          labelText: marketString(context, en: 'Locality display label *', am: 'የአካባቢ ማሳያ ስም *', mdy: ''))),
        const SizedBox(height: 10),
        TextField(controller: _serviceAreas, decoration: InputDecoration(
          labelText: marketString(context, en: 'Other service areas (comma separated)', am: 'ተጨማሪ የአገልግሎት አካባቢዎች (በኮማ ይለዩ)', mdy: ''))),
        const SizedBox(height: 10),
        TextField(controller: _hours, decoration: InputDecoration(
          labelText: marketString(context, en: 'Opening days / hours (optional)', am: 'የሥራ ቀናት / ሰዓታት (አማራጭ)', mdy: ''),
          hintText: 'Mon–Sat, 08:00–18:00')),
        _sectionTitle(marketString(context, en: 'Contact and privacy', am: 'የመገናኛ መረጃ እና ግላዊነት', mdy: '')),
        TextField(key: const Key('seller-business-phone'), controller: _phone, keyboardType: TextInputType.phone,
          decoration: InputDecoration(labelText: marketString(context, en: 'Business contact phone (private by default)', am: 'የንግድ ስልክ (በነባሪ ለሕዝብ አይታይም)', mdy: ''))),
        CheckboxListTile(key: const Key('seller-business-publish-phone'), contentPadding: EdgeInsets.zero, value: _publishPhone,
          onChanged: _busy ? null : (value) => setState(() => _publishPhone = value ?? false),
          title: Text(marketString(context, en: 'Publish this phone number on my business profile',
            am: 'ይህን ስልክ ቁጥር በንግድ መገለጫዬ ላይ አሳይ', mdy: ''))),
        TextField(key: const Key('seller-business-email'), controller: _email, keyboardType: TextInputType.emailAddress,
          decoration: InputDecoration(labelText: marketString(context, en: 'Business email (optional)', am: 'የንግድ ኢሜይል (አማራጭ)', mdy: ''))),
        CheckboxListTile(key: const Key('seller-business-publish-email'), contentPadding: EdgeInsets.zero, value: _publishEmail,
          onChanged: _busy ? null : (value) => setState(() => _publishEmail = value ?? false),
          title: Text(marketString(context, en: 'Publish this email on my business profile',
            am: 'ይህን ኢሜይል በንግድ መገለጫዬ ላይ አሳይ', mdy: ''))),
        DropdownButtonFormField<String>(
          key: const Key('seller-business-contact-method'),
          value: _contactMethod ?? 'none',
          decoration: InputDecoration(labelText: marketString(context, en: 'Preferred public contact method', am: 'የሕዝብ መገናኛ ዘዴ', mdy: '')),
          items: [
            DropdownMenuItem<String>(value: 'none', child: Text(marketString(context, en: 'Not selected', am: 'አልተመረጠም', mdy: ''))),
            DropdownMenuItem(value: 'phone', child: Text(marketString(context, en: 'Phone call', am: 'በስልክ ጥሪ', mdy: ''))),
            DropdownMenuItem(value: 'sms', child: Text('SMS')),
            DropdownMenuItem(value: 'email', child: Text('Email')),
          ],
          onChanged: _busy ? null : (value) => setState(() => _contactMethod = value == 'none' ? null : value),
        ),
        _sectionTitle(marketString(context, en: 'Languages', am: 'ቋንቋዎች', mdy: '')),
        CheckboxListTile(contentPadding: EdgeInsets.zero, value: _languages.contains('am'),
          onChanged: _busy ? null : (value) => setState(() {
            if (value == true) { _languages.add('am'); } else { _languages.remove('am'); }
          }), title: const Text('አማርኛ')),
        CheckboxListTile(contentPadding: EdgeInsets.zero, value: _languages.contains('en'),
          onChanged: _busy ? null : (value) => setState(() {
            if (value == true) { _languages.add('en'); } else { _languages.remove('en'); }
          }), title: const Text('English')),
        _sectionTitle(marketString(context, en: 'Public map location', am: 'የሕዝብ የካርታ አካባቢ', mdy: '')),
        DropdownButtonFormField<String>(
          key: const Key('seller-business-location-visibility'),
          value: _locationVisibility,
          decoration: InputDecoration(labelText: marketString(context, en: 'Location visibility', am: 'የአካባቢ ታይነት', mdy: '')),
          items: [
            DropdownMenuItem(value: 'hidden', child: Text(marketString(context, en: 'Hidden', am: 'የተደበቀ', mdy: ''))),
            DropdownMenuItem(value: 'approximate', child: Text(marketString(context, en: 'Approximate locality only', am: 'ግምታዊ አካባቢ ብቻ', mdy: ''))),
            DropdownMenuItem(value: 'exact', child: Text(marketString(context, en: 'Exact pin (consent required)', am: 'ትክክለኛ ነጥብ (ፈቃድ ያስፈልጋል)', mdy: ''))),
          ],
          onChanged: _busy ? null : (value) => setState(() {
            _locationVisibility = value ?? 'hidden';
            if (_locationVisibility != 'exact') {
              _latitude.clear(); _longitude.clear(); _confirmExactLocation = false;
            }
          }),
        ),
        if (_locationVisibility == 'exact') ...[
          const SizedBox(height: 10),
          TextField(controller: _latitude, keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: true),
            decoration: const InputDecoration(labelText: 'Latitude')),
          const SizedBox(height: 8),
          TextField(controller: _longitude, keyboardType: const TextInputType.numberWithOptions(decimal: true, signed: true),
            decoration: const InputDecoration(labelText: 'Longitude')),
          CheckboxListTile(contentPadding: EdgeInsets.zero, value: _confirmExactLocation,
            onChanged: _busy ? null : (value) => setState(() => _confirmExactLocation = value ?? false),
            title: Text(marketString(context, en: 'I explicitly consent to publishing this exact business location.',
              am: 'ይህን ትክክለኛ የንግድ አካባቢ ለሕዝብ ለማሳየት በግልጽ ፈቃደኛ ነኝ።', mdy: ''))),
        ],
        if (_error != null) Padding(
          padding: const EdgeInsets.only(top: 12),
          child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
        ),
        const SizedBox(height: 20),
        FilledButton.icon(
          key: const Key('seller-business-save'),
          onPressed: _busy ? null : _save,
          icon: _busy ? const SizedBox(width: 18, height: 18,
            child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.save_outlined),
          label: Text(_busy
            ? marketString(context, en: 'Saving…', am: 'በማስቀመጥ ላይ…', mdy: '')
            : marketString(context, en: _editing ? 'Save business profile' : 'Submit business profile',
              am: _editing ? 'የንግድ መገለጫውን አስቀምጥ' : 'የንግድ መገለጫውን አስገባ', mdy: '')),
        ),
      ]),
  );
}
