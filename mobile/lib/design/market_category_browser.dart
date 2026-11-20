import 'package:flutter/material.dart';

import 'market_design_system.dart';
import 'market_icon_pack.dart';
import '../l10n/market_strings.dart';

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

  static List<String> _subcategoriesFor(Map<String, dynamic> category, {required bool amharic}) {
    final name = (category['name'] as String? ?? '').toLowerCase();
    final id = category['id'] as String? ?? '';
    if (name.contains('live') || name.contains('animal') || name.contains('እንስሳ') || id.endsWith('0001')) {
      return amharic
        ? ['ከብቶችና ላሞች', 'ፍየሎችና በጎች', 'ዶሮዎችና እንቁላል', 'ግመሎች', 'ማርና ሰም', 'ወተትና የወተት ውጤቶች']
        : ['Cattle and oxen', 'Goats and sheep', 'Poultry and eggs', 'Camels', 'Honey and beeswax', 'Milk and dairy'];
    }
    if (name.contains('agri') || name.contains('farm') || name.contains('crop') || name.contains('ግብርና') || id.endsWith('0002')) {
      return amharic
        ? ['በቆሎና እህሎች', 'ማሽላ', 'ጤፍና ስንዴ', 'ባቄላና ጥራጥሬዎች', 'ሰሊጥና ዘይት እህሎች', 'ፍራፍሬና አትክልቶች', 'ዘርና ችግኞች']
        : ['Maize and grains', 'Sorghum', 'Teff and wheat', 'Beans and pulses', 'Sesame and oilseeds', 'Fruits and vegetables', 'Seeds and seedlings'];
    }
    if (name.contains('food') || name.contains('grocer') || name.contains('ምግብ') || id.endsWith('0003')) {
      return amharic
        ? ['ማር', 'እህልና ዱቄት', 'ቅመማ ቅመሞችና ግብዓቶች', 'የተዘጋጀ ምግብ', 'አልኮል ያልሆኑ መጠጦች', 'የቤት ሸቀጣ ሸቀጦች']
        : ['Honey', 'Grain and flour', 'Spices and ingredients', 'Prepared food', 'Non-alcoholic drinks', 'Household groceries'];
    }
    if (name.contains('shop') || name.contains('product') || name.contains('retail') || name.contains('ሱቅ') || id.endsWith('0004')) {
      return amharic
        ? ['ልብስና ባህላዊ አልባሳት', 'ጫማና መለዋወጫዎች', 'የቤት ዕቃዎች', 'ስልኮችና ኤሌክትሮኒክስ', 'የፀሐይ መብራቶችና ባትሪዎች', 'መሣሪያዎችና የግንባታ እቃዎች', 'የተሽከርካሪ መለዋወጫዎች']
        : ['Clothing and traditional wear', 'Shoes and accessories', 'Household goods', 'Phones and electronics', 'Solar lamps and batteries', 'Tools and building supplies', 'Vehicle parts'];
    }
    if (name.contains('service') || name.contains('አገልግሎት') || id.endsWith('0005')) {
      return amharic
        ? ['የእርሻ ሠራተኛና ማረስ', 'የእንስሳትና የእንስሳት ሕክምና', 'ግንባታና አናጢነት', 'ቧንቧና ኤሌክትሪክ ሥራ', 'ብየዳና ጥገና', 'ልብስ ስፌትና የግል እንክብካቤ', 'ትምህርትና የሙያ አገልግሎቶች', 'ትራንስፖርትና የመሣሪያ ኪራይ']
        : ['Farm labour and ploughing', 'Livestock and veterinary services', 'Construction and carpentry', 'Plumbing and electrical work', 'Welding and repairs', 'Tailoring and personal care', 'Tutoring and professional services', 'Transport and equipment hire'];
    }
    if (name.contains('property') || name.contains('rental') || name.contains('home') || name.contains('ንብረት') || id.endsWith('0006')) {
      return amharic
        ? ['የሱቅና የሥራ ቦታ ኪራይ', 'ቤቶችና ማረፊያዎች', 'መሬትና ንብረት', 'የመሣሪያና ማሽን ኪራይ', 'የዝግጅት ድንኳኖችና ወንበሮች']
        : ['Shop and workspace rentals', 'Homes and accommodation', 'Land and property', 'Equipment and machinery hire', 'Event tents and chairs'];
    }
    return amharic ? ['ሌሎች የአካባቢ ምርቶች', 'ሌሎች የአካባቢ አገልግሎቶች'] : ['Other local goods', 'Other local services'];
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
              Expanded(child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(marketString(context, en: 'Explore categories', am: 'ምድቦችን ይመልከቱ', mdy: ''), style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
                  SizedBox(height: 3),
                  Text(marketString(context, en: 'Choose a market group or narrow it down', am: 'የገበያ ምድብ ይምረጡ ወይም ፍለጋውን ያጥቡ', mdy: ''), style: TextStyle(color: MarketPalette.muted)),
                ],
              )),
              IconButton(tooltip: marketString(context, en: 'Close category browser', am: 'የምድብ መምረጫውን ዝጋ', mdy: ''), onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.close_rounded)),
            ]),
          ),
          Expanded(child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
            children: [
              Card(child: ListTile(
                leading: const MarketCategoryGlyph(category: 'All categories', size: 46),
                title: Text(marketString(context, en: 'All categories', am: 'ሁሉም ምድቦች', mdy: ''), style: const TextStyle(fontWeight: FontWeight.w700)),
                subtitle: Text(marketString(context, en: 'Show every published listing', am: 'የታተሙ ሁሉንም ዝርዝሮች አሳይ', mdy: '')),
                trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 16),
                onTap: () => Navigator.pop(context, const MarketCategorySelection()),
              )),
              const SizedBox(height: 8),
              ...categories.map((category) {
                final id = category['id'] as String;
                final name = category['name'] as String? ?? 'Market';
                final selected = id == selectedCategoryId;
                final subcategories = _subcategoriesFor(category, amharic: Localizations.localeOf(context).languageCode == 'am');
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
                            Text(marketString(context, en: '${subcategories.length} browse topics', am: '${subcategories.length} የፍለጋ አማራጮች', mdy: ''),
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
