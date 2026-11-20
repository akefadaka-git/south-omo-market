import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:http/http.dart' as http;

import '../marketplace_pages.dart';
import '../design/market_design_system.dart';

const defaultApiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000/api/v1',
);

/// Branded launch gate: the splash is the real initial route.
class MarketLaunchScreen extends StatefulWidget {
  const MarketLaunchScreen({super.key, required this.apiBaseUrl, required this.client, required this.onLocaleChanged});
  final String apiBaseUrl;
  final http.Client client;
  final ValueChanged<Locale> onLocaleChanged;
  @override
  State<MarketLaunchScreen> createState() => _MarketLaunchScreenState();
}

class _MarketLaunchScreenState extends State<MarketLaunchScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _motion = AnimationController(
    vsync: this, duration: const Duration(milliseconds: 1400),
  )..forward();

  @override
  void initState() {
    super.initState();
    Timer(const Duration(milliseconds: 1900), () {
      if (!mounted) return;
      Navigator.of(context).pushReplacement(MaterialPageRoute<void>(
        builder: (_) => MarketplaceDiscoveryPage(
          apiBaseUrl: widget.apiBaseUrl,
          client: widget.client,
          onLocaleChanged: widget.onLocaleChanged,
          onSellerSignIn: (context) => Navigator.of(context).push(
            MaterialPageRoute<void>(
              builder: (_) => MarketplaceHomePage(
                apiBaseUrl: widget.apiBaseUrl, client: widget.client,
              ),
            ),
          ),
        ),
      ));
    });
  }

  @override
  void dispose() { _motion.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: MarketPalette.deep,
    body: AnimatedBuilder(
      animation: _motion,
      builder: (context, child) => Stack(
        fit: StackFit.expand,
        children: [
          Positioned(right: -90 + 18 * _motion.value, top: 70,
            child: Container(width: 260, height: 260,
              decoration: BoxDecoration(shape: BoxShape.circle,
                border: Border.all(color: MarketPalette.mint.withValues(
                  alpha: .10 + .08 * _motion.value), width: 24)))),
          Positioned(left: -115, bottom: 35,
            child: Container(width: 300, height: 300,
              decoration: BoxDecoration(shape: BoxShape.circle,
                border: Border.all(color: MarketPalette.jade.withValues(alpha: .16), width: 28)))),
          Center(child: Opacity(opacity: _motion.value.clamp(0.0, 1.0),
            child: Transform.scale(scale: .88 + .12 * _motion.value,
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                const MarketBrandMark(size: 104, onDark: true),
                const SizedBox(height: 22),
                const Text('ደቡብ ኦሞ ገበያ',
                  style: TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.w800)),
                const SizedBox(height: 8),
                Text('የአካባቢያችን ምርት፣ አገልግሎትና ገበያ',
                  style: TextStyle(color: Colors.white.withValues(alpha: .76), fontSize: 14)),
                const SizedBox(height: 34),
                const SizedBox(width: 24, height: 24,
                  child: CircularProgressIndicator(strokeWidth: 2.2, color: MarketPalette.mint)),
              ])))),
          Positioned(bottom: 34, left: 0, right: 0,
            child: Text('ከአካባቢ ለአካባቢ', textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white.withValues(alpha: .48), fontSize: 12))),
        ],
      ),
    ),
  );
}


class SouthOmoMarketApp extends StatefulWidget {
  const SouthOmoMarketApp({
    super.key,
    this.apiBaseUrl = defaultApiBaseUrl,
    this.client,
  });

  final String apiBaseUrl;
  final http.Client? client;

  @override
  State<SouthOmoMarketApp> createState() => _SouthOmoMarketAppState();
}

class _SouthOmoMarketAppState extends State<SouthOmoMarketApp> {
  Locale _locale = const Locale('am');

  void _setLocale(Locale locale) {
    if (locale.languageCode != 'am' && locale.languageCode != 'en') return;
    setState(() => _locale = locale);
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'ደቡብ ኦሞ ገበያ',
        debugShowCheckedModeBanner: false,
        locale: _locale,
        supportedLocales: const [Locale('am'), Locale('en')],
        localizationsDelegates: GlobalMaterialLocalizations.delegates,
        theme: MarketDesignSystem.lightTheme,
        home: MarketLaunchScreen(
          apiBaseUrl: widget.apiBaseUrl,
          client: widget.client ?? http.Client(),
          onLocaleChanged: _setLocale,
        ),
      );
}

