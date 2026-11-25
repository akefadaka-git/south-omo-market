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
  String _accountType = 'buyer';
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


  String _apiError(http.Response response) {
    final isAmharic = Localizations.localeOf(context).languageCode == 'am';
    try {
      final body = jsonDecode(response.body);
      if (body is Map<String, dynamic>) {
        final error = body['error'];
        if (error is Map<String, dynamic>) {
          final fields = error['field_errors'];
          if (fields is Map<String, dynamic> && fields.isNotEmpty) {
            final first = fields.entries.first;
            final field = first.key.toString();
            if (isAmharic) {
              const labels = {
                'phone_number': 'ስልክ ቁጥር',
                'display_name': 'ሙሉ ስም',
                'password': 'የይለፍ ቃል',
                'preferred_location_id': 'የሚመርጡት አካባቢ',
                'preferred_market_id': 'የሚመርጡት ገበያ',
                'account_type': 'የመለያ አይነት',
              };
              return (labels[field] ?? 'የመረጃ መስክ') + ' ያስተካክሉ።';
            }
            return field + ': ' + first.value.toString();
          }
          final message = error['message']?.toString();
          if (response.statusCode == 422 && isAmharic) {
            return 'ያስገቡት መረጃ ትክክል አይደለም። እባክዎ የተጠቆሙትን መስኮች ያስተካክሉ።';
          }
          if (message != null && message.isNotEmpty) return message;
        }
        final detail = body['detail'];
        if (detail is String) {
          if (isAmharic) {
            if (detail.contains('Preferred locality')) return 'የመረጡት አካባቢ አልተገኘም ወይም ንቁ አይደለም። እንደገና ይምረጡ።';
            if (detail.contains('Preferred market must be active')) return 'የመረጡት ገበያ ንቁ አይደለም።';
            if (detail.contains('does not belong')) return 'የመረጡት ገበያ ከአካባቢው ጋር አይዛመድም።';
            if (detail.contains('Phone number format')) return 'የስልክ ቁጥሩን ቅርጽ ያረጋግጡ።';
          }
          return detail;
        }
      }
    } catch (_) {
      // A malformed/non-JSON error body receives the safe status fallback below.
    }
    if (response.statusCode == 409) {
      return isAmharic ? 'ይህ ስልክ ቁጥር አስቀድሞ ተመዝግቧል። ወደ መግቢያ ይመለሱ።' : 'That phone number is already registered. Choose sign in.';
    }
    if (response.statusCode == 422) {
      return isAmharic ? 'ምዝገባው አልተሳካም። የገቡትን መረጃ ያረጋግጡ።' : 'Registration data is invalid. Review the highlighted fields.';
    }
    return isAmharic ? 'ምዝገባው አልተሳካም (${response.statusCode})።' : 'Registration failed (${response.statusCode}).';
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
            'account_type': _accountType,
          }),
        );
        if (created.statusCode != 201) {
          throw Exception(_apiError(created));
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
      if (_register) DropdownButtonFormField<String>(
        key: const Key('buyer-account-type'),
        value: _accountType,
        isExpanded: true,
        dropdownColor: Colors.white,
        style: const TextStyle(color: MarketPalette.ink, fontSize: 16, fontWeight: FontWeight.w600),
        decoration: InputDecoration(labelText: marketString(context, en: 'Register as', am: 'የመለያ አይነት', mdy: '')),
        items: [
          DropdownMenuItem(value: 'buyer', child: Text(marketString(context, en: 'Buyer', am: 'ገዢ', mdy: ''))),
          DropdownMenuItem(value: 'merchant', child: Text(marketString(context, en: 'Merchant / Seller', am: 'ነጋዴ / ሻጭ', mdy: ''))),
          DropdownMenuItem(value: 'bulk_distributor', child: Text(marketString(context, en: 'Bulk distributor', am: 'ጅምላ አከፋፋይ', mdy: ''))),
          DropdownMenuItem(value: 'producer', child: Text(marketString(context, en: 'Producer / Supplier', am: 'አምራች / አቅራቢ', mdy: ''))),
          DropdownMenuItem(value: 'service_provider', child: Text(marketString(context, en: 'Service provider', am: 'አገልግሎት ሰጪ', mdy: ''))),
          DropdownMenuItem(value: 'other', child: Text(marketString(context, en: 'Other', am: 'ሌላ', mdy: ''))),
        ],
        onChanged: (value) => setState(() => _accountType = value ?? 'buyer'),
      ),
      if (_register) const SizedBox(height: 10),
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
          dropdownColor: Colors.white,
          menuMaxHeight: 360,
          style: const TextStyle(color: MarketPalette.ink, fontSize: 16, fontWeight: FontWeight.w600),
          iconEnabledColor: MarketPalette.forest,
          decoration: InputDecoration(labelText: marketString(context, en: 'Preferred area (required)', am: 'የሚመርጡት አካባቢ (አስፈላጊ)', mdy: '')),
          items: _locations.map((row) => DropdownMenuItem<String>(
            value: row['id'] as String,
            child: Text((Localizations.localeOf(context).languageCode == 'am' ? (row['name_am'] ?? 'የአማርኛ ስም ይጠበቃል') : (row['name_en'] ?? '')) as String, overflow: TextOverflow.ellipsis),
          )).toList(),
          onChanged: _loadingOptions ? null : (value) => setState(() {
            _preferredLocationId = value;
            _preferredMarketId = null;
          }),
          validator: (value) => value == null ? marketString(context, en: 'Select your preferred area.', am: 'የሚመርጡትን አካባቢ ይምረጡ።', mdy: '') : null,
        ),
        const SizedBox(height: 10),
        DropdownButtonFormField<String>(
          key: const Key('buyer-preferred-market'),
          value: _preferredMarketId,
          isExpanded: true,
          dropdownColor: Colors.white,
          menuMaxHeight: 360,
          style: const TextStyle(color: MarketPalette.ink, fontSize: 16, fontWeight: FontWeight.w600),
          iconEnabledColor: MarketPalette.forest,
          decoration: InputDecoration(labelText: marketString(context, en: 'Preferred market (optional)', am: 'ተመራጭ ገበያ (አማራጭ)', mdy: '')),
          items: _markets.where((row) => _preferredLocationId == null ||
              row['location_id'] == null || row['location_id'] == _preferredLocationId)
            .map((row) => DropdownMenuItem<String>(
              value: row['id'] as String,
              child: Text((Localizations.localeOf(context).languageCode == 'am' ? (row['name_am'] ?? 'የአማርኛ ስም ይጠበቃል') : (row['name_en'] ?? '')) as String, overflow: TextOverflow.ellipsis),
            )).toList(),
          onChanged: (value) => setState(() => _preferredMarketId = value),
        ),
        const SizedBox(height: 10),
        DropdownButtonFormField<String>(
          key: const Key('buyer-preferred-language'),
          value: _preferredLanguage,
          dropdownColor: Colors.white,
          menuMaxHeight: 240,
          style: const TextStyle(color: MarketPalette.ink, fontSize: 16, fontWeight: FontWeight.w600),
          iconEnabledColor: MarketPalette.forest,
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
