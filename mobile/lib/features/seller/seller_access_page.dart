import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../marketplace_pages.dart';
import '../../l10n/market_strings.dart';
import '../../design/market_design_system.dart';
import 'seller_inbox_page.dart';

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
            ? marketString(context, en: 'That phone number is already registered.', am: 'ይህ ስልክ ቁጥር አስቀድሞ ተመዝግቧል።', mdy: '')
            : marketString(context, en: 'Seller account registration failed (${created.statusCode}).', am: 'የሻጭ መለያ መመዝገብ አልተሳካም (${created.statusCode})።', mdy: ''));
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

