import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../l10n/market_strings.dart';

class CustomerProfilePage extends StatefulWidget {
  const CustomerProfilePage({
    super.key,
    required this.apiBaseUrl,
    required this.accessToken,
    required this.client,
  });

  final String apiBaseUrl;
  final String accessToken;
  final http.Client client;

  @override
  State<CustomerProfilePage> createState() => _CustomerProfilePageState();
}

class _CustomerProfilePageState extends State<CustomerProfilePage> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  List<Map<String, dynamic>> _locations = [];
  List<Map<String, dynamic>> _markets = [];
  String? _locationId;
  String? _marketId;
  String _language = 'am';
  String? _contactPreference;
  bool _loading = true;
  bool _saving = false;
  bool _loggingOut = false;
  String? _error;
  String? _notice;
  bool _started = false;

  String get _base => widget.apiBaseUrl.replaceFirst(RegExp(r'/+$'), '');
  Map<String, String> get _headers => {
    'Authorization': 'Bearer ${widget.accessToken}',
    'Content-Type': 'application/json',
  };

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_started) return;
    _started = true;
    _load();
  }

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final lang = Localizations.localeOf(context).languageCode;
      final responses = await Future.wait([
        widget.client.get(Uri.parse('$_base/customers/me'), headers: _headers),
        widget.client.get(Uri.parse('$_base/locations?lang=$lang')),
        widget.client.get(Uri.parse('$_base/markets?lang=$lang')),
      ]);
      if (responses.any((response) => response.statusCode != 200)) {
        if (responses[0].statusCode == 401) {
          throw Exception(marketString(context, en: 'Your session has expired. Sign in again.', am: 'የመግቢያ ጊዜዎ አብቅቷል። እንደገና ይግቡ።', mdy: ''));
        }
        throw Exception(marketString(context, en: 'Your profile or locality options could not be loaded.', am: 'መገለጫዎን ወይም የአካባቢ ምርጫዎችን መጫን አልተቻለም።', mdy: ''));
      }
      final profile = jsonDecode(responses[0].body) as Map<String, dynamic>;
      final locations = (jsonDecode(responses[1].body) as List<dynamic>).cast<Map<String, dynamic>>()
          .where((row) => row['level'] == 'town' || row['level'] == 'locality').toList();
      final markets = (jsonDecode(responses[2].body) as List<dynamic>).cast<Map<String, dynamic>>();
      if (!mounted) return;
      setState(() {
        _name.text = profile['display_name'] as String? ?? '';
        _email.text = profile['email'] as String? ?? '';
        _locationId = profile['preferred_location_id'] as String?;
        _marketId = profile['preferred_market_id'] as String?;
        _language = profile['preferred_language'] as String? ?? 'am';
        _contactPreference = profile['contact_preference'] as String?;
        _locations = locations;
        _markets = markets;
      });
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _logout() async {
    if (_loggingOut || _saving) return;
    setState(() { _loggingOut = true; _error = null; });
    try {
      final response = await widget.client.post(
        Uri.parse('$_base/auth/logout'),
        headers: _headers,
      );
      if (response.statusCode != 204 && response.statusCode != 401) {
        throw Exception(marketString(context,
          en: 'Could not securely sign out. Please retry.',
          am: 'በደህና መውጣት አልተቻለም። እንደገና ይሞክሩ።', mdy: ''));
      }
      if (mounted) Navigator.of(context).pop();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loggingOut = false);
    }
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() { _saving = true; _error = null; _notice = null; });
    try {
      final response = await widget.client.patch(
        Uri.parse('$_base/customers/me'),
        headers: _headers,
        body: jsonEncode({
          'display_name': _name.text.trim(),
          'email': _email.text.trim().isEmpty ? null : _email.text.trim(),
          'preferred_location_id': _locationId,
          'preferred_market_id': _marketId,
          'preferred_language': _language,
          'contact_preference': _contactPreference,
        }),
      );
      if (response.statusCode != 200) {
        throw Exception(response.statusCode == 401
            ? marketString(context, en: 'Your session has expired. Sign in again.', am: 'የመግቢያ ጊዜዎ አብቅቷል። እንደገና ይግቡ።', mdy: '')
            : marketString(context, en: 'Profile changes could not be saved (${response.statusCode}).', am: 'የመገለጫ ለውጦችን ማስቀመጥ አልተቻለም (${response.statusCode})።', mdy: ''));
      }
      if (!mounted) return;
      setState(() => _notice = marketString(context, en: 'Profile updated successfully.', am: 'መገለጫው በተሳካ ሁኔታ ተዘምኗል።', mdy: ''));
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(marketString(context, en: 'Customer profile', am: 'የደንበኛ መገለጫ', mdy: '')),
      actions: [
        IconButton(
          tooltip: marketString(context, en: 'Refresh profile', am: 'መገለጫውን አድስ', mdy: ''),
          onPressed: _loading || _saving || _loggingOut ? null : _load,
          icon: const Icon(Icons.refresh),
        ),
        IconButton(
          key: const Key('customer-profile-logout'),
          tooltip: marketString(context, en: 'Sign out', am: 'ውጣ', mdy: ''),
          onPressed: _loading || _saving || _loggingOut ? null : _logout,
          icon: _loggingOut
            ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
            : const Icon(Icons.logout),
        ),
      ],
    ),
    body: _loading
      ? const Center(child: CircularProgressIndicator())
      : _error != null && _locations.isEmpty
        ? Center(child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Text(_error!, textAlign: TextAlign.center),
              const SizedBox(height: 12),
              OutlinedButton.icon(onPressed: _load, icon: const Icon(Icons.refresh),
                label: Text(marketString(context, en: 'Retry', am: 'እንደገና ሞክር', mdy: ''))),
            ]),
          ))
        : Form(
            key: _formKey,
            child: ListView(
              padding: const EdgeInsets.all(18),
              children: [
                Text(marketString(context, en: 'Your account details', am: 'የመለያዎ መረጃ', mdy: ''),
                  style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 14),
                TextFormField(
                  key: const Key('customer-profile-name'),
                  controller: _name,
                  decoration: InputDecoration(labelText: marketString(context, en: 'Full name', am: 'ሙሉ ስም', mdy: '')),
                  validator: (value) => value == null || value.trim().isEmpty
                    ? marketString(context, en: 'Enter your name.', am: 'ስምዎን ያስገቡ።', mdy: '') : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  key: const Key('customer-profile-email'),
                  controller: _email,
                  keyboardType: TextInputType.emailAddress,
                  decoration: InputDecoration(labelText: marketString(context, en: 'Email (optional)', am: 'ኢሜይል (አማራጭ)', mdy: '')),
                  validator: (value) => value != null && value.trim().isNotEmpty && !value.contains('@')
                    ? marketString(context, en: 'Enter a valid email address.', am: 'ትክክለኛ ኢሜይል ያስገቡ።', mdy: '') : null,
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  key: const Key('customer-profile-location'),
                  value: _locationId,
                  isExpanded: true,
                  decoration: InputDecoration(labelText: marketString(context, en: 'Preferred town / locality', am: 'ተመራጭ ከተማ / አካባቢ', mdy: '')),
                  items: _locations.map((row) => DropdownMenuItem<String>(
                    value: row['id'] as String,
                    child: Text(row['name'] as String, overflow: TextOverflow.ellipsis),
                  )).toList(),
                  onChanged: (value) => setState(() { _locationId = value; _marketId = null; }),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  key: const Key('customer-profile-market'),
                  value: _marketId,
                  isExpanded: true,
                  decoration: InputDecoration(labelText: marketString(context, en: 'Preferred market (optional)', am: 'ተመራጭ ገበያ (አማራጭ)', mdy: '')),
                  items: _markets.where((row) => _locationId == null || row['location_id'] == null || row['location_id'] == _locationId)
                    .map((row) => DropdownMenuItem<String>(
                      value: row['id'] as String,
                      child: Text(row['name'] as String, overflow: TextOverflow.ellipsis),
                    )).toList(),
                  onChanged: (value) => setState(() => _marketId = value),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  key: const Key('customer-profile-language'),
                  value: _language,
                  decoration: InputDecoration(labelText: marketString(context, en: 'Preferred language', am: 'ተመራጭ ቋንቋ', mdy: '')),
                  items: const [
                    DropdownMenuItem(value: 'am', child: Text('አማርኛ')),
                    DropdownMenuItem(value: 'en', child: Text('English')),
                  ],
                  onChanged: (value) => setState(() => _language = value ?? 'am'),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  key: const Key('customer-profile-contact'),
                  value: _contactPreference,
                  decoration: InputDecoration(labelText: marketString(context, en: 'Preferred contact method', am: 'ተመራጭ የመገናኛ ዘዴ', mdy: '')),
                  items: [
                    DropdownMenuItem(value: null, child: Text(marketString(context, en: 'No preference', am: 'ምርጫ የለም', mdy: ''))),
                    DropdownMenuItem(value: 'phone', child: Text(marketString(context, en: 'Phone call', am: 'ስልክ ጥሪ', mdy: ''))),
                    DropdownMenuItem(value: 'sms', child: const Text('SMS')),
                    DropdownMenuItem(value: 'email', child: const Text('Email')),
                  ],
                  onChanged: (value) => setState(() => _contactPreference = value),
                ),
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                ],
                if (_notice != null) ...[
                  const SizedBox(height: 12),
                  Text(_notice!, style: TextStyle(color: Theme.of(context).colorScheme.primary)),
                ],
                const SizedBox(height: 20),
                FilledButton.icon(
                  key: const Key('save-customer-profile'),
                  onPressed: _saving ? null : _save,
                  icon: _saving ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.save_outlined),
                  label: Text(_saving ? marketString(context, en: 'Saving…', am: 'በማስቀመጥ ላይ…', mdy: '') : marketString(context, en: 'Save profile', am: 'መገለጫውን አስቀምጥ', mdy: '')),
                ),
              ],
            ),
          ),
  );
}
