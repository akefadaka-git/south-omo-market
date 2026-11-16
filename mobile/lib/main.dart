import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:http/http.dart' as http;

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
