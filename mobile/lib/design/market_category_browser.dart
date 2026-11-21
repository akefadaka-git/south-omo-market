import 'package:flutter/material.dart';

import 'market_design_system.dart';
import 'market_icon_pack.dart';
import '../l10n/market_strings.dart';

class MarketCategorySelection {
  const MarketCategorySelection({this.categoryId, this.searchTerm});
  final String? categoryId;
  final String? searchTerm;
}

/// Displays the category tree returned by the API. Category IDs and
/// parent-child relationships remain server-authoritative.
class MarketCategoryBrowserSheet extends StatelessWidget {
  const MarketCategoryBrowserSheet({super.key, required this.categories, this.selectedCategoryId});
  final List<Map<String, dynamic>> categories;
  final String? selectedCategoryId;

  @override
  Widget build(BuildContext context) {
    final roots = categories.where((category) => category['parent_id'] == null).toList()
      ..sort((a, b) => (a['name'] as String).compareTo(b['name'] as String));

    return SafeArea(
      child: SizedBox(
        height: MediaQuery.sizeOf(context).height * .82,
        child: Column(children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 18, 12, 8),
            child: Row(children: [
              Expanded(child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(marketString(context, en: 'Explore categories', am: 'ምድቦችን ይመልከቱ', mdy: ''),
                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
                  const SizedBox(height: 3),
                  Text(marketString(context, en: 'Choose a group, then select a subcategory', am: 'ምድብ ይምረጡ፣ ከዚያ ንዑስ ምድብ ይምረጡ', mdy: ''),
                    style: const TextStyle(color: MarketPalette.muted)),
                ],
              )),
              IconButton(
                tooltip: marketString(context, en: 'Close category browser', am: 'የምድብ መምረጫውን ዝጋ', mdy: ''),
                onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.close_rounded),
              ),
            ]),
          ),
          Expanded(child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
            children: [
              Card(child: ListTile(
                leading: const MarketCategoryGlyph(category: 'All categories', size: 46),
                title: Text(marketString(context, en: 'All categories', am: 'ሁሉም ምድቦች', mdy: ''),
                  style: const TextStyle(fontWeight: FontWeight.w700)),
                subtitle: Text(marketString(context, en: 'Show every published listing', am: 'የታተሙ ሁሉንም ዝርዝሮች አሳይ', mdy: '')),
                trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 16),
                onTap: () => Navigator.pop(context, const MarketCategorySelection()),
              )),
              const SizedBox(height: 8),
              ...roots.map((root) {
                final rootId = root['id'] as String;
                final name = root['name'] as String? ?? 'Market';
                final children = categories.where((category) =>
                  category['parent_id'] == rootId && category['is_leaf'] == true).toList()
                  ..sort((a, b) => (a['name'] as String).compareTo(b['name'] as String));
                return Card(
                  margin: const EdgeInsets.only(bottom: 10),
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(14, 12, 14, 14),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Row(children: [
                        MarketCategoryGlyph(category: name, size: 48),
                        const SizedBox(width: 12),
                        Expanded(child: Text(name,
                          style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16))),
                        Text('${children.length}',
                          style: const TextStyle(color: MarketPalette.muted, fontSize: 12)),
                      ]),
                      if (children.isNotEmpty) ...[
                        const SizedBox(height: 12),
                        Wrap(spacing: 7, runSpacing: 7, children: children.map((child) => ActionChip(
                          avatar: Icon(MarketIconPack.forCategory(name), size: 16),
                          label: Text(child['name'] as String? ?? ''),
                          onPressed: () => Navigator.pop(context,
                            MarketCategorySelection(categoryId: child['id'] as String)),
                        )).toList()),
                      ] else
                        Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Text(marketString(context, en: 'Subcategories are not available yet.', am: 'ንዑስ ምድቦች ገና አልተዘጋጁም።', mdy: ''),
                            style: const TextStyle(color: MarketPalette.muted, fontSize: 12)),
                        ),
                    ]),
                  ),
                );
              }),
            ],
          )),
        ]),
      ),
    );
  }
}
