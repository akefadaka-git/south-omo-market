import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../l10n/market_strings.dart';
import '../../design/market_design_system.dart';
import '../../design/market_brand_pages.dart';
import '../../design/market_category_browser.dart';
import 'listing_detail_page.dart';
import 'market_calendar_page.dart';

class MarketplaceDiscoveryPage extends StatefulWidget {
  const MarketplaceDiscoveryPage({
    super.key,
    required this.apiBaseUrl,
    required this.client,
    this.onSellerSignIn,
    this.onLocaleChanged,
  });

  final String apiBaseUrl;
  final http.Client client;
  final void Function(BuildContext context)? onSellerSignIn;
  final ValueChanged<Locale>? onLocaleChanged;

  @override
  State<MarketplaceDiscoveryPage> createState() => _MarketplaceDiscoveryPageState();
}

class _MarketplaceDiscoveryPageState extends State<MarketplaceDiscoveryPage> {
  List<Map<String, dynamic>> _categories = [];
  List<Map<String, dynamic>> _locations = [];
  List<Map<String, dynamic>> _listings = [];
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  String? _categoryId;
  String? _locationId;
  String _sort = 'newest';
  String? _error;
  bool _loading = true;
  bool _loadingMore = false;
  bool _hasMore = false;
  int _nextOffset = 0;

  String? _loadedLocale;

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
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _loadingMore = false; _error = null; _nextOffset = 0; });
    if (widget.apiBaseUrl.trim().isEmpty) {
      if (mounted) {
        setState(() {
          _error = marketString(
            context,
            en: 'The API server is not configured for this app build.',
            am: 'ለዚህ መተግበሪያ የኤፒአይ ሰርቨር አልተዋቀረም።',
            mdy: '',
          );
          _loading = false;
        });
      }
      return;
    }
    try {
      final categoryLanguage = Localizations.localeOf(context).languageCode;
      final listingUri = Uri.parse('${widget.apiBaseUrl}/listings').replace(
        queryParameters: {
          'limit': '50',
          'offset': '0',
          'sort': _sort,
          if (_searchQuery.trim().isNotEmpty) 'q': _searchQuery.trim(),
          if (_categoryId != null) 'category_id': _categoryId!,
          if (_locationId != null) 'location_id': _locationId!,
        },
      );
      final results = await Future.wait([
        widget.client.get(Uri.parse('${widget.apiBaseUrl}/categories?lang=$categoryLanguage')),
        widget.client.get(listingUri),
        widget.client.get(Uri.parse('${widget.apiBaseUrl}/locations?lang=$categoryLanguage')),
      ]);
      if (results.any((response) => response.statusCode != 200)) {
        throw Exception(marketString(context, en: 'Marketplace listings could not be loaded.', am: 'የገበያ ዝርዝሮችን መጫን አልተቻለም።', mdy: ''));
      }
      final categories = (jsonDecode(results[0].body) as List<dynamic>)
          .cast<Map<String, dynamic>>();
      final listings = (jsonDecode(results[1].body) as List<dynamic>)
          .cast<Map<String, dynamic>>();
      final locations = (jsonDecode(results[2].body) as List<dynamic>)
          .cast<Map<String, dynamic>>()
          .where((location) => location['level'] == 'town' || location['level'] == 'locality')
          .toList();
      if (!mounted) return;
      setState(() {
        _categories = categories;
        _locations = locations;
        _listings = listings;
        _nextOffset = listings.length;
        _hasMore = listings.length == 50;
      });
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _loadMore() async {
    if (_loading || _loadingMore || !_hasMore || widget.apiBaseUrl.trim().isEmpty) return;
    setState(() => _loadingMore = true);
    try {
      final uri = Uri.parse('${widget.apiBaseUrl}/listings').replace(
        queryParameters: {
          'limit': '50',
          'offset': _nextOffset.toString(),
          'sort': _sort,
          if (_searchQuery.trim().isNotEmpty) 'q': _searchQuery.trim(),
          if (_categoryId != null) 'category_id': _categoryId!,
          if (_locationId != null) 'location_id': _locationId!,
        },
      );
      final response = await widget.client.get(uri);
      if (response.statusCode != 200) {
        throw Exception(marketString(context, en: 'More listings could not be loaded.', am: 'ተጨማሪ ዝርዝሮችን መጫን አልተቻለም።', mdy: ''));
      }
      final rows = (jsonDecode(response.body) as List<dynamic>).cast<Map<String, dynamic>>();
      if (!mounted) return;
      setState(() {
        final seenIds = _listings
            .map((listing) => listing['id'])
            .whereType<String>()
            .toSet();
        final uniqueRows = rows.where((row) {
          final id = row['id'];
          return id is! String || id.isEmpty || seenIds.add(id);
        }).toList();
        _listings = [..._listings, ...uniqueRows];
        // Advance by the number returned, not the number appended: an item
        // may appear on adjacent pages if the catalogue changes mid-scroll.
        _nextOffset += rows.length;
        _hasMore = rows.length == 50;
      });
    } catch (error) {
      if (mounted) setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loadingMore = false);
    }
  }

  Future<void> _browseCategories() async {
    final selection = await showModalBottomSheet<MarketCategorySelection>(
      context: context,
      isScrollControlled: true,
      backgroundColor: MarketPalette.paper,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(26)),
      ),
      builder: (_) => MarketCategoryBrowserSheet(
        categories: _categories,
        selectedCategoryId: _categoryId,
      ),
    );
    if (selection == null || !mounted) return;
    _searchController.text = selection.searchTerm ?? '';
    setState(() {
      _categoryId = selection.categoryId;
      _searchQuery = selection.searchTerm ?? '';
    });
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    final query = _searchQuery.trim().toLowerCase();
    final visibleListings = _listings.where((item) {
      if (query.isEmpty) return true;
      final categoryName = _categories.firstWhere((entry) => entry['id'] == item['category_id'], orElse: () => {'name': ''})['name'] ?? '';
      final searchable = '${item['title'] ?? ''} ${item['description'] ?? ''} ${item['location'] ?? ''} $categoryName'.toLowerCase();
      return searchable.contains(query);
    }).toList();

    return Scaffold(
    appBar: AppBar(title: Row(mainAxisSize: MainAxisSize.min, children: [
      const MarketBrandMark(size: 34),
      const SizedBox(width: 10),
      Flexible(child: Text(marketString(context, en: 'South Omo Market', am: 'ደቡብ ኦሞ ገበያ', mdy: ''))),
    ]), actions: [
      if (widget.onLocaleChanged != null)
        PopupMenuButton<String>(
          tooltip: marketString(context, en: 'Change language', am: 'ቋንቋ ቀይር', mdy: ''),
          onSelected: (language) => widget.onLocaleChanged!(Locale(language)),
          itemBuilder: (_) => const [
            PopupMenuItem<String>(value: 'am', child: Text('አማርኛ')),
            PopupMenuItem<String>(value: 'en', child: Text('English')),
          ],
          icon: const Icon(Icons.language_rounded),
        ),
      if (widget.onSellerSignIn != null)
        IconButton(
          tooltip: marketString(context, en: 'Seller sign in', am: 'የሻጭ መግቢያ', mdy: ''),
          onPressed: () => widget.onSellerSignIn!(context),
          icon: const Icon(MarketIcons.seller),
        ),
      IconButton(
        tooltip: marketString(context, en: 'Market days', am: 'የገበያ ቀናት', mdy: ''),
        onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
          builder: (_) => MarketCalendarPage(apiBaseUrl: widget.apiBaseUrl, client: widget.client),
        )),
        icon: const Icon(Icons.calendar_month_rounded),
      ),
      IconButton(tooltip: marketString(context, en: 'Refresh listings', am: 'ዝርዝሮችን አድስ', mdy: ''), onPressed: _loading ? null : _load,
        icon: const Icon(Icons.refresh)),
      IconButton(
        tooltip: marketString(context, en: 'About South Omo Market', am: 'ስለ ደቡብ ኦሞ ገበያ', mdy: ''),
        onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
          builder: (_) => const MarketAboutPage(),
        )),
        icon: const Icon(Icons.info_outline_rounded),
      ),
    ]),
    body: Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(14, 10, 14, 4),
        child: MarketBrandPanel(
          title: marketString(context, en: 'Trade closer. Grow together.', am: 'በቅርብ ይገበያዩ፤ አብረው ያድጉ።', mdy: ''),
          subtitle: marketString(context, en: 'Discover goods, local skills and trusted businesses across South Omo.', am: 'በደቡብ ኦሞ ያሉ ምርቶችን፣ ክህሎቶችን እና ንግዶችን ያግኙ።', mdy: ''),
        ),
      ),
      Padding(
        padding: const EdgeInsets.fromLTRB(12, 12, 12, 8),
        child: TextField(
          key: const Key('marketplace-search'),
          controller: _searchController,
          onChanged: (value) => setState(() => _searchQuery = value),
          onSubmitted: (_) => _load(),
          textInputAction: TextInputAction.search,
          decoration: InputDecoration(
            labelText: marketString(context, en: 'Search products and services', am: 'ምርቶችን እና አገልግሎቶችን ፈልግ', mdy: ''),
            prefixIcon: const Icon(MarketIcons.search),
            suffixIcon: _searchQuery.isEmpty ? null : IconButton(
              tooltip: marketString(context, en: 'Clear search', am: 'ፍለጋውን አጽዳ', mdy: ''),
              onPressed: () {
                _searchController.clear();
                setState(() => _searchQuery = '');
              },
              icon: const Icon(Icons.close),
            ),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(16)),
          ),
        ),
      ),
      Padding(
        padding: const EdgeInsets.fromLTRB(12, 4, 12, 8),
        child: Row(children: [
          Expanded(child: OutlinedButton.icon(
            key: const Key('browse-market-categories'),
            onPressed: _loading ? null : _browseCategories,
            icon: const Icon(Icons.grid_view_rounded),
            label: Text(marketString(context, en: 'Browse categories', am: 'ምድቦችን ይመልከቱ', mdy: '')),
          )),
          if (_categoryId != null) ...[
            const SizedBox(width: 8),
            IconButton(
              tooltip: marketString(context, en: 'Clear category', am: 'ምድቡን አጽዳ', mdy: ''),
              onPressed: () {
                setState(() { _categoryId = null; _searchController.clear(); _searchQuery = ''; });
                _load();
              },
              icon: const Icon(Icons.filter_alt_off_rounded),
            ),
          ],
        ]),
      ),
      Padding(
        padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
        child: DropdownButtonFormField<String>(
          value: _locationId,
          decoration: InputDecoration(labelText: marketString(context, en: 'Filter by location', am: 'በአካባቢ አጣራ', mdy: '')),
          items: [
            DropdownMenuItem<String>(value: null, child: Text(marketString(context, en: 'All locations', am: 'ሁሉም አካባቢዎች', mdy: ''))),
            ..._locations.map((location) => DropdownMenuItem<String>(
              value: location['id'] as String,
              child: Text(location['name'] as String),
            )),
          ],
          onChanged: (value) { setState(() => _locationId = value); _load(); },
        ),
      ),
      Padding(
        padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
        child: DropdownButtonFormField<String>(
          key: const Key('marketplace-sort'),
          value: _sort,
          decoration: InputDecoration(
            labelText: marketString(context, en: 'Sort listings', am: 'ዝርዝሮችን ደርድር', mdy: ''),
          ),
          items: [
            DropdownMenuItem(value: 'newest', child: Text(marketString(context, en: 'Newest first', am: 'አዳዲሶች ቀድመው', mdy: ''))),
            DropdownMenuItem(value: 'price_asc', child: Text(marketString(context, en: 'Price: low to high', am: 'ዋጋ፦ ከዝቅተኛ ወደ ከፍተኛ', mdy: ''))),
            DropdownMenuItem(value: 'price_desc', child: Text(marketString(context, en: 'Price: high to low', am: 'ዋጋ፦ ከከፍተኛ ወደ ዝቅተኛ', mdy: ''))),
          ],
          onChanged: (value) {
            if (value == null) return;
            setState(() => _sort = value);
            _load();
          },
        ),
      ),
      Expanded(child: _loading
        ? const Center(child: CircularProgressIndicator())
        : _error != null
          ? Center(child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                Text(_error!, textAlign: TextAlign.center),
                const SizedBox(height: 14),
                OutlinedButton.icon(
                  key: const Key('retry-marketplace-load'),
                  onPressed: _loading ? null : _load,
                  icon: const Icon(Icons.refresh),
                  label: Text(marketString(
                    context,
                    en: 'Retry connection',
                    am: 'እንደገና ይሞክሩ',
                    mdy: '',
                  )),
                ),
              ]),
            ))
          : visibleListings.isEmpty
            ? Center(child: Text(
                query.isEmpty
                  ? marketString(context, en: 'No published listings found.', am: 'የታተሙ ማስታወቂያዎች አልተገኙም።', mdy: '')
                  : marketString(context, en: 'No matches. Try another search or clear the filters.', am: 'ውጤት አልተገኘም። ሌላ ፍለጋ ወይም ማጣሪያ ይሞክሩ።', mdy: ''),
                textAlign: TextAlign.center,
              ))
            : RefreshIndicator(
              onRefresh: _load,
              child: ListView.builder(
                itemCount: visibleListings.length + (_hasMore ? 1 : 0),
                itemBuilder: (context, index) {
                  if (index == visibleListings.length) {
                    return Padding(
                      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                      child: OutlinedButton(
                        onPressed: _loadingMore ? null : _loadMore,
                        child: _loadingMore
                            ? const SizedBox(
                                width: 18, height: 18,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : Text(marketString(context, en: 'Load more listings', am: 'ተጨማሪ ዝርዝሮችን ጫን', mdy: '')),
                      ),
                    );
                  }
                  final item = visibleListings[index];
                  final category = (_categories.firstWhere(
                    (entry) => entry['id'] == item['category_id'],
                    orElse: () => {'name': 'Local finds'},
                  )['name'] as String?) ?? 'Local finds';
                  return Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    child: MarketListingCard(
                      title: item['title'] as String? ?? 'Listing',
                      location: item['location'] as String? ?? '',
                      price: '${(((item['price_minor'] as num?) ?? 0) / 100).toStringAsFixed(2)} ETB',
                      category: category,
                      onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
                        builder: (_) => ListingDetailPage(
                          apiBaseUrl: widget.apiBaseUrl,
                          client: widget.client,
                          listingId: item['id'] as String,
                        ),
                      )),
                    ),
                  );
                },
              ),
            ),
      ),
    ]),
  );
  }
}

