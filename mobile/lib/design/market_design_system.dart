import 'package:flutter/material.dart';

/// South Omo Market's visual language: a contemporary trading identity
/// inspired by the Omo river basin, woven craft geometry and open horizons.
abstract final class MarketPalette {
  static const ink = Color(0xFF102B2A);
  static const deep = Color(0xFF0B2024);
  static const forest = Color(0xFF155B50);
  static const jade = Color(0xFF1B8A78);
  static const mint = Color(0xFFB9E7D8);
  static const sand = Color(0xFFF4EBDD);
  static const paper = Color(0xFFFCFAF5);
  static const clay = Color(0xFFE87955);
  static const sun = Color(0xFFF2BD59);
  static const muted = Color(0xFF687C78);
  static const line = Color(0xFFDCE6DF);
  static const danger = Color(0xFFB94343);
}

/// Central theme and component geometry. Kept dependency-free for offline use.
abstract final class MarketDesignSystem {
  static ThemeData get lightTheme {
    const scheme = ColorScheme(
      brightness: Brightness.light,
      primary: MarketPalette.forest,
      onPrimary: Colors.white,
      secondary: MarketPalette.clay,
      onSecondary: Colors.white,
      error: MarketPalette.danger,
      onError: Colors.white,
      surface: MarketPalette.paper,
      onSurface: MarketPalette.ink,
      surfaceContainerHighest: Color(0xFFEAF1EC),
      onSurfaceVariant: MarketPalette.muted,
      outline: MarketPalette.line,
      shadow: Color(0x1A102B2A),
      inverseSurface: MarketPalette.deep,
      onInverseSurface: Colors.white,
      inversePrimary: MarketPalette.mint,
      tertiary: MarketPalette.sun,
      onTertiary: MarketPalette.ink,
    );

    final base = ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: MarketPalette.paper,
      visualDensity: VisualDensity.standard,
      splashFactory: InkSparkle.splashFactory,
    );

    final text = base.textTheme.copyWith(
      displayLarge: base.textTheme.displayLarge?.copyWith(
        color: MarketPalette.ink, fontWeight: FontWeight.w800, letterSpacing: -1.5),
      displayMedium: base.textTheme.displayMedium?.copyWith(
        color: MarketPalette.ink, fontWeight: FontWeight.w800, letterSpacing: -1),
      headlineLarge: base.textTheme.headlineLarge?.copyWith(
        color: MarketPalette.ink, fontWeight: FontWeight.w800, letterSpacing: -.6),
      headlineMedium: base.textTheme.headlineMedium?.copyWith(
        color: MarketPalette.ink, fontWeight: FontWeight.w700),
      titleLarge: base.textTheme.titleLarge?.copyWith(
        color: MarketPalette.ink, fontWeight: FontWeight.w700),
      titleMedium: base.textTheme.titleMedium?.copyWith(
        color: MarketPalette.ink, fontWeight: FontWeight.w700),
      bodyLarge: base.textTheme.bodyLarge?.copyWith(
        color: MarketPalette.ink, height: 1.45),
      bodyMedium: base.textTheme.bodyMedium?.copyWith(
        color: MarketPalette.muted, height: 1.4),
    );

    TextStyle? ethiopic(TextStyle? style) => style?.copyWith(
      fontFamilyFallback: const ['Noto Sans Ethiopic', 'NotoSansEthiopic'],
    );
    final localizedText = text.copyWith(
      displayLarge: ethiopic(text.displayLarge),
      displayMedium: ethiopic(text.displayMedium),
      displaySmall: ethiopic(text.displaySmall),
      headlineLarge: ethiopic(text.headlineLarge),
      headlineMedium: ethiopic(text.headlineMedium),
      headlineSmall: ethiopic(text.headlineSmall),
      titleLarge: ethiopic(text.titleLarge),
      titleMedium: ethiopic(text.titleMedium),
      titleSmall: ethiopic(text.titleSmall),
      bodyLarge: ethiopic(text.bodyLarge),
      bodyMedium: ethiopic(text.bodyMedium),
      bodySmall: ethiopic(text.bodySmall),
      labelLarge: ethiopic(text.labelLarge),
      labelMedium: ethiopic(text.labelMedium),
      labelSmall: ethiopic(text.labelSmall),
    );

    return base.copyWith(
      textTheme: localizedText,
      appBarTheme: const AppBarTheme(
        backgroundColor: MarketPalette.paper,
        foregroundColor: MarketPalette.ink,
        elevation: 0,
        centerTitle: false,
        scrolledUnderElevation: 0,
        titleTextStyle: TextStyle(
          color: MarketPalette.ink, fontSize: 19, fontWeight: FontWeight.w800,
          letterSpacing: -.35),
      ),
      cardTheme: CardThemeData(
        color: Colors.white,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(22),
          side: const BorderSide(color: MarketPalette.line, width: .8),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 17),
        hintStyle: const TextStyle(color: MarketPalette.muted),
        labelStyle: const TextStyle(color: MarketPalette.muted, fontWeight: FontWeight.w600),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: const BorderSide(color: MarketPalette.line),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: const BorderSide(color: MarketPalette.line),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: const BorderSide(color: MarketPalette.jade, width: 1.7),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: MarketPalette.forest,
          foregroundColor: Colors.white,
          minimumSize: const Size(48, 52),
          padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 15),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: MarketPalette.forest,
          minimumSize: const Size(44, 48),
          side: const BorderSide(color: MarketPalette.line),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
        ),
      ),
      chipTheme: base.chipTheme.copyWith(
        backgroundColor: const Color(0xFFEAF1EC),
        selectedColor: MarketPalette.forest,
        side: BorderSide.none,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13)),
        labelStyle: const TextStyle(fontWeight: FontWeight.w600),
      ),
      dividerTheme: const DividerThemeData(color: MarketPalette.line, thickness: 1),
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: MarketPalette.jade, linearTrackColor: MarketPalette.mint),
    );
  }
}

/// Small, original vector brand mark; no raster image or network dependency.
class MarketBrandMark extends StatelessWidget {
  const MarketBrandMark({super.key, this.size = 42, this.onDark = false});

  final double size;
  final bool onDark;

  @override
  Widget build(BuildContext context) => SizedBox.square(
    dimension: size,
    child: CustomPaint(painter: _MarketMarkPainter(onDark: onDark)),
  );
}

class _MarketMarkPainter extends CustomPainter {
  const _MarketMarkPainter({required this.onDark});
  final bool onDark;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final radius = Radius.circular(size.width * .31);
    final bg = Paint()..color = onDark ? Colors.white.withValues(alpha: .13) : MarketPalette.deep;
    canvas.drawRRect(RRect.fromRectAndRadius(rect, radius), bg);
    final scale = size.width / 48;
    canvas.save();
    canvas.scale(scale);
    final mint = Paint()..color = MarketPalette.mint..style = PaintingStyle.stroke
      ..strokeWidth = 2.6..strokeCap = StrokeCap.round..strokeJoin = StrokeJoin.round;
    final sun = Paint()..color = MarketPalette.sun;
    final path = Path()
      ..moveTo(8, 31)..quadraticBezierTo(17, 20, 24, 29)
      ..quadraticBezierTo(32, 38, 40, 25);
    canvas.drawPath(path, mint);
    final ridge = Path()
      ..moveTo(9, 23)..lineTo(18, 13)..lineTo(24, 20)
      ..lineTo(31, 10)..lineTo(40, 22);
    canvas.drawPath(ridge, mint);
    canvas.drawCircle(const Offset(34, 13), 3.2, sun);
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _MarketMarkPainter oldDelegate) =>
      oldDelegate.onDark != onDark;
}

/// A semantic icon vocabulary so the app does not depend on arbitrary icon choices.
abstract final class MarketIcons {
  static const livestock = Icons.pets_outlined;
  static const agriculture = Icons.grass_outlined;
  static const food = Icons.restaurant_outlined;
  static const retail = Icons.storefront_outlined;
  static const services = Icons.handyman_outlined;
  static const property = Icons.home_work_outlined;
  static const search = Icons.search_rounded;
  static const location = Icons.location_on_outlined;
  static const verified = Icons.verified_rounded;
  static const seller = Icons.store_mall_directory_outlined;
  static const message = Icons.chat_bubble_outline_rounded;
  static const explore = Icons.explore_outlined;
  static const filter = Icons.tune_rounded;
  static const refresh = Icons.refresh_rounded;

  static IconData category(String? name) {
    final key = (name ?? '').toLowerCase();
    if (key.contains('live') || key.contains('animal')) return livestock;
    if (key.contains('agri') || key.contains('farm')) return agriculture;
    if (key.contains('food') || key.contains('grocery')) return food;
    if (key.contains('service')) return services;
    if (key.contains('property') || key.contains('rental')) return property;
    return retail;
  }
}

/// Brand panel used at the top of the discovery experience and seller entry.
class MarketBrandPanel extends StatelessWidget {
  const MarketBrandPanel({super.key, required this.title, required this.subtitle});
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.fromLTRB(20, 20, 20, 22),
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(26),
      gradient: const LinearGradient(
        begin: Alignment.topLeft, end: Alignment.bottomRight,
        colors: [MarketPalette.deep, MarketPalette.forest, MarketPalette.jade]),
      boxShadow: const [BoxShadow(
        color: Color(0x1C0B2024), blurRadius: 22, offset: Offset(0, 10))],
    ),
    child: Stack(
      children: [
        Positioned(right: -18, top: -25, child: Container(
          width: 142, height: 142,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(color: Colors.white.withValues(alpha: .10), width: 18),
          ),
        )),
        Positioned(right: 35, bottom: -48, child: Container(
          width: 110, height: 110,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(color: MarketPalette.mint.withValues(alpha: .12), width: 14),
          ),
        )),
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const MarketBrandMark(size: 54, onDark: true),
          const SizedBox(width: 14),
          Expanded(child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(
                color: Colors.white, fontSize: 21, height: 1.2,
                fontWeight: FontWeight.w800, letterSpacing: -.4)),
              const SizedBox(height: 6),
              Text(subtitle, style: TextStyle(
                color: Colors.white.withValues(alpha: .82),
                fontSize: 13, height: 1.4, fontWeight: FontWeight.w500)),
            ],
          )),
        ]),
        Positioned(left: 2, bottom: 0, child: Container(
          width: 34, height: 3,
          decoration: BoxDecoration(color: MarketPalette.sun,
            borderRadius: BorderRadius.circular(4)),
        )),
      ],
    ),
  );
}


/// Image-led listing card with a resilient offline/error fallback.
class MarketListingCard extends StatelessWidget {
  const MarketListingCard({
    super.key,
    required this.title,
    required this.location,
    required this.price,
    required this.category,
    required this.onTap,
    this.imageUrl,
  });

  final String title;
  final String location;
  final String price;
  final String category;
  final String? imageUrl;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final fallback = Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [MarketPalette.mint, Color(0xFFEAF1EC), MarketPalette.sand],
        ),
      ),
      child: Center(
        child: Icon(MarketIcons.category(category),
          size: 34, color: MarketPalette.forest),
      ),
    );

    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              SizedBox(
                width: 108,
                height: 112,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(16),
                  child: imageUrl == null || imageUrl!.isEmpty
                    ? fallback
                    : Image.network(
                        imageUrl!,
                        fit: BoxFit.cover,
                        filterQuality: FilterQuality.low,
                        errorBuilder: (context, error, stackTrace) => fallback,
                        loadingBuilder: (context, child, progress) =>
                          progress == null ? child : fallback,
                      ),
                ),
              ),
              const SizedBox(width: 13),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: MarketPalette.mint.withValues(alpha: .55),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        category,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: MarketPalette.forest,
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                    const SizedBox(height: 7),
                    Text(
                      title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        const Icon(MarketIcons.location,
                          size: 14, color: MarketPalette.muted),
                        const SizedBox(width: 4),
                        Expanded(
                          child: Text(
                            location,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 9),
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            price,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: MarketPalette.ink,
                              fontSize: 16,
                              fontWeight: FontWeight.w900,
                              letterSpacing: -.25,
                            ),
                          ),
                        ),
                        const Icon(Icons.arrow_forward_rounded,
                          size: 18, color: MarketPalette.jade),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
