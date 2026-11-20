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
  String? _error;

  @override
  void dispose() {
    _phone.dispose(); _name.dispose(); _password.dispose(); super.dispose();
  }

  Future<void> _authenticate() async {
    if (_phone.text.trim().length < 7 || _password.text.length < 12 ||
        (_register && _name.text.trim().isEmpty)) {
      setState(() => _error = marketString(context, en: 'Enter a valid phone number, password (at least 12 characters), and display name when registering.', am: 'ትክክለኛ ስልክ ቁጥር፣ ቢያንስ 12 ፊደላት ያለው የይለፍ ቃል እና ሲመዘገቡ የሚታይ ስም ያስገቡ።', mdy: ''));
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
        decoration: InputDecoration(labelText: marketString(context, en: 'Display name', am: 'የሚታይ ስም', mdy: ''), prefixIcon: Icon(Icons.person_outline))),
      TextField(key: const Key('buyer-phone'), controller: _phone, keyboardType: TextInputType.phone,
        decoration: InputDecoration(labelText: marketString(context, en: 'Phone number', am: 'ስልክ ቁጥር', mdy: ''), prefixIcon: Icon(Icons.phone_outlined))),
      TextField(key: const Key('buyer-password'), controller: _password, obscureText: true,
        decoration: InputDecoration(labelText: marketString(context, en: 'Password (minimum 12 characters)', am: 'የይለፍ ቃል (ቢያንስ 12 ፊደላት)', mdy: ''), prefixIcon: Icon(Icons.lock_outline))),
      if (_error != null) Padding(
        padding: const EdgeInsets.only(top: 8),
        child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
      ),
    ])),
    actions: [
      TextButton(
        onPressed: _busy ? null : () => setState(() { _register = !_register; _error = null; }),
        child: Text(_register ? marketString(context, en: 'I already have an account', am: 'መለያ አለኝ', mdy: '') : marketString(context, en: 'Create account', am: 'መለያ ፍጠር', mdy: '')),
      ),
      FilledButton(onPressed: _busy ? null : _authenticate,
        child: Text(_busy ? marketString(context, en: 'Please wait…', am: 'እባክዎ ይጠብቁ…', mdy: '') : (_register ? marketString(context, en: 'Register and continue', am: 'ተመዝግበው ይቀጥሉ', mdy: '') : marketString(context, en: 'Sign in', am: 'ግባ', mdy: '')))),
    ],
  );
}
