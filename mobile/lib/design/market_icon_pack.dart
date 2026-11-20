import 'package:flutter/material.dart';

/// Curated semantic icon set for South Omo Market.
/// Keep category and action glyphs consistent across all marketplace surfaces.
abstract final class MarketIconPack {
  static const explore = Icons.explore_rounded;
  static const products = Icons.inventory_2_outlined;
  static const services = Icons.handyman_outlined;
  static const livestock = Icons.pets_outlined;
  static const crops = Icons.grass_rounded;
  static const food = Icons.restaurant_rounded;
  static const honey = Icons.hive_outlined;
  static const retail = Icons.storefront_rounded;
  static const electronics = Icons.devices_other_rounded;
  static const building = Icons.construction_rounded;
  static const transport = Icons.two_wheeler_rounded;
  static const home = Icons.home_work_outlined;
  static const education = Icons.school_outlined;
  static const repair = Icons.build_circle_outlined;
  static const farming = Icons.agriculture_rounded;
  static const business = Icons.business_center_outlined;
  static const search = Icons.search_rounded;
  static const location = Icons.location_on_outlined;
  static const message = Icons.chat_bubble_outline_rounded;
  static const seller = Icons.store_mall_directory_outlined;
  static const verified = Icons.verified_rounded;
  static const filter = Icons.tune_rounded;
  static const refresh = Icons.refresh_rounded;
  static const about = Icons.info_outline_rounded;

  static IconData forCategory(String? category) {
    final value = (category ?? '').toLowerCase();
    if (value.contains('live') || value.contains('animal')) return livestock;
    if (value.contains('agri') || value.contains('farm') || value.contains('crop')) return crops;
    if (value.contains('food') || value.contains('grocery')) return food;
    if (value.contains('honey') || value.contains('dairy')) return honey;
    if (value.contains('service') || value.contains('repair')) return services;
    if (value.contains('electronic')) return electronics;
    if (value.contains('building') || value.contains('construction')) return building;
    if (value.contains('transport') || value.contains('vehicle')) return transport;
    if (value.contains('property') || value.contains('rental') || value.contains('home')) return home;
    if (value.contains('education') || value.contains('training')) return education;
    if (value.contains('business') || value.contains('professional')) return business;
    return retail;
  }
}

/// A small branded icon tile with a consistent tactile shape and semantics.
class MarketCategoryGlyph extends StatelessWidget {
  const MarketCategoryGlyph({
    super.key,
    required this.category,
    this.size = 54,
    this.iconSize = 25,
  });

  final String category;
  final double size;
  final double iconSize;

  @override
  Widget build(BuildContext context) => Semantics(
    label: category,
    image: true,
    child: Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(size * .32),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFFDDF2E9), Color(0xFFF5EBDD)],
        ),
        border: Border.all(color: const Color(0xFFDCE6DF)),
      ),
      child: Icon(MarketIconPack.forCategory(category),
        size: iconSize, color: const Color(0xFF155B50)),
    ),
  );
}
