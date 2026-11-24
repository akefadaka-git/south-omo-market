import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../../l10n/market_strings.dart';
import '../../design/market_design_system.dart';

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
  bool _loadingOptions = false;
  String? _error;
  String? _optionsError;
  String? _preferredLocationId;
  String? _preferredMarketId;
  String _preferredLanguage = 'am';
  List<Map<String, dynamic>> _locations = [];
  List<Map<String, dynamic>> _markets = [];

  @override
  void dispose() {
    _phone.dispose(); _name.dispose(); _password.dispose(); super.dispose();
  }

  Future<void> _loadRegistrationOptions() async {
    if (_locations.isNotEmpty || _loadingOptions) return;
    setState(() { _loadingOptions = true; _optionsError = null; });
    try {
      final language = Localizations.localeOf(context).languageCode;
      final responses = await Future.wait([
        widget.client.get(Uri.parse('${widget.apiBaseUrl}/locations?lang=$language')),
        widget.client.get(Uri.parse('${widget.apiBaseUrl}/markets?lang=$language')),
      ]);
      if (responses.any((response) => response.statusCode != 200)) {
        throw Exception('Could not load towns and markets. You can retry by closing and reopening registration.');
      }
      final locations = (jsonDecode(responses[0].body) as List<dynamic>)
          .cast<Map<String, dynamic>>()
          .where((row) => row['level'] == 'town' || row['level'] == 'locality')
          .toList();
      final markets = (jsonDecode(responses[1].body) as List<dynamic>)
          .cast<Map<String, dynamic>>();
      if (!mounted) return;
      setState(() { _locations = locations; _markets = markets; });
    } catch (error) {
      if (mounted) setState(() => _optionsError = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loadingOptions = false);
    }
  }

  Future<void> _authenticate() async {
    if (_phone.text.trim().length < 7 || _password.text.length < 6 ||
        (_register && (_name.text.trim().isEmpty || _preferredLocationId == null))) {
      setState(() => _error = marketString(context, en: 'Enter a valid phone number, password (at least 6 characters), and display name when registering.', am: 'ትክክለኛ ስልክ ቁጥር፣ ቢያንስ 6 ፊደላት ያለው የይለፍ ቃል እና ሲመዘገቡ የሚታይ ስም ያስገቡ።', mdy: ''));
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
            'preferred_location_id': _preferredLocationId,
            'preferred_market_id': _preferredMarketId,
            'preferred_language': _preferredLanguage,
          }),
        );
        if (created.statusCode != 201) {
          throw Exception(created.statusCode == 409
            ? marketString(context, en: 'That phone number is already registered. Choose sign in.', am: 'ይህ ስልክ ቁጥር አስቀድሞ ተመዝግቧል። ወደ መግቢያ ይመለሱ።', mdy: '')
            : marketString(context, en: 'Account registration failed (${created.statusCode}).', am: 'መለያ መመዝገብ አልተሳካም (${created.statusCode})።', mdy: ''));
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
      if (response.statusCode != 200) throw Exception(marketString(context, en: 'Sign in failed (${response.statusCode}).', am: 'መግባት አልተሳካም (${response.statusCode})።', mdy: ''));
      final token = (jsonDecode(response.body) as Map<String, dynamic>)['access_token'] as String?;
      if (token == null || token.isEmpty) throw Exception(marketString(context, en: 'The API did not return an access token.', am: 'ከአገልጋዩ የመግቢያ ቁልፍ አልተመለሰም።', mdy: ''));
      if (mounted) Navigator.of(context, rootNavigator: true).pop<String>(token);
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Row(children: [
      const MarketBrandMark(size: 34),
      const SizedBox(width: 10),
      Expanded(child: Text(_register ? marketString(context, en: 'Create buyer account', am: 'የገዢ መለያ ይፍጠሩ', mdy: '') : marketString(context, en: 'Buyer sign in', am: 'የገዢ መግቢያ', mdy: ''))),
    ]),
    content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
      Text(_register
        ? marketString(context, en: 'Create an account to contact sellers and follow up on your inquiries.', am: 'ሻጮችን ለማነጋገርና የላኩትን ጥያቄ ለመከታተል መለያ ይፍጠሩ።', mdy: '')
        : marketString(context, en: 'Sign in to contact this seller. Your registered phone number is shared with the seller.', am: 'ይህን ሻጭ ለማነጋገር ይግቡ። የተመዘገበው ስልክ ቁጥርዎ ለሻጩ ይታያል።', mdy: '')),
      const SizedBox(height: 14),
      if (_register) TextField(key: const Key('buyer-display-name'), controller: _name,
        decoration: InputDecoration(labelText: marketString(context, en: 'Full name', am: 'ሙሉ ስም', mdy: ''), prefixIcon: Icon(Icons.person_outline))),
      if (_register) ...[
        const SizedBox(height: 10),
        if (_loadingOptions) const LinearProgressIndicator(),
        if (_optionsError != null) Align(
          alignment: Alignment.centerLeft,
          child: Text(_optionsError!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
        ),
        DropdownButtonFormField<String>(
          key: const Key('buyer-preferred-location'),
          value: _preferredLocationId,
          isExpanded: true,
          decoration: InputDecoration(labelText: marketString(context, en: 'Preferred town / locality (required)', am: 'ተመራጭ ከተማ / አካባቢ (አስፈላጊ)', mdy: '')),
          items: _locations.map((row) => DropdownMenuItem<String>(
            value: row['id'] as String,
            child: Text((row['name'] ?? row['name_en'] ?? '') as String, overflow: TextOverflow.ellipsis),
          )).toList(),
          onChanged: _loadingOptions ? null : (value) => setState(() {
            _preferredLocationId = value;
            _preferredMarketId = null;
          }),
          validator: (value) => value == null ? marketString(context, en: 'Select your preferred town or locality.', am: 'ተመራጭ ከተማዎን ወይም አካባቢዎን ይምረጡ።', mdy: '') : null,
        ),
        const SizedBox(height: 10),
        DropdownButtonFormField<String>(
          key: const Key('buyer-preferred-market'),
          value: _preferredMarketId,
          isExpanded: true,
          decoration: InputDecoration(labelText: marketString(context, en: 'Preferred market (optional)', am: 'ተመራጭ ገበያ (አማራጭ)', mdy: '')),
          items: _markets.where((row) => _preferredLocationId == null ||
              row['location_id'] == null || row['location_id'] == _preferredLocationId)
            .map((row) => DropdownMenuItem<String>(
              value: row['id'] as String,
              child: Text(row['name'] as String, overflow: TextOverflow.ellipsis),
            )).toList(),
          onChanged: (value) => setState(() => _preferredMarketId = value),
        ),
        const SizedBox(height: 10),
        DropdownButtonFormField<String>(
          key: const Key('buyer-preferred-language'),
          value: _preferredLanguage,
          decoration: InputDecoration(labelText: marketString(context, en: 'Preferred language', am: 'ተመራጭ ቋንቋ', mdy: '')),
          items: [
            DropdownMenuItem(value: 'am', child: Text('አማርኛ')),
            DropdownMenuItem(value: 'en', child: Text('English')),
          ],
          onChanged: (value) => setState(() => _preferredLanguage = value ?? 'am'),
        ),
      ],
      TextField(key: const Key('buyer-phone'), controller: _phone, keyboardType: TextInputType.phone,
        decoration: InputDecoration(labelText: marketString(context, en: 'Phone number', am: 'ስልክ ቁጥር', mdy: ''), prefixIcon: Icon(Icons.phone_outlined))),
      TextField(key: const Key('buyer-password'), controller: _password, obscureText: true,
        decoration: InputDecoration(labelText: marketString(context, en: 'Password (minimum 6 characters)', am: 'የይለፍ ቃል (ቢያንስ 6 ፊደላት)', mdy: ''), prefixIcon: Icon(Icons.lock_outline))),
      if (_error != null) Padding(
        padding: const EdgeInsets.only(top: 8),
        child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
      ),
    ])),
    actions: [
      TextButton(
        onPressed: _busy ? null : () {
          final enteringRegistration = !_register;
          setState(() { _register = enteringRegistration; _error = null; });
          if (enteringRegistration) _loadRegistrationOptions();
        },
        child: Text(_register ? marketString(context, en: 'I already have an account', am: 'መለያ አለኝ', mdy: '') : marketString(context, en: 'Create account', am: 'መለያ ፍጠር', mdy: '')),
      ),
      FilledButton(onPressed: _busy ? null : _authenticate,
        child: Text(_busy ? marketString(context, en: 'Please wait…', am: 'እባክዎ ይጠብቁ…', mdy: '') : (_register ? marketString(context, en: 'Register and continue', am: 'ተመዝግበው ይቀጥሉ', mdy: '') : marketString(context, en: 'Sign in', am: 'ግባ', mdy: '')))),
    ],
  );
}
