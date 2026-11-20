import 'package:flutter/material.dart';

import 'market_design_system.dart';
import 'market_icon_pack.dart';

class MarketCategorySelection {
  const MarketCategorySelection({this.categoryId, this.searchTerm});
  final String? categoryId;
  final String? searchTerm;
}

/// The API's broad category IDs remain authoritative; subcategory chips refine
/// the currently loaded results locally until the API exposes a full hierarchy.
class MarketCategoryBrowserSheet extends StatelessWidget {
  const MarketCategoryBrowserSheet({super.key, required this.categories, this.selectedCategoryId});
  final List<Map<String, dynamic>> categories;
  final String? selectedCategoryId;

  static List<String> _subcategoriesFor(Map<String, dynamic> category) {
    final name = (category['name'] as String? ?? '').toLowerCase();
    final id = category['id'] as String? ?? '';
    if (name.contains('live') || name.contains('animal') || name.contains('እንስሳ') || id.endsWith('0001')) {
      return ['Cattle and oxen', 'Goats and sheep', 'Poultry and eggs', 'Camels', 'Honey and beeswax', 'Milk and dairy'];
    }
    if (name.contains('agri') || name.contains('farm') || name.contains('crop') || name.contains('ግብርና') || id.endsWith('0002')) {
      return ['Maize and grains', 'Sorghum', 'Teff and wheat', 'Beans and pulses', 'Sesame and oilseeds', 'Fruits and vegetables', 'Seeds and seedlings'];
    }
    if (name.contains('food') || name.contains('grocer') || name.contains('ምግብ') || id.endsWith('0003')) {
      return ['Honey', 'Grain and flour', 'Spices and ingredients', 'Prepared food', 'Non-alcoholic drinks', 'Household groceries'];
    }
    if (name.contains('shop') || name.contains('product') || name.contains('retail') || name.contains('ሱቅ') || id.endsWith('0004')) {
      return ['Clothing and traditional wear', 'Shoes and accessories', 'Household goods', 'Phones and electronics', 'Solar lamps and batteries', 'Tools and building supplies', 'Vehicle parts'];
    }
    if (name.contains('service') || name.contains('አገልግሎት') || id.endsWith('0005')) {
      return ['Farm labour and ploughing', 'Livestock and veterinary services', 'Construction and carpentry', 'Plumbing and electrical work', 'Welding and repairs', 'Tailoring and personal care', 'Tutoring and professional services', 'Transport and equipment hire'];
    }
    if (name.contains('property') || name.contains('rental') || name.contains('home') || name.contains('ንብረት') || id.endsWith('0006')) {
      return ['Shop and workspace rentals', 'Homes and accommodation', 'Land and property', 'Equipment and machinery hire', 'Event tents and chairs'];
    }
    return const ['Other local goods', 'Other local services'];
  }

  @override
  Widget build(BuildContext context) => SafeArea(
    child: SizedBox(
      height: MediaQuery.sizeOf(context).height * .82,
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 18, 12, 8),
            child: Row(children: [
              const Expanded(child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Explore categories', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
                  SizedBox(height: 3),
                  Text('Choose a market group or narrow it down', style: TextStyle(color: MarketPalette.muted)),
                ],
              )),
              IconButton(tooltip: 'Close category browser', onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.close_rounded)),
            ]),
          ),
          Expanded(child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
            children: [
              Card(child: ListTile(
                leading: const MarketCategoryGlyph(category: 'All categories', size: 46),
                title: const Text('All categories', style: TextStyle(fontWeight: FontWeight.w700)),
                subtitle: const Text('Show every published listing'),
                trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 16),
                onTap: () => Navigator.pop(context, const MarketCategorySelection()),
              )),
              const SizedBox(height: 8),
              ...categories.map((category) {
                final id = category['id'] as String;
                final name = category['name'] as String? ?? 'Market';
                final selected = id == selectedCategoryId;
                final subcategories = _subcategoriesFor(category);
                return Card(
                  margin: const EdgeInsets.only(bottom: 10),
                  color: selected ? const Color(0xFFF0F7F2) : Colors.white,
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(14, 12, 14, 14),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      InkWell(
                        borderRadius: BorderRadius.circular(14),
                        onTap: () => Navigator.pop(context, MarketCategorySelection(categoryId: id)),
                        child: Row(children: [
                          MarketCategoryGlyph(category: name, size: 48),
                          const SizedBox(width: 12),
                          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text(name, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                            Text('${subcategories.length} browse topics',
                              style: const TextStyle(color: MarketPalette.muted, fontSize: 12)),
                          ])),
                          Icon(selected ? Icons.check_circle_rounded : Icons.arrow_forward_ios_rounded,
                            color: selected ? MarketPalette.jade : MarketPalette.muted, size: 18),
                        ]),
                      ),
                      const SizedBox(height: 12),
                      Wrap(spacing: 7, runSpacing: 7, children: subcategories.map((topic) => ActionChip(
                        avatar: Icon(MarketIconPack.forCategory(name), size: 16),
                        label: Text(topic),
                        onPressed: () => Navigator.pop(context,
                          MarketCategorySelection(categoryId: id, searchTerm: topic)),
                      )).toList()),
                    ]),
                  ),
                );
              }),
            ],
          )),
        ],
      ),
    ),
  );
}
